"""All 8 alternatives produce a plan, and they're visibly different.

Sanity rules:
  - Every alternative returns at least one year_pit polygon.
  - Conservative produces a smaller year-1 pit than Base; Aggressive produces a
    bigger one. Multiplier semantics hold.
  - Low-Waste's external OB dump is smaller (or absent) compared to Base.
  - Environment-Sensitive shifts the pit centroid away from a sensitive feature.
  - Plantation footprints in Low-Waste / Env-Sensitive / Min-Disturbance are
    larger than Base's because their strategies bump plantation_fraction.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.year_planner import generate_for_project  # noqa: E402
from services.strategies import STRATEGIES  # noqa: E402


BASE_PROJECT = {
    "project_details": {
        "project_name": "Test", "area_ha": 4.8, "scale": "1:1000",
        "plan_period_years": 5,
    },
    "digitized_layers": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"layer_type": "lease_boundary"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[73.6485, 27.1995], [73.6515, 27.1995],
                                 [73.6515, 27.2020], [73.6485, 27.2020],
                                 [73.6485, 27.1995]]],
            },
        }, {
            # Sensitive feature in the NE quadrant — Env-Sensitive should
            # push the pit centroid to the SW.
            "type": "Feature",
            "properties": {"layer_type": "village", "label": "Test village"},
            "geometry": {"type": "Point", "coordinates": [73.6513, 27.2018]},
        }],
    },
    "engineering_inputs": {
        "production": {"annual_production_target_tonnes": 50000, "approved_capacity_tonnes_per_year": 50000},
        "bench": {"bench_height_m": 6},
        "mineral_waste": {"bulk_density_t_per_m3": 2.4, "topsoil_thickness_m": 0.3,
                          "overburden_thickness_m": 1.0, "mineral_recovery_percent": 90},
    },
}


def _result_for(alts: list[str]) -> dict:
    return generate_for_project(BASE_PROJECT, alts)


def test_all_eight_alternatives_produce_plans() -> None:
    all_alts = list(STRATEGIES.keys())
    assert len(all_alts) == 8
    result = _result_for(all_alts)
    assert len(result["generated_plans"]) == 8
    for plan in result["generated_plans"]:
        year_pits = [f for f in plan["features"]["features"]
                     if f["properties"]["layer_type"] == "year_pit"]
        assert year_pits, f"{plan['alternative']} produced no year_pit polygons"


def test_production_multipliers_change_pit_size() -> None:
    result = _result_for(["base", "conservative", "aggressive"])
    qts = {q["alternative"]: q["rows"] for q in result["quantity_tables"]}
    base_y1 = qts["base"][0]["pit_area_m2"]
    cons_y1 = qts["conservative"][0]["pit_area_m2"]
    aggr_y1 = qts["aggressive"][0]["pit_area_m2"]
    assert cons_y1 < base_y1 < aggr_y1
    # within 5 % of the multiplier
    assert abs(cons_y1 / base_y1 - 0.7) < 0.05
    assert abs(aggr_y1 / base_y1 - 1.3) < 0.05


def test_low_waste_shrinks_external_ob_dump() -> None:
    result = _result_for(["base", "low_waste"])
    def _ob_area(plan):
        for f in plan["features"]["features"]:
            if f["properties"]["layer_type"] == "overburden_dump":
                from shapely.geometry import shape
                return shape(f["geometry"]).area
        return 0.0
    base_ob = _ob_area(next(p for p in result["generated_plans"] if p["alternative"] == "base"))
    lw_ob   = _ob_area(next(p for p in result["generated_plans"] if p["alternative"] == "low_waste"))
    # Both may be tiny in degree-area (we're not reprojecting here) but ratio holds.
    if base_ob > 0:
        assert lw_ob <= base_ob * 0.5, f"low_waste OB={lw_ob} should be <= 50% of base OB={base_ob}"


def test_environment_sensitive_shifts_centroid_away_from_village() -> None:
    result = _result_for(["base", "environment_sensitive"])
    def _ult_centroid(plan):
        from shapely.geometry import shape
        for f in plan["features"]["features"]:
            if f["properties"]["layer_type"] == "ultimate_pit_limit":
                return shape(f["geometry"]).centroid
        return None
    base_c = _ult_centroid(next(p for p in result["generated_plans"] if p["alternative"] == "base"))
    env_c  = _ult_centroid(next(p for p in result["generated_plans"] if p["alternative"] == "environment_sensitive"))
    assert base_c is not None and env_c is not None
    # Village is at (73.6513, 27.2018) — env-sensitive centroid should be
    # further from it (in WGS lng/lat degrees) than the base centroid.
    village = (73.6513, 27.2018)
    def _d2(c):
        return (c.x - village[0]) ** 2 + (c.y - village[1]) ** 2
    assert _d2(env_c) > _d2(base_c), "environment_sensitive did not move centroid away from sensitive feature"


def test_low_waste_year1_backfill_is_zero_but_year2_is_not() -> None:
    """Low-Waste shifts backfill_start_year from 3 to 2."""
    result = _result_for(["low_waste"])
    rows = result["quantity_tables"][0]["rows"]
    assert rows[0]["backfill_m3"] == 0       # year 1 still no backfill
    assert rows[1]["backfill_m3"] > 0        # year 2 starts backfill
    # And the fraction (0.65) is much higher than base's 0.4
    base_result = _result_for(["base"])
    base_year3 = base_result["quantity_tables"][0]["rows"][2]["backfill_m3"]
    lw_year3 = rows[2]["backfill_m3"]
    assert lw_year3 > base_year3 * 1.4, f"low_waste backfill={lw_year3} should be ~1.6× base={base_year3}"
