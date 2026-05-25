"""DXF export composer — round-trips through ezdxf and contains the right
layers, entities, and metadata for a statutory plate.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import ezdxf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.dxf_export import compose_year_dxf, compose_overview_dxf  # noqa: E402
from services.year_planner import generate_for_project  # noqa: E402


FIXTURE = {
    "project_details": {
        "project_name": "DXF Test", "applicant_name": "M/s. Test",
        "mineral": "Limestone", "village": "Haripura", "tehsil": "Kheenvsar",
        "district": "Nagaur", "state": "Rajasthan", "area_ha": 4.8,
        "scale": "1:1000", "survey_date": "2025-03-10", "plan_period_years": 5,
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
            "type": "Feature",
            "properties": {"layer_type": "proposed_borehole", "label": "PBH-1"},
            "geometry": {"type": "Point", "coordinates": [73.6500, 27.2005]},
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
    p.update({
        "selected_alternatives": ["base"],
        "generated_plans": result["generated_plans"],
        "quantity_tables": result["quantity_tables"],
        "validation_warnings": result["validation_warnings"],
    })
    return p


def _read_dxf(body: bytes) -> ezdxf.document.Drawing:
    return ezdxf.read(io.StringIO(body.decode("utf-8")))


REQUIRED_LAYERS = {
    "LEASE_BOUNDARY", "BARRIER_7_5M", "ULT_PIT_LIMIT",
    "YEAR_1_WORKING", "YEAR_2_WORKING", "YEAR_3_WORKING",
    "YEAR_4_WORKING", "YEAR_5_WORKING",
    "OB_DUMP_Y1", "TOPSOIL_Y1", "PLANTATION_Y1",
    "HAUL_ROAD", "TITLE_BLOCK", "CERTIFICATION", "INDEX_LEGEND",
    "GRID", "TEXT_LABELS", "NORTH_ARROW", "SCALE_BAR",
    "BH_EXISTING", "BH_PROPOSED",
}


def test_year_dxf_has_required_layers(project: dict) -> None:
    body = compose_year_dxf(project, alternative="base", year=1)
    assert len(body) > 30_000
    doc = _read_dxf(body)
    layers = {l.dxf.name for l in doc.layers}
    missing = REQUIRED_LAYERS - layers
    assert not missing, f"missing required layers: {missing}"


def test_year_dxf_units_are_meters_and_dxf_version_is_r2010(project: dict) -> None:
    body = compose_year_dxf(project, alternative="base", year=1)
    doc = _read_dxf(body)
    # R2010 == AC1024
    assert doc.dxfversion == "AC1024", f"expected AC1024 (R2010), got {doc.dxfversion}"
    # ezdxf.units.M == 6 (meters)
    assert doc.units == 6, f"expected units=6 (meters), got {doc.units}"


def test_year_dxf_filters_other_year_features(project: dict) -> None:
    """The Year 1 DXF should contain entities on YEAR_1_WORKING, OB_DUMP_Y1,
    TOPSOIL_Y1, PLANTATION_Y1 — but no entities on the Year 5 versions."""
    body = compose_year_dxf(project, alternative="base", year=1)
    doc = _read_dxf(body)
    from collections import Counter
    counts = Counter(e.dxf.layer for e in doc.modelspace())
    assert counts.get("YEAR_1_WORKING", 0) > 0
    assert counts.get("OB_DUMP_Y1", 0) > 0
    assert counts.get("TOPSOIL_Y1", 0) > 0
    assert counts.get("PLANTATION_Y1", 0) > 0
    # No entities on year-5 layers (the year filter dropped them)
    assert counts.get("YEAR_5_WORKING", 0) == 0
    assert counts.get("OB_DUMP_Y5", 0) == 0


def test_overview_dxf_contains_all_year_pits(project: dict) -> None:
    body = compose_overview_dxf(project, alternative="base")
    doc = _read_dxf(body)
    from collections import Counter
    counts = Counter(e.dxf.layer for e in doc.modelspace())
    for y in range(1, 6):
        assert counts.get(f"YEAR_{y}_WORKING", 0) > 0, f"YEAR_{y}_WORKING empty on overview DXF"


def test_year_dxf_includes_title_block_and_certification_text(project: dict) -> None:
    body = compose_year_dxf(project, alternative="base", year=3)
    doc = _read_dxf(body)
    texts: list[str] = []
    for e in doc.modelspace():
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                texts.append(e.dxf.text if e.dxftype() == "TEXT" else e.text)
            except Exception:
                continue
    blob = " ".join(texts).upper()
    assert "3RD YEAR DEVELOPMENT PLAN" in blob, f"title missing — got {blob[:200]}"
    assert "PLATE NO. - 5C" in blob, "plate number missing"
    assert "DXF TEST" in blob, "project name missing"
    assert "CERTIFICATION" in blob
    assert "RQP" in blob or "QUALIFIED" in blob


def test_year_dxf_rejects_out_of_range_year(project: dict) -> None:
    with pytest.raises(ValueError):
        compose_year_dxf(project, alternative="base", year=0)
    with pytest.raises(ValueError):
        compose_year_dxf(project, alternative="base", year=99)


def test_auto_prepare_defaults_to_all_eight_alternatives() -> None:
    """The legacy default of just [base, conservative, aggressive] auto-upgrades
    to all 8 strategies on the next auto-prepare."""
    from services.extract import _ensure_engineering_defaults
    # Empty selected_alternatives → all 8
    p = _ensure_engineering_defaults({"project_details": {"area_ha": 4.8}})
    assert len(p["selected_alternatives"]) == 8
    # Legacy default → upgraded to all 8
    p2 = _ensure_engineering_defaults({
        "project_details": {"area_ha": 4.8},
        "selected_alternatives": ["base", "conservative", "aggressive"],
    })
    assert len(p2["selected_alternatives"]) == 8
    # User-curated subset → preserved (not overwritten)
    p3 = _ensure_engineering_defaults({
        "project_details": {"area_ha": 4.8},
        "selected_alternatives": ["base", "low_waste"],
    })
    assert p3["selected_alternatives"] == ["base", "low_waste"]
