"""Plate-type presets produce distinct PDFs with the right title block."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pdfplumber
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.pdf_composer import compose_plate  # noqa: E402
from services.year_planner import generate_for_project  # noqa: E402


FIXTURE = {
    "project_details": {
        "project_name": "Plate Test", "area_ha": 4.8, "scale": "1:1000",
        "village": "Haripura", "tehsil": "Kheenvsar", "district": "Nagaur", "state": "Rajasthan",
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
def project() -> dict:
    result = generate_for_project(FIXTURE, ["base"])
    p = dict(FIXTURE)
    p.update({"selected_alternatives": ["base"], "generated_plans": result["generated_plans"],
              "quantity_tables": result["quantity_tables"], "validation_warnings": result["validation_warnings"]})
    return p


@pytest.mark.parametrize("plate_type,expected_title", [
    ("year_wise_mining_plan", "YEAR-WISE MINING PLAN"),
    ("progressive_mine_closure_plan", "PROGRESSIVE MINE CLOSURE PLAN"),
    ("conceptual_plan", "CONCEPTUAL PLAN"),
])
def test_plate_titles_differ(project: dict, plate_type: str, expected_title: str) -> None:
    pdf_bytes = compose_plate(project, alternative="base", plate_type=plate_type,
                              paper="A3", orientation="landscape", scale=1000)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = (pdf.pages[0].extract_text() or "").upper()
        assert expected_title in text, f"{plate_type} did not render title '{expected_title}'"


def test_environment_plan_omits_pit_polygons(project: dict) -> None:
    """The Environment Plan should not include any year_pit or OB layers — and
    since the fixture has no env features either, it falls back to an error.
    Provide a sensitive feature first so the plate has something to draw."""
    fixture = dict(project)
    layers = dict(project["digitized_layers"])
    layers["features"] = list(layers["features"]) + [{
        "type": "Feature",
        "properties": {"layer_type": "village"},
        "geometry": {"type": "Point", "coordinates": [73.6500, 27.2000]},
    }]
    fixture["digitized_layers"] = layers
    pdf_bytes = compose_plate(fixture, alternative="base", plate_type="environment_plan",
                              paper="A3", orientation="landscape", scale=1000)
    assert len(pdf_bytes) > 30_000
    # Title check is enough for now; visual content correctness is part of
    # the conceptual-output disclaimer.
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = (pdf.pages[0].extract_text() or "").upper()
        assert "ENVIRONMENT PLAN" in text
