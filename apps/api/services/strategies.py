"""Per-alternative planning strategies (spec Section 5).

Each strategy bundles the parameters that make one alternative geometrically
or economically distinct from another. Defaults are tuned for the Haripura
sample so all eight alternatives produce visibly different output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry


# Center-strategy callables receive (available_area, lease, all_features_utm)
# and must return (cx, cy) — the seed point for concentric pit expansion.
CenterFn = Callable[[Polygon, BaseGeometry, list[tuple[dict[str, Any], BaseGeometry]]], tuple[float, float]]


def center_centroid(available: Polygon, lease: BaseGeometry, _features: list) -> tuple[float, float]:
    c = available.centroid
    return c.x, c.y


def center_near_exit(available: Polygon, lease: BaseGeometry, _features: list) -> tuple[float, float]:
    """Bias pit start toward the centroid-side closest to the lease perimeter
    (proxy for the cheapest haul-road exit). Cost-Optimized uses this.
    """
    centroid = available.centroid
    from shapely.ops import nearest_points
    _, edge = nearest_points(centroid, lease.exterior)
    # take a point ~30 % of the way from the centroid toward the exit edge
    cx = centroid.x + (edge.x - centroid.x) * 0.30
    cy = centroid.y + (edge.y - centroid.y) * 0.30
    if Point(cx, cy).within(available):
        return cx, cy
    return centroid.x, centroid.y


_SENSITIVE_TYPES = {"village", "existing_tank", "water_reservoir", "sensitive_structure", "existing_electric_line"}


def center_away_from_sensitive(available: Polygon, _lease: BaseGeometry,
                                features: list[tuple[dict[str, Any], BaseGeometry]]) -> tuple[float, float]:
    """Environment-Sensitive: push pit centroid away from any sensitive feature."""
    centroid = available.centroid
    sens = [g for (props, g) in features if props.get("layer_type") in _SENSITIVE_TYPES]
    if not sens:
        return centroid.x, centroid.y
    dx = 0.0
    dy = 0.0
    for g in sens:
        c = g.centroid
        dx_i = centroid.x - c.x
        dy_i = centroid.y - c.y
        # inverse-distance weighting in projected meters
        d = (dx_i * dx_i + dy_i * dy_i) ** 0.5 or 1.0
        dx += dx_i / d
        dy += dy_i / d
    # normalise + offset by ~10 % of the available radius
    mag = (dx * dx + dy * dy) ** 0.5 or 1.0
    radius = (available.area / 3.14159) ** 0.5
    offset = radius * 0.10
    cx = centroid.x + (dx / mag) * offset
    cy = centroid.y + (dy / mag) * offset
    if Point(cx, cy).within(available):
        return cx, cy
    return centroid.x, centroid.y


def center_high_grade(available: Polygon, lease: BaseGeometry,
                      features: list[tuple[dict[str, Any], BaseGeometry]]) -> tuple[float, float]:
    """Grade-Blending: bias toward the centroid of any drawn geological_zone
    features. Falls back to area centroid if none are present (v1 has no
    grade-aware fill from CSV import yet).
    """
    zones = [g for (props, g) in features if props.get("layer_type") == "geological_zone"]
    if zones:
        from shapely.ops import unary_union
        c = unary_union(zones).centroid
        if Point(c.x, c.y).within(available):
            return c.x, c.y
    return center_centroid(available, lease, [])


@dataclass(frozen=True)
class AlternativeStrategy:
    name: str
    production_multiplier: float = 1.0
    center_fn: CenterFn = center_centroid
    backfill_start_year: int = 3
    backfill_fraction: float = 0.4
    plantation_fraction: float = 0.10
    # Fraction of total OB volume kept as external dump (Low-Waste lowers this
    # to e.g. 0.3 because more is back-haul-filled into the pit).
    ob_dump_external_fraction: float = 1.0
    notes: str = ""

    def quantity_kwargs(self) -> dict[str, Any]:
        return {
            "backfill_started_year": self.backfill_start_year,
            "backfill_fraction": self.backfill_fraction,
            "plantation_fraction": self.plantation_fraction,
        }


STRATEGIES: dict[str, AlternativeStrategy] = {
    "base": AlternativeStrategy(
        name="base",
        notes="Balanced concentric expansion from the available-area centroid.",
    ),
    "conservative": AlternativeStrategy(
        name="conservative",
        production_multiplier=0.7,
        notes="Slow advance; 70 % of base target.",
    ),
    "aggressive": AlternativeStrategy(
        name="aggressive",
        production_multiplier=1.3,
        notes="Faster excavation; 130 % of base target.",
    ),
    "low_waste": AlternativeStrategy(
        name="low_waste",
        backfill_start_year=2,        # backfill earlier
        backfill_fraction=0.65,        # backfill more
        plantation_fraction=0.15,      # slightly more plantation
        ob_dump_external_fraction=0.3, # most OB goes back into the pit
        notes="Backfill priority. Earlier backfill, larger fraction, smaller external OB dump.",
    ),
    "environment_sensitive": AlternativeStrategy(
        name="environment_sensitive",
        production_multiplier=0.85,
        center_fn=center_away_from_sensitive,
        plantation_fraction=0.20,
        notes="Centroid pushed away from villages, tanks, sensitive structures; "
              "production reduced 15 %; doubled plantation footprint.",
    ),
    "cost_optimized": AlternativeStrategy(
        name="cost_optimized",
        center_fn=center_near_exit,
        notes="Pit biased toward the closest lease-perimeter exit to shorten haul.",
    ),
    "grade_blending": AlternativeStrategy(
        name="grade_blending",
        center_fn=center_high_grade,
        notes="Pit biased toward digitized geological-zone centroids when present.",
    ),
    "minimum_disturbance": AlternativeStrategy(
        name="minimum_disturbance",
        production_multiplier=0.8,
        backfill_start_year=2,
        backfill_fraction=0.55,
        plantation_fraction=0.18,
        ob_dump_external_fraction=0.4,
        notes="Smaller annual footprint, early backfill, reduced external dump.",
    ),
}


def get(alternative: str) -> AlternativeStrategy:
    return STRATEGIES.get(alternative, STRATEGIES["base"])
