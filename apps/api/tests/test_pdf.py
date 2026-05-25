"""Assert the PDF composer produces a valid statutory-looking A3 plate."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pdfplumber
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.pdf_composer import compose_plate  # noqa: E402
from services.year_planner import generate_for_project  # noqa: E402


FIXTURE_PROJECT = {
    "project_details": {
        "project_name": "Test Plate",
        "applicant_name": "M/s. Test",
        "mineral": "Limestone",
        "village": "Haripura", "tehsil": "Kheenvsar", "district": "Nagaur", "state": "Rajasthan",
        "area_ha": 4.8, "map_type": "year_wise_mining_plan", "scale": "1:1000",
        "survey_date": "2025-03-10", "plan_period_years": 5,
    },
    "digitized_layers": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"layer_type": "lease_boundary", "label": "Lease"},
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
    result = generate_for_project(FIXTURE_PROJECT, ["base"])
    project = dict(FIXTURE_PROJECT)
    project.update({
        "selected_alternatives": ["base"],
        "generated_plans": result["generated_plans"],
        "quantity_tables": result["quantity_tables"],
        "validation_warnings": result["validation_warnings"],
    })
    return project


def test_plate_is_a3_landscape_with_required_text(project_with_plan: dict) -> None:
    pdf_bytes = compose_plate(project_with_plan, alternative="base",
                              paper="A3", orientation="landscape", scale=1000)
    assert len(pdf_bytes) > 50_000, "PDF unexpectedly tiny — drawing failed?"

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert len(pdf.pages) == 1
        page = pdf.pages[0]
        # A3 landscape = 16.54 × 11.69 inches = 1190.4 × 841.7 points
        assert abs(page.width - 1190.0) < 5, f"page width {page.width} pt is not A3 landscape"
        assert abs(page.height - 842.0) < 5, f"page height {page.height} pt is not A3 landscape"

        text = (page.extract_text() or "").upper()
        assert "TEST PLATE" in text, "title block missing project name"
        assert "CERTIFICATION" in text, "certification box missing"
        assert "RQP" in text or "QUALIFIED" in text, "certification clause missing"
        assert "SCALE" in text, "scale label missing"
        assert "HARIPURA" in text, "village context missing"
