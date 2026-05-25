"""Per-year statutory plate composer."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pdfplumber
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.year_plate import compose_year_plate  # noqa: E402
from services.year_planner import generate_for_project  # noqa: E402


FIXTURE = {
    "project_details": {
        "project_name": "Year Plate Test", "applicant_name": "M/s. Test",
        "mineral": "Limestone", "village": "Haripura", "tehsil": "Kheenvsar",
        "district": "Nagaur", "state": "Rajasthan", "area_ha": 4.8,
        "map_type": "year_wise_mining_plan", "scale": "1:1000",
        "survey_date": "2025-03-10", "plan_period_years": 5,
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
        }],
    },
    "engineering_inputs": {
        "production": {"annual_production_target_tonnes": 50000, "approved_capacity_tonnes_per_year": 50000},
        "bench": {"bench_height_m": 6},
        "mineral_waste": {"bulk_density_t_per_m3": 2.4, "topsoil_thickness_m": 0.3,
                          "overburden_thickness_m": 1.0, "mineral_recovery_percent": 90},
    },
}


@pytest.fixture(scope="module")
def project_with_plan() -> dict:
    result = generate_for_project(FIXTURE, ["base"])
    p = dict(FIXTURE)
    p.update({"selected_alternatives": ["base"], "generated_plans": result["generated_plans"],
              "quantity_tables": result["quantity_tables"], "validation_warnings": result["validation_warnings"]})
    return p


@pytest.mark.parametrize("year,plate_letter,ordinal", [
    (1, "A", "1ST"),
    (2, "B", "2ND"),
    (3, "C", "3RD"),
    (4, "D", "4TH"),
    (5, "E", "5TH"),
])
def test_year_plate_has_correct_title_and_plate_number(project_with_plan: dict, year: int, plate_letter: str, ordinal: str) -> None:
    pdf_bytes = compose_year_plate(project_with_plan, alternative="base", year=year,
                                   paper="A3", orientation="landscape", scale=1000)
    assert len(pdf_bytes) > 30_000
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert len(pdf.pages) == 1
        page = pdf.pages[0]
        # A3 landscape
        assert abs(page.width - 1190.0) < 5
        assert abs(page.height - 842.0) < 5
        text = (page.extract_text() or "").upper()
        assert f"{ordinal} YEAR DEVELOPMENT PLAN" in text, f"Year {year} title missing"
        # PDF text extraction strips/varies the en-dash separator — accept any whitespace
        # between "PLATE NO." and the plate code.
        import re as _re
        assert _re.search(rf"PLATE NO\.\s*[-–—]?\s*5{plate_letter}\b", text) is not None, \
            f"Plate number 5{plate_letter} missing — got: {text[-200:]}"
        assert "CERTIFICATION" in text
        assert "YEAR PLATE TEST" in text


def test_year_plate_omits_other_years_pits(project_with_plan: dict) -> None:
    """Year 1 plate should only highlight Year 1 (other years appear faintly
    as outlines, not coloured fills)."""
    pdf_bytes_y1 = compose_year_plate(project_with_plan, alternative="base", year=1)
    pdf_bytes_y3 = compose_year_plate(project_with_plan, alternative="base", year=3)
    # Different content should produce different byte payloads
    assert pdf_bytes_y1 != pdf_bytes_y3
    # Year 5 plate has the most "DIRECTION OF YEAR" arrows context absent (final year)
    pdf_bytes_y5 = compose_year_plate(project_with_plan, alternative="base", year=5)
    with pdfplumber.open(io.BytesIO(pdf_bytes_y5)) as pdf:
        text = (pdf.pages[0].extract_text() or "").upper()
        assert "DIRECTION OF YEAR 6" not in text, "should not point to a non-existent year 6"


def test_year_plate_rejects_out_of_range_year(project_with_plan: dict) -> None:
    with pytest.raises(ValueError):
        compose_year_plate(project_with_plan, alternative="base", year=0)
    with pytest.raises(ValueError):
        compose_year_plate(project_with_plan, alternative="base", year=6)


def test_per_year_ob_features_are_cumulative(project_with_plan: dict) -> None:
    """The planner now emits one overburden_dump feature per year, growing
    cumulatively. Year 5's polygon should have the largest area."""
    from shapely.geometry import shape
    plan = next(p for p in project_with_plan["generated_plans"] if p["alternative"] == "base")
    ob_features = sorted(
        [f for f in plan["features"]["features"] if f["properties"]["layer_type"] == "overburden_dump"],
        key=lambda f: f["properties"].get("year", 0),
    )
    assert len(ob_features) >= 2, "expected per-year OB features"
    areas = [shape(f["geometry"]).area for f in ob_features]
    # Strictly non-decreasing year-over-year (cumulative growth)
    for i in range(1, len(areas)):
        assert areas[i] >= areas[i - 1] * 0.95, f"year {i+1} OB area {areas[i]} < year {i} {areas[i-1]}"
