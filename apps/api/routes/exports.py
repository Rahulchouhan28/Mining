from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, JSONResponse

import storage
from services.pdf_composer import compose_plate
from services.kml_export import project_to_kml
from services.excel_export import project_to_excel
from services.comparison_pdf import compose_comparison
from services.report_pdf import compose_report
from services.year_plate import compose_year_plate
from services.dxf_export import compose_year_dxf, compose_overview_dxf

router = APIRouter()


def _load(slug: str) -> dict[str, Any]:
    try:
        return storage.load_project(slug)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{slug}/export/geojson")
def export_geojson(slug: str) -> Response:
    project = _load(slug)
    layers = project.get("digitized_layers") or {"type": "FeatureCollection", "features": []}
    body = json.dumps(layers, indent=2)
    return Response(body, media_type="application/geo+json", headers={
        "content-disposition": f'attachment; filename="{slug}.geojson"',
    })


@router.get("/{slug}/export/kml")
def export_kml(slug: str) -> Response:
    project = _load(slug)
    body = project_to_kml(project)
    return Response(body, media_type="application/vnd.google-earth.kml+xml", headers={
        "content-disposition": f'attachment; filename="{slug}.kml"',
    })


@router.get("/{slug}/export/excel")
def export_excel(slug: str) -> Response:
    project = _load(slug)
    body = project_to_excel(project)
    return Response(body, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"content-disposition": f'attachment; filename="{slug}_quantities.xlsx"'})


@router.get("/{slug}/export/pdf")
def export_pdf(
    slug: str,
    alternative: str = Query("base"),
    plate_type: str = Query("year_wise_mining_plan"),
    scale: int = Query(1000, ge=100, le=20000),
    paper: str = Query("A3"),
    orientation: str = Query("landscape"),
) -> Response:
    project = _load(slug)
    try:
        body = compose_plate(project, alternative=alternative, plate_type=plate_type,
                             paper=paper, orientation=orientation, scale=scale)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    # cache to disk too
    exports_dir = storage.project_dir(slug) / "exports"
    filename = f"{plate_type}_{alternative}_1to{scale}.pdf"
    (exports_dir / filename).write_bytes(body)

    return Response(body, media_type="application/pdf", headers={
        "content-disposition": f'attachment; filename="{filename}"',
    })


@router.get("/{slug}/export/year-plate")
def export_year_plate(
    slug: str,
    alternative: str = Query("base"),
    year: int = Query(1, ge=1, le=5),
    paper: str = Query("A3"),
    orientation: str = Query("landscape"),
    scale: int = Query(1000, ge=100, le=20000),
) -> Response:
    """Render the single-year statutory plate for `year` (Plate 5A/5B/...)."""
    project = _load(slug)
    try:
        body = compose_year_plate(project, alternative=alternative, year=year,
                                  paper=paper, orientation=orientation, scale=scale)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    exports_dir = storage.project_dir(slug) / "exports"
    plate_letter = ["", "A", "B", "C", "D", "E"][year]
    filename = f"year_{year}_development_plan_{alternative}_5{plate_letter}.pdf"
    (exports_dir / filename).write_bytes(body)

    return Response(body, media_type="application/pdf", headers={
        "content-disposition": f'attachment; filename="{filename}"',
    })


