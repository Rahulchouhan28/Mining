"""Verify the spec's Haripura inputs produce the expected per-year quantities.

Haripura sample: 50,000 t/y target, ρ=2.4 t/m³, 90 % recovery, 6 m benches.
For a single year:

  required mineral mass = 50,000 t
  in-pit volume        = 50,000 / (2.4 × 0.90) = 23,148.15 m³
  pit area at 6 m bench = 23,148.15 / 6        = 3,858.0 m²

`compute_year_quantities` works in the opposite direction (area → tonnes).
Plugging 3858 m² back in MUST round-trip to ≈ 50,000 saleable t.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.quantities import compute_year_quantities  # noqa: E402


def test_haripura_year1_round_trip() -> None:
    row = compute_year_quantities(
        year=1,
        pit_area_m2=3858.0,
        bench_height_m=6.0,
        bulk_density=2.4,
        topsoil_thickness=0.3,
        overburden_thickness=1.0,
        mineral_recovery_percent=90.0,
    )
    # excavation = 3858 × 6 = 23,148 m³
    assert abs(row["excavation_volume_m3"] - 23_148.0) < 1.0
    # mineral tonnes = 23,148 × 2.4 = 55,555 t (ROM before recovery)
    assert abs(row["mineral_tonnes"] - 55_555.0) < 5.0
    # saleable = 55,555 × 0.90 = 50,000 t
    assert abs(row["saleable_tonnes"] - 50_000.0) < 5.0
    # topsoil = 3858 × 0.3 = 1,157 m³
    assert abs(row["topsoil_m3"] - 1_157.4) < 1.0
    # OB = 3858 × 1.0 = 3,858 m³
    assert abs(row["overburden_m3"] - 3_858.0) < 1.0
    # stripping ratio = (1157.4 + 3858) / 23148 ≈ 0.217
    assert abs(row["stripping_ratio"] - 0.217) < 0.01


def test_backfill_kicks_in_year3() -> None:
    common = dict(pit_area_m2=3858.0, bench_height_m=6.0, bulk_density=2.4,
                  topsoil_thickness=0.3, overburden_thickness=1.0,
                  mineral_recovery_percent=90.0)
    assert compute_year_quantities(year=1, **common)["backfill_m3"] == 0
    assert compute_year_quantities(year=2, **common)["backfill_m3"] == 0
    assert compute_year_quantities(year=3, **common)["backfill_m3"] > 0
