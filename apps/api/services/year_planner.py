"""Year-wise pit slicer (spec Section 6).

Inputs: lease boundary (WGS84) and engineering parameters.
Output: per-alternative GeoJSON FeatureCollection of generated layers +
quantity table + validation warnings.

The geometric model is intentionally simple for v1:

  1. Reproject lease → EPSG:32643 (UTM 43 N).
  2. Available mineable area = lease shrunk by 7.5 m statutory barrier.
  3. Required pit area per year = annual_target / density / recovery / bench_h.
  4. Year polygons grow concentrically from the centroid of the available area
     using radial buffers, intersected with the available envelope so they
     never escape the barrier.
  5. OB / topsoil / plantation are placed in the largest leftover polygon
     after the ultimate (final year) pit is subtracted.
  6. Haul road = straight line from the ultimate-pit centroid edge to the
     nearest lease boundary point.

This is a *conceptual* plan, not a Whittle / Lerchs-Grossmann optimisation.
A qualified mining engineer must verify before any statutory submission.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union

from services.projection import geom_to_utm, geom_to_wgs, geojson_to_shape, shape_to_geojson
from services.quantities import compute_year_quantities
from services.strategies import get as get_strategy
from services.validation import validate_engineering_inputs, validate_geometry


@dataclass
class PlanningOutput:
    alternative: str
    features: dict[str, Any]                    # GeoJSON FeatureCollection (WGS84)
    quantities: dict[str, Any]                  # { alternative, rows: [...] }
    warnings: list[dict[str, Any]]


def _extract_lease(layers: dict[str, Any] | None) -> dict[str, Any] | None:
    if not layers:
        return None
    for f in (layers.get("features") or []):
        if (f.get("properties") or {}).get("layer_type") == "lease_boundary":
            return f.get("geometry")
    return None


def _largest_polygon(g: BaseGeometry) -> Polygon | None:
    if g.is_empty:
        return None
    if isinstance(g, Polygon):
        return g
    if isinstance(g, MultiPolygon):
        return max(g.geoms, key=lambda p: p.area)
    return None


def _wgs_feature(layer_type: str, utm_geom: BaseGeometry, **props: Any) -> dict[str, Any]:
    wgs = geom_to_wgs(utm_geom)
    return {
        "type": "Feature",
        "geometry": shape_to_geojson(wgs),
        "properties": {"layer_type": layer_type, **{k: v for k, v in props.items() if v is not None}},
    }


def generate_for_alternative(project: dict[str, Any], alternative: str) -> PlanningOutput:
    ei = project.get("engineering_inputs") or {}
    details = project.get("project_details") or {}
    plan_years = int(details.get("plan_period_years") or 5)
    plan_years = max(1, min(5, plan_years))

    warnings: list[dict[str, Any]] = []
    warnings.extend(validate_engineering_inputs(ei, alternative))

    lease_gj = _extract_lease(project.get("digitized_layers"))
    if not lease_gj:
        warnings.extend(validate_geometry(lease=None, barrier=None, pits=[], alternative=alternative))
        return PlanningOutput(alternative, {"type": "FeatureCollection", "features": []},
                              {"alternative": alternative, "rows": []}, warnings)

    lease_wgs = geojson_to_shape(lease_gj)
    lease = geom_to_utm(lease_wgs)
    if not isinstance(lease, (Polygon, MultiPolygon)):
        warnings.append({"severity": "error", "code": "BAD_LEASE", "message": "Lease must be a polygon.", "alternative": alternative})
        return PlanningOutput(alternative, {"type": "FeatureCollection", "features": []},
                              {"alternative": alternative, "rows": []}, warnings)
    lease = _largest_polygon(lease) or lease

    # 7.5 m statutory barrier — inward buffer
    barrier_inner = lease.buffer(-7.5)
    barrier_ring = lease.difference(barrier_inner)  # the annular barrier itself
    available = _largest_polygon(barrier_inner) if not barrier_inner.is_empty else None
    if available is None or available.area < 1.0:
        warnings.append({"severity": "error", "code": "BARRIER_TOO_LARGE", "message": "Lease too small for 7.5 m barrier.", "alternative": alternative})
        return PlanningOutput(alternative, {"type": "FeatureCollection", "features": []},
                              {"alternative": alternative, "rows": []}, warnings)

    # Engineering inputs
    prod = ei.get("production") or {}
    mw = ei.get("mineral_waste") or {}
    bench = ei.get("bench") or {}
    annual_target_t = float(prod.get("annual_production_target_tonnes") or 0)
    density = float(mw.get("bulk_density_t_per_m3") or 0)
    recovery = float(mw.get("mineral_recovery_percent") or 0) / 100.0
    bench_h = float(bench.get("bench_height_m") or 0)
    topsoil_h = float(mw.get("topsoil_thickness_m") or 0)
    ob_h = float(mw.get("overburden_thickness_m") or 0)

    strategy = get_strategy(alternative)
    effective_target = annual_target_t * strategy.production_multiplier

    # All UTM features in the project (used by strategies that need to
    # see sensitive structures, geological zones, etc.)
    all_features_utm: list[tuple[dict[str, Any], BaseGeometry]] = []
    for f in (project.get("digitized_layers") or {}).get("features") or []:
        try:
            all_features_utm.append((f.get("properties") or {}, geom_to_utm(geojson_to_shape(f["geometry"]))))
        except Exception:
            continue

    # Required pit area per year (m²)
    if density > 0 and recovery > 0 and bench_h > 0:
        area_per_year = effective_target / density / recovery / bench_h
    else:
        area_per_year = available.area / plan_years  # fallback: split equally

    # Cap so we don't ever exceed available area in total.
    total_needed = area_per_year * plan_years
    if total_needed > available.area:
        scale = available.area / total_needed
        area_per_year *= scale
        warnings.append({
            "severity": "warning", "code": "AREA_CAPPED",
            "message": f"Cumulative pit area exceeds available mineable area; year sizes scaled by {scale:.2f}.",
            "alternative": alternative,
        })

    # Concentric expansion from a strategy-chosen seed point
    cx, cy = strategy.center_fn(available, lease, all_features_utm)
    year_polys: list[Polygon] = []
    prev_cum: Polygon | None = None
    for y in range(1, plan_years + 1):
        cumulative_area = area_per_year * y
        radius = math.sqrt(cumulative_area / math.pi)
        circle = Point(cx, cy).buffer(radius, resolution=64)
        cum = circle.intersection(available)
        cum_poly = _largest_polygon(cum) or Polygon()
        if prev_cum is None:
            year_poly = cum_poly
        else:
            year_poly = cum_poly.difference(prev_cum)
            year_poly = _largest_polygon(year_poly) or Polygon()
        year_polys.append(year_poly)
        prev_cum = cum_poly

    ultimate_pit = unary_union(year_polys)
    ultimate_pit_poly = _largest_polygon(ultimate_pit)
    if ultimate_pit_poly is None or ultimate_pit_poly.is_empty:
        warnings.append({"severity": "error", "code": "NO_PIT", "message": "Could not generate ultimate pit.", "alternative": alternative})
        return PlanningOutput(alternative, {"type": "FeatureCollection", "features": []},
                              {"alternative": alternative, "rows": []}, warnings)

    # Place OB dump in the largest empty region inside the available area
    empty = available.difference(ultimate_pit_poly.buffer(2.0))  # 2 m buffer between pit and dump
    ob_region = _largest_polygon(empty)
    ob_dump: Polygon | None = None
    topsoil_stack: Polygon | None = None
    plantation: Polygon | None = None
    if ob_region is not None and not ob_region.is_empty and ob_region.area > 10:
        # OB takes roughly proportional area to total OB volume / mean dump height.
        # Low-Waste / Min-Disturbance shrink the external dump because more is
        # back-haul-filled into the pit.
        total_ob_m3 = ultimate_pit_poly.area * ob_h * strategy.ob_dump_external_fraction
        dump_height = 6.0  # assumed lift height
        ob_target_area = min(total_ob_m3 / dump_height, ob_region.area * 0.6)
        ob_dump = _shrink_to_area(ob_region, ob_target_area, prefer_center=False)

        remaining = ob_region.difference(ob_dump.buffer(2.0)) if ob_dump is not None else ob_region
        remaining_poly = _largest_polygon(remaining)
        if remaining_poly is not None and remaining_poly.area > 10:
            total_ts_m3 = ultimate_pit_poly.area * topsoil_h
            ts_target_area = min(total_ts_m3 / 3.0, remaining_poly.area * 0.5)
            topsoil_stack = _shrink_to_area(remaining_poly, ts_target_area, prefer_center=False)

            rem2 = remaining_poly.difference(topsoil_stack.buffer(2.0)) if topsoil_stack is not None else remaining_poly
            rem2_poly = _largest_polygon(rem2)
            if rem2_poly is not None and rem2_poly.area > 10:
                plantation_target = min(ultimate_pit_poly.area * strategy.plantation_fraction, rem2_poly.area)
                plantation = _shrink_to_area(rem2_poly, plantation_target, prefer_center=True)

    # Haul road: line from ultimate-pit boundary to nearest lease boundary
    pit_centroid = ultimate_pit_poly.centroid
    pit_edge, lease_edge = nearest_points(ultimate_pit_poly.exterior, lease.exterior)
    haul_road = LineString([pit_centroid, pit_edge, lease_edge])

    # Build features (reproject to WGS84)
    features: list[dict[str, Any]] = []
    features.append(_wgs_feature("statutory_barrier_7_5m", barrier_ring, locked=True, label="7.5 m statutory barrier"))
    features.append(_wgs_feature("ultimate_pit_limit", ultimate_pit_poly, label="Ultimate Pit Limit"))
    for i, yp in enumerate(year_polys, start=1):
        if yp.is_empty:
            continue
        features.append(_wgs_feature("year_pit", yp, year=i, label=f"Year {i} Pit", alternative=alternative))
    if ob_dump and not ob_dump.is_empty:
        # Per-year cumulative slices: Year N plate shows OB[year=N], which is
        # what's been dumped on the surface by the end of year N. Each grows
        # concentrically from the dump anchor.
        for i, slice_poly in enumerate(_per_year_cumulative(ob_dump, plan_years), start=1):
            if slice_poly is None or slice_poly.is_empty:
                continue
            features.append(_wgs_feature(
                "overburden_dump", slice_poly, year=i,
                label=f"OB dump through Year {i}", alternative=alternative,
            ))
    if topsoil_stack and not topsoil_stack.is_empty:
        for i, slice_poly in enumerate(_per_year_cumulative(topsoil_stack, plan_years), start=1):
            if slice_poly is None or slice_poly.is_empty:
                continue
            features.append(_wgs_feature(
                "topsoil_stack", slice_poly, year=i,
                label=f"Topsoil stack through Year {i}", alternative=alternative,
            ))
    if plantation and not plantation.is_empty:
        for i, slice_poly in enumerate(_per_year_cumulative(plantation, plan_years), start=1):
            if slice_poly is None or slice_poly.is_empty:
                continue
            features.append(_wgs_feature(
                "plantation", slice_poly, year=i,
                label=f"Plantation through Year {i}", alternative=alternative,
            ))
    features.append(_wgs_feature("haul_road", haul_road, label="Haul Road", alternative=alternative))

    # Quantity table per year
    rows: list[dict[str, Any]] = []
    for i, yp in enumerate(year_polys, start=1):
        rows.append(compute_year_quantities(
            year=i,
            pit_area_m2=yp.area,
            bench_height_m=bench_h or 6.0,
            bulk_density=density or 1.0,
            topsoil_thickness=topsoil_h,
            overburden_thickness=ob_h,
            mineral_recovery_percent=(recovery * 100.0) if recovery > 0 else 100.0,
            **strategy.quantity_kwargs(),
        ))

    warnings.extend(validate_geometry(lease=lease, barrier=barrier_inner, pits=year_polys, alternative=alternative))

    return PlanningOutput(
        alternative=alternative,
        features={"type": "FeatureCollection", "features": features},
        quantities={"alternative": alternative, "rows": rows, "generated_at": datetime.now(timezone.utc).isoformat()},
        warnings=warnings,
    )


def _per_year_cumulative(full_poly: Polygon, plan_years: int) -> list[Polygon | None]:
    """Return [poly_year_1, ..., poly_year_N] where poly_year_N has cumulative
    area proportional to N / plan_years, growing concentrically from the
    polygon's centroid and intersected with the full polygon.

    Year `plan_years` always returns the full polygon. Used to slice OB,
    topsoil, and plantation footprints into per-year cumulative growth.
    """
    if plan_years <= 1:
        return [full_poly]
    anchor = full_poly.centroid
    full_area = full_poly.area
    out: list[Polygon | None] = []
    seed_radius = math.sqrt(full_area / math.pi)
    for i in range(1, plan_years + 1):
        if i == plan_years:
            out.append(full_poly)
            continue
        target_area = full_area * (i / plan_years)
        radius = math.sqrt(target_area / math.pi)
        clipped: Polygon | None = None
        for _ in range(8):
            circle = Point(anchor.x, anchor.y).buffer(radius, resolution=48)
            clipped_geom = circle.intersection(full_poly)
            clipped = _largest_polygon(clipped_geom)
            if clipped is None or clipped.is_empty:
                radius *= 1.5
                continue
            if clipped.area >= target_area * 0.95:
                break
            radius = min(radius * 1.3, seed_radius * 3.0)
        out.append(clipped if clipped is not None and not clipped.is_empty else None)
    return out


def _shrink_to_area(poly: Polygon, target_area: float, *, prefer_center: bool) -> Polygon:
    """Shrink `poly` inward by repeated buffering until area ≤ target_area.

    Returns the smallest connected polygon that satisfies the area constraint,
    or the full poly if it's already small enough.
    """
    if poly.area <= target_area or target_area <= 0:
        return poly
    # binary search on inward buffer distance
    lo, hi = 0.0, max(1.0, math.sqrt(poly.area / math.pi))
    best = poly
    for _ in range(20):
        mid = (lo + hi) / 2
        candidate = poly.buffer(-mid)
        candidate_poly = _largest_polygon(candidate)
        if candidate_poly is None or candidate_poly.is_empty:
            hi = mid
            continue
        if candidate_poly.area > target_area:
            lo = mid
            best = candidate_poly
        else:
            best = candidate_poly
            hi = mid
    return best


def generate_for_project(project: dict[str, Any], alternatives: list[str]) -> dict[str, Any]:
    plans: list[dict[str, Any]] = []
    qtables: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for alt in alternatives:
        out = generate_for_alternative(project, alt)
        plans.append({"alternative": alt, "generated_at": out.quantities.get("generated_at"), "features": out.features})
        qtables.append({"alternative": alt, "rows": out.quantities["rows"]})
        warnings.extend(out.warnings)
    return {"generated_plans": plans, "quantity_tables": qtables, "validation_warnings": warnings}
