"""Auto-extract a lease boundary from whatever the user uploaded.

Strategy:
  1. If any upload is a KML / KMZ / GeoJSON, parse the largest polygon as the lease.
  2. Otherwise fall back to a synthetic square sized from `project_details.area_ha`,
     centred on a sensible default (Haripura, 27.20°N 73.65°E).
  3. Also seed engineering inputs with conceptual defaults if the user hasn't
     filled them in. Mark every seeded field 'ASSUMED — NEEDS VALIDATION'.

Returns a copy of the project dict with `digitized_layers` and
`engineering_inputs` populated, ready for `year_planner.generate_for_project`.
"""
from __future__ import annotations

import io
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform as shp_transform

import storage

_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
_to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

DEFAULT_CENTER_LAT = 27.2005
DEFAULT_CENTER_LON = 73.6500

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def auto_prepare(slug: str) -> dict[str, Any]:
    project = storage.load_project(slug)
    project = _ensure_engineering_defaults(project)

    lease_feature = _try_extract_from_uploads(slug, project) or _synthetic_lease(project)
    borehole_features = _try_extract_boreholes(slug, project)

    layers = project.get("digitized_layers") or {"type": "FeatureCollection", "features": []}
    # Preserve other user-drawn features; replace lease + replace existing
    # auto-extracted boreholes (re-running auto-prepare refreshes both).
    others = [
        f for f in layers.get("features", [])
        if (f.get("properties") or {}).get("layer_type") != "lease_boundary"
        and not (f.get("properties") or {}).get("auto_extracted")
    ]
    layers["type"] = "FeatureCollection"
    layers["features"] = [lease_feature, *borehole_features, *others]
    project["digitized_layers"] = layers

    storage.save_project(slug, project)
    return project