@router.get("/{slug}/export/year-plates-zip")
def export_year_plates_zip(slug: str, alternative: str = Query("base")) -> Response:
    """All per-year plates for `alternative` bundled into a single ZIP."""
    project = _load(slug)
    details = project.get("project_details") or {}
    plan_years = int(details.get("plan_period_years") or 5)
    plan_years = max(1, min(5, plan_years))

    buf = io.BytesIO()
    plate_letter = ["", "A", "B", "C", "D", "E"]
    failures: list[str] = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for year in range(1, plan_years + 1):
            try:
                pdf = compose_year_plate(project, alternative=alternative, year=year,
                                         paper="A3", orientation="landscape", scale=1000)
                zf.writestr(f"Year_{year}_development_plan_5{plate_letter[year]}.pdf", pdf)
            except Exception as e:  # noqa: BLE001
                failures.append(f"year {year}: {e}")
        zf.writestr("README.txt",
                    f"Per-year statutory plates for: "
                    f"{details.get('project_name', slug)} (approach: {alternative})\n"
                    "Each plate shows that year's pit highlighted with faint outlines\n"
                    "of prior years and a DIRECTION OF NEXT YEAR arrow.\n\n"
                    "Conceptual output. Final statutory submission must be verified\n"
                    "and signed by a qualified mining engineer / RQP / competent person.\n"
                    + (("\nFailures:\n  " + "\n  ".join(failures)) if failures else ""))
    return Response(buf.getvalue(), media_type="application/zip", headers={
        "content-disposition": f'attachment; filename="{slug}_year_plates_{alternative}.zip"',
    })


@router.get("/{slug}/export/year-dxf")
def export_year_dxf(
    slug: str,
    alternative: str = Query("base"),
    year: int = Query(1, ge=1, le=5),
) -> Response:
    """Per-year statutory plate as AutoCAD DXF (R2010, units = meters, UTM 43 N)."""
    project = _load(slug)
    try:
        body = compose_year_dxf(project, alternative=alternative, year=year)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    plate_letter = ["", "A", "B", "C", "D", "E"][year]
    filename = f"year_{year}_development_plan_{alternative}_5{plate_letter}.dxf"
    (storage.project_dir(slug) / "exports" / filename).write_bytes(body)
    return Response(body, media_type="application/vnd.autodesk.dxf", headers={
        "content-disposition": f'attachment; filename="{filename}"',
    })


@router.get("/{slug}/export/overview-dxf")
def export_overview_dxf(slug: str, alternative: str = Query("base")) -> Response:
    """Year-wise overview plate as AutoCAD DXF."""
    project = _load(slug)
    try:
        body = compose_overview_dxf(project, alternative=alternative)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    filename = f"year_wise_overview_{alternative}.dxf"
    (storage.project_dir(slug) / "exports" / filename).write_bytes(body)
    return Response(body, media_type="application/vnd.autodesk.dxf", headers={
        "content-disposition": f'attachment; filename="{filename}"',
    })


@router.get("/{slug}/export/year-dxfs-zip")
def export_year_dxfs_zip(slug: str, alternative: str = Query("base")) -> Response:
    """All per-year DXF plates + overview, bundled into a single ZIP."""
    project = _load(slug)
    details = project.get("project_details") or {}
    plan_years = int(details.get("plan_period_years") or 5)
    plan_years = max(1, min(5, plan_years))

    buf = io.BytesIO()
    plate_letter = ["", "A", "B", "C", "D", "E"]
    failures: list[str] = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for year in range(1, plan_years + 1):
            try:
                dxf = compose_year_dxf(project, alternative=alternative, year=year)
                zf.writestr(f"Year_{year}_development_plan_5{plate_letter[year]}.dxf", dxf)
            except Exception as e:  # noqa: BLE001
                failures.append(f"year {year}: {e}")
        try:
            zf.writestr(f"Year_wise_overview_{alternative}.dxf",
                        compose_overview_dxf(project, alternative=alternative))
        except Exception as e:  # noqa: BLE001
            failures.append(f"overview: {e}")
        zf.writestr("README.txt",
                    "AutoCAD DXF plates (R2010, units = meters, EPSG:32643 UTM 43 N)\n"
                    f"Project: {details.get('project_name', slug)} · approach: {alternative}\n\n"
                    "Open in AutoCAD, BricsCAD, LibreCAD, QCAD, ZWCAD, ProgeCAD, etc.\n"
                    "All layers named per Indian RQP convention (LEASE_BOUNDARY,\n"
                    "BARRIER_7_5M, YEAR_N_WORKING, OB_DUMP_YN, TOPSOIL_YN, PLANTATION_YN,\n"
                    "ULT_PIT_LIMIT, HAUL_ROAD, GARLAND_DRAIN, SETTLING_TANK,\n"
                    "BH_EXISTING, BH_PROPOSED, GRID, TITLE_BLOCK, CERTIFICATION).\n\n"
                    "Conceptual output. Final statutory submission must be verified\n"
                    "and signed by a qualified mining engineer / RQP / competent person.\n"
                    + (("\nFailures:\n  " + "\n  ".join(failures)) if failures else ""))
    return Response(buf.getvalue(), media_type="application/zip", headers={
        "content-disposition": f'attachment; filename="{slug}_year_plates_{alternative}_dxf.zip"',
    })


