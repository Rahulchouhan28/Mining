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