def _try_extract_boreholes(slug: str, project: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse any uploaded `borehole_data` CSV into proposed_borehole point features.

    The CSV is expected to have headers for latitude and longitude (any of the
    common synonyms below). Other columns are kept in the feature properties.
    Falls back to an empty list if no borehole CSV is uploaded or parsing fails.
    """
    out: list[dict[str, Any]] = []
    for record in project.get("uploaded_files") or []:
        if record.get("category") != "borehole_data":
            continue
        rel = record.get("stored_path")
        if not rel:
            continue
        full = storage.ROOT.parent / rel
        if not full.exists() or not full.name.lower().endswith(".csv"):
            continue
        try:
            out.extend(_boreholes_from_csv(full, source=record.get("filename") or full.name))
        except Exception:  # noqa: BLE001 — extraction is best-effort
            continue
    return out


_LAT_KEYS = {"lat", "latitude", "y", "northing", "lat_dd", "lat (deg)"}
_LON_KEYS = {"lon", "lng", "long", "longitude", "x", "easting", "lon_dd", "lng (deg)", "long (deg)"}
_ID_KEYS  = {"id", "borehole", "bh", "bh_id", "name", "hole", "hole_id"}


def _boreholes_from_csv(path: Path, *, source: str) -> list[dict[str, Any]]:
    import csv as _csv

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = _csv.DictReader(fh)
        if not reader.fieldnames:
            return []
        col_map: dict[str, str] = {}
        for col in reader.fieldnames:
            lower = col.strip().lower()
            if lower in _LAT_KEYS and "lat" not in col_map:
                col_map["lat"] = col
            elif lower in _LON_KEYS and "lon" not in col_map:
                col_map["lon"] = col
            elif lower in _ID_KEYS and "id" not in col_map:
                col_map["id"] = col
        if "lat" not in col_map or "lon" not in col_map:
            return []

        features: list[dict[str, Any]] = []
        for row in reader:
            try:
                lat = float(row[col_map["lat"]])
                lon = float(row[col_map["lon"]])
            except (TypeError, ValueError, KeyError):
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            props: dict[str, Any] = {
                "layer_type": "proposed_borehole",
                "label": row.get(col_map["id"]) if "id" in col_map else None,
                "auto_extracted": True,
                "source": f"auto-extracted from {source}",
            }
            # Keep all extra columns as metadata
            for k, v in row.items():
                if k in (col_map.get("lat"), col_map.get("lon"), col_map.get("id")):
                    continue
                if v is None or v == "":
                    continue
                props[f"bh_{k.strip().lower().replace(' ', '_')}"] = v
            features.append({
                "type": "Feature",
                "properties": {k: v for k, v in props.items() if v is not None},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
        return features


def _try_extract_from_uploads(slug: str, project: dict[str, Any]) -> dict[str, Any] | None:
    pdir = storage.project_dir(slug)
    for record in project.get("uploaded_files") or []:
        rel = record.get("stored_path")
        if not rel:
            continue
        full = storage.ROOT.parent / rel
        if not full.exists():
            continue
        name = (record.get("filename") or full.name).lower()
        try:
            if name.endswith(".geojson") or name.endswith(".json"):
                poly = _largest_polygon_from_geojson(full.read_bytes())
            elif name.endswith(".kml"):
                poly = _largest_polygon_from_kml(full.read_bytes())
            elif name.endswith(".kmz"):
                poly = _largest_polygon_from_kmz(full.read_bytes())
            else:
                continue
            if poly is None or poly.is_empty:
                continue
            return _feature(poly, source=f"auto-extracted from {record.get('filename')}")
        except Exception:  # noqa: BLE001 — extraction is best-effort
            continue
    return None


def _largest_polygon_from_geojson(data: bytes) -> Polygon | None:
    obj = json.loads(data)
    return _largest_polygon_from_geojson_object(obj)


def _largest_polygon_from_geojson_object(obj: Any) -> Polygon | None:
    geoms: list[Polygon] = []
    if isinstance(obj, dict):
        t = obj.get("type")
        if t == "FeatureCollection":
            for f in obj.get("features") or []:
                p = _largest_polygon_from_geojson_object(f)
                if p is not None:
                    geoms.append(p)
        elif t == "Feature":
            g = obj.get("geometry")
            if g is not None:
                p = _largest_polygon_from_geojson_object(g)
                if p is not None:
                    geoms.append(p)
        elif t in {"Polygon", "MultiPolygon"}:
            g = shape(obj)
            if isinstance(g, Polygon):
                geoms.append(g)
            elif isinstance(g, MultiPolygon):
                geoms.extend(g.geoms)
    if not geoms:
        return None
    return max(geoms, key=lambda p: p.area)


def _largest_polygon_from_kml(data: bytes) -> Polygon | None:
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = data.decode("latin-1", errors="ignore")
    # Strip namespaces for resilient querying.
    text = re.sub(r'\sxmlns="[^"]+"', "", text, count=1)
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    polys: list[Polygon] = []
    for poly_el in root.iter("Polygon"):
        coords_el = poly_el.find("outerBoundaryIs/LinearRing/coordinates")
        if coords_el is None or not coords_el.text:
            continue
        ring = _parse_kml_coords(coords_el.text)
        if len(ring) >= 4:
            holes = []
            for inner in poly_el.findall("innerBoundaryIs/LinearRing/coordinates"):
                if inner.text:
                    hole = _parse_kml_coords(inner.text)
                    if len(hole) >= 4:
                        holes.append(hole)
            try:
                polys.append(Polygon(ring, holes))
            except Exception:
                continue
    if not polys:
        return None
    return max(polys, key=lambda p: p.area)


def _parse_kml_coords(text: str) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for tok in text.split():
        bits = tok.split(",")
        if len(bits) >= 2:
            try:
                out.append((float(bits[0]), float(bits[1])))
            except ValueError:
                continue
    return out


def _largest_polygon_from_kmz(data: bytes) -> Polygon | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".kml"):
                    return _largest_polygon_from_kml(zf.read(name))
    except zipfile.BadZipFile:
        return None
    return None


def _synthetic_lease(project: dict[str, Any]) -> dict[str, Any]:
    details = project.get("project_details") or {}
    area_ha = float(details.get("area_ha") or 4.8)
    side_m = math.sqrt(area_ha * 10_000)  # square footprint
    cx_utm, cy_utm = _to_utm.transform(DEFAULT_CENTER_LON, DEFAULT_CENTER_LAT)
    half = side_m / 2.0
    corners_utm = [
        (cx_utm - half, cy_utm - half),
        (cx_utm + half, cy_utm - half),
        (cx_utm + half, cy_utm + half),
        (cx_utm - half, cy_utm + half),
        (cx_utm - half, cy_utm - half),
    ]
    poly_utm = Polygon(corners_utm)
    poly_wgs = shp_transform(_to_wgs.transform, poly_utm)
    return _feature(poly_wgs, source=f"synthetic {area_ha} ha square")


def _feature(poly_wgs: Polygon, *, source: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "layer_type": "lease_boundary",
            "label": "Lease Boundary",
            "auto_extracted": True,
            "source": source,
        },
        "geometry": mapping(poly_wgs),
    }


def _ensure_engineering_defaults(project: dict[str, Any]) -> dict[str, Any]:
    """Fill in conceptual defaults for any missing engineering input fields."""
    DEFAULTS: dict[str, dict[str, Any]] = {
        "production": {
            "annual_production_target_tonnes": 50000,
            "approved_capacity_tonnes_per_year": 50000,
            "working_days_per_year": 250,
            "shifts_per_day": 1,
            "hours_per_shift": 8,
        },
        "bench": {
            "bench_height_m": 6,
            "bench_width_m": 6,
            "face_slope_degree": 70,
            "overall_pit_slope_degree": 45,
            "ultimate_pit_depth_m": 42,
        },
        "mineral_waste": {
            "bulk_density_t_per_m3": 2.4,
            "topsoil_thickness_m": 0.3,
            "overburden_thickness_m": 1.0,
            "mineral_recovery_percent": 90,
            "reject_percent": 10,
        },
    }
    ei = project.get("engineering_inputs") or {}
    assumed: set[str] = set(ei.get("assumed_fields") or [])
    for section, fields in DEFAULTS.items():
        cur = ei.get(section) or {}
        for k, v in fields.items():
            if cur.get(k) in (None, ""):
                cur[k] = v
                assumed.add(f"{section}.{k}")
        ei[section] = cur
    ei["assumed_fields"] = sorted(assumed)
    project["engineering_inputs"] = ei
    # Default to ALL eight alternatives so every approach button shows on Step
    # 6 + Step 9. The auto-upgrade clause also catches projects saved before
    # this change (which used the legacy 3-alternative default).
    DEFAULT_ALTERNATIVES = [
        "base", "conservative", "aggressive",
        "low_waste", "environment_sensitive",
        "cost_optimized", "grade_blending", "minimum_disturbance",
    ]
    LEGACY_DEFAULT = {"base", "conservative", "aggressive"}
    current = project.get("selected_alternatives") or []
    if not current or set(current) == LEGACY_DEFAULT:
        project["selected_alternatives"] = DEFAULT_ALTERNATIVES
    return project