@router.get("/{slug}/export/comparison-pdf")
def export_comparison_pdf(slug: str) -> Response:
    project = _load(slug)
    try:
        body = compose_comparison(project)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return Response(body, media_type="application/pdf", headers={
        "content-disposition": f'attachment; filename="{slug}_alternative_comparison.pdf"',
    })


@router.get("/{slug}/export/report-pdf")
def export_report_pdf(slug: str) -> Response:
    project = _load(slug)
    body = compose_report(project)
    return Response(body, media_type="application/pdf", headers={
        "content-disposition": f'attachment; filename="{slug}_engineering_report.pdf"',
    })


@router.get("/{slug}/export/zip")
def export_zip(slug: str) -> Response:
    project = _load(slug)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # GIS
        zf.writestr(
            f"GIS/{slug}.geojson",
            json.dumps(project.get("digitized_layers") or {"type": "FeatureCollection", "features": []}, indent=2),
        )
        zf.writestr(f"GIS/{slug}.kml", project_to_kml(project))

        # Excel
        zf.writestr(f"Excel/{slug}_quantities.xlsx", project_to_excel(project))

        # PDF — one per generated alternative
        for plan in project.get("generated_plans") or []:
            alt = plan.get("alternative")
            try:
                pdf_bytes = compose_plate(project, alternative=alt, plate_type="year_wise_mining_plan",
                                          paper="A3", orientation="landscape", scale=1000)
                zf.writestr(f"Maps/year_wise_mining_plan_{alt}.pdf", pdf_bytes)
            except Exception:
                # keep ZIP creation resilient even if one plate fails
                continue

        # Alternative comparison plate
        try:
            zf.writestr("Maps/alternative_comparison.pdf", compose_comparison(project))
        except Exception:
            pass

        # Engineering report
        try:
            zf.writestr("Reports/engineering_report.pdf", compose_report(project))
        except Exception:
            pass

        # Metadata
        zf.writestr("Metadata/project_details.json", json.dumps(project.get("project_details") or {}, indent=2))
        zf.writestr("Metadata/engineering_inputs.json", json.dumps(project.get("engineering_inputs") or {}, indent=2))
        zf.writestr("Metadata/validation_warnings.json", json.dumps(project.get("validation_warnings") or [], indent=2))
        zf.writestr("Metadata/quantity_tables.json", json.dumps(project.get("quantity_tables") or [], indent=2))

        zf.writestr("README.txt",
                    f"Mining Plan output for: {project.get('project_details', {}).get('project_name', slug)}\n"
                    "Conceptual output. Final statutory submission must be verified and signed by a\n"
                    "qualified mining engineer / RQP / competent person.\n")
    return Response(buf.getvalue(), media_type="application/zip", headers={
        "content-disposition": f'attachment; filename="{slug}_mining_plan.zip"',
    })


# Legacy stub kept for backward compatibility with earlier routes table
@router.get("/{slug}/export/{kind}")
def export_unknown(slug: str, kind: str) -> JSONResponse:
    return JSONResponse({"error": f"unknown export kind: {kind}"}, status_code=404)
