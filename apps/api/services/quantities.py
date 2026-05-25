"""Per-year quantity formulas (spec Section 6). All inputs SI; pit_area in m²,
bench_height in m, density in t/m³, recovery as percent (0-100).
"""
from __future__ import annotations

from typing import Any


def compute_year_quantities(
    year: int,
    pit_area_m2: float,
    bench_height_m: float,
    bulk_density: float,
    topsoil_thickness: float,
    overburden_thickness: float,
    mineral_recovery_percent: float,
    *,
    backfill_started_year: int = 3,
) -> dict[str, Any]:
    """Return one row of the per-year quantity table.

    Conservative model: each year's pit advances one bench downward and outward
    enough that pit_area * bench_height equals the year's excavation volume.
    """
    recovery_frac = max(0.0, min(1.0, mineral_recovery_percent / 100.0))
    excavation_volume_m3 = pit_area_m2 * bench_height_m
    # MWP simplification: assume the bench cut is mostly mineral; in reality there
    # is a stripping component each year. The OB / topsoil quantities below
    # represent the layer above the year's footprint that is removed *first*.
    mineral_volume_m3 = excavation_volume_m3
    mineral_tonnes = mineral_volume_m3 * bulk_density
    saleable_tonnes = mineral_tonnes * recovery_frac
    topsoil_m3 = pit_area_m2 * topsoil_thickness
    overburden_m3 = pit_area_m2 * overburden_thickness
    # Backfill kicks in once we're deep enough that the year-1 pit is mined out.
    backfill_m3 = 0.0 if year < backfill_started_year else 0.4 * mineral_volume_m3
    plantation_area_m2 = 0.1 * pit_area_m2
    stripping_ratio = (
        (topsoil_m3 + overburden_m3) / mineral_volume_m3 if mineral_volume_m3 > 0 else 0.0
    )
    return {
        "year": year,
        "pit_area_m2": round(pit_area_m2, 1),
        "excavation_volume_m3": round(excavation_volume_m3, 1),
        "mineral_volume_m3": round(mineral_volume_m3, 1),
        "mineral_tonnes": round(mineral_tonnes, 1),
        "saleable_tonnes": round(saleable_tonnes, 1),
        "topsoil_m3": round(topsoil_m3, 1),
        "overburden_m3": round(overburden_m3, 1),
        "backfill_m3": round(backfill_m3, 1),
        "plantation_area_m2": round(plantation_area_m2, 1),
        "stripping_ratio": round(stripping_ratio, 3),
    }


ALTERNATIVE_PRODUCTION_MULTIPLIER: dict[str, float] = {
    "base": 1.0,
    "conservative": 0.7,
    "aggressive": 1.3,
    # v2 alternatives keep the production target steady but vary geometry:
    "low_waste": 1.0,
    "environment_sensitive": 0.85,
    "cost_optimized": 1.0,
    "grade_blending": 1.0,
    "minimum_disturbance": 0.8,
}
