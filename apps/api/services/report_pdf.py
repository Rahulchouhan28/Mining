"""Multi-page narrative engineering report PDF (ReportLab).

Sections:
  1. Cover with project details + certification clause
  2. Engineering inputs (with ASSUMED markers)
  3. Quantity tables per alternative
  4. Year-by-year calculation formulas (transparency for the reviewer)
  5. Validation warnings
  6. Glossary of assumptions and the conceptual-output disclaimer

This is a *document*, not a plate — it's intended for the RQP's desk review.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

CERTIFICATION_TEXT = (
    "THIS PLAN IS GENERATED FROM USER-UPLOADED MAPS AND ENGINEERING INPUTS. "
    "FINAL STATUTORY SUBMISSION MUST BE VERIFIED AND SIGNED BY A QUALIFIED "
    "MINING ENGINEER / RQP / COMPETENT PERSON."
)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=18, leading=22, textColor=HexColor("#0f172a")),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, leading=17, textColor=HexColor("#0f172a"), spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontSize=10, leading=13, textColor=HexColor("#0f172a"), spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontSize=9.5, leading=13, textColor=HexColor("#1e293b")),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontSize=8, leading=11, textColor=HexColor("#475569")),
        "cert": ParagraphStyle("cert", parent=base["BodyText"], fontSize=9, leading=12, textColor=HexColor("#7f1d1d"), backColor=HexColor("#fef2f2"), borderColor=HexColor("#b91c1c"), borderWidth=0.8, borderPadding=6),
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=22, leading=28, alignment=TA_CENTER, textColor=HexColor("#0f172a")),
        "subtitle": ParagraphStyle("subtitle", parent=base["BodyText"], fontSize=11, alignment=TA_CENTER, textColor=HexColor("#475569")),
        "label": ParagraphStyle("label", parent=base["BodyText"], fontSize=8, textColor=HexColor("#64748b")),
    }


def _table(rows: list[list[str]], header: bool = True) -> Table:
    t = Table(rows, repeatRows=1 if header else 0, hAlign="LEFT")
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])
    t.setStyle(style)
    return t


def compose_report(project: dict[str, Any]) -> bytes:
    s = _styles()
    details = project.get("project_details") or {}
    ei = project.get("engineering_inputs") or {}
    assumed = set(ei.get("assumed_fields") or [])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"Engineering Report — {details.get('project_name', '')}")
    flow: list[Any] = []

    # ---- Cover ----
    flow.append(Paragraph("YEAR-WISE MINING PLAN", s["title"]))
    flow.append(Paragraph("Engineering report", s["subtitle"]))
    flow.append(Spacer(1, 14 * mm))

    cover_rows = [
        ["Project name",    details.get("project_name", "")],
        ["Applicant",       details.get("applicant_name", "")],
        ["Mineral",         details.get("mineral", "")],
        ["Village / Tehsil / District / State",
            f"{details.get('village','')} / {details.get('tehsil','')} / {details.get('district','')} / {details.get('state','')}"],
        ["Area",            f"{details.get('area_ha', '')} ha"],
        ["Map type",        details.get("map_type", "")],
        ["Scale",           details.get("scale", "")],
        ["Survey date",     details.get("survey_date", "—")],
        ["Plan period",     f"{details.get('plan_period_years', '?')} years"],
        ["Generated",       datetime.now().strftime("%d %b %Y, %H:%M")],
    ]
    flow.append(Table(cover_rows, colWidths=[55 * mm, None], style=TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))
    flow.append(Spacer(1, 14 * mm))
    flow.append(Paragraph("CERTIFICATION", s["h3"]))
    flow.append(Paragraph(CERTIFICATION_TEXT, s["cert"]))

    # ---- Engineering inputs ----
    flow.append(PageBreak())
    flow.append(Paragraph("Engineering inputs", s["h1"]))
    flow.append(Paragraph(
        "Values flagged ASSUMED were filled with conceptual defaults; an RQP "
        "must validate them before statutory submission.", s["small"]))
    flow.append(Spacer(1, 4 * mm))

    sections = [
        ("Production",       "production",          [
            ("annual_production_target_tonnes", "Annual target", "t/y"),
            ("approved_capacity_tonnes_per_year", "Approved capacity", "t/y"),
            ("working_days_per_year", "Working days", "d/y"),
            ("shifts_per_day", "Shifts", "/day"),
            ("hours_per_shift", "Hours / shift", ""),
        ]),
        ("Bench design",     "bench",                [
            ("bench_height_m", "Bench height", "m"),
            ("bench_width_m", "Bench width", "m"),
            ("face_slope_degree", "Face slope", "°"),
            ("overall_pit_slope_degree", "Overall pit slope", "°"),
            ("ultimate_pit_depth_m", "Ultimate pit depth", "m"),
        ]),
        ("Mineral & waste",  "mineral_waste",        [
            ("bulk_density_t_per_m3", "Bulk density", "t/m³"),
            ("topsoil_thickness_m", "Topsoil thickness", "m"),
            ("overburden_thickness_m", "Overburden thickness", "m"),
            ("mineral_recovery_percent", "Recovery", "%"),
            ("reject_percent", "Reject", "%"),
        ]),
    ]
    for title, section_key, fields in sections:
        flow.append(Paragraph(title, s["h2"]))
        rows = [["Parameter", "Value", "Unit", "Status"]]
        section = ei.get(section_key) or {}
        for key, label, unit in fields:
            v = section.get(key)
            tag = "ASSUMED" if f"{section_key}.{key}" in assumed else "—"
            rows.append([label, "—" if v in (None, "") else f"{v}", unit, tag])
        flow.append(_table(rows))

    grade = ei.get("grade") or {}
    if grade:
        flow.append(Paragraph("Grade / chemical analysis", s["h2"]))
        rows = [["Parameter", "Value (%)"]]
        for k, v in grade.items():
            rows.append([k, f"{v}"])
        flow.append(_table(rows))

    # ---- Per-alternative results ----
    flow.append(PageBreak())
    flow.append(Paragraph("Year-wise plan results", s["h1"]))

    for qt in project.get("quantity_tables") or []:
        alt = qt["alternative"]
        flow.append(Paragraph(f"Approach: {alt.replace('_', ' ').upper()}", s["h2"]))
        headers = ["Yr", "Pit (m²)", "Excav. (m³)", "Mineral (m³)", "Mineral (t)",
                   "Saleable (t)", "Topsoil (m³)", "OB (m³)", "Backfill (m³)", "SR"]
        rows = [headers]
        totals = [0.0] * (len(headers) - 1)
        for r in qt.get("rows") or []:
            row = [
                str(r.get("year", "")),
                f"{r.get('pit_area_m2', 0):,.0f}",
                f"{r.get('excavation_volume_m3', 0):,.0f}",
                f"{r.get('mineral_volume_m3', 0):,.0f}",
                f"{r.get('mineral_tonnes', 0):,.0f}",
                f"{r.get('saleable_tonnes', 0):,.0f}",
                f"{r.get('topsoil_m3', 0):,.0f}",
                f"{r.get('overburden_m3', 0):,.0f}",
                f"{r.get('backfill_m3', 0):,.0f}",
                f"{r.get('stripping_ratio', 0):.3f}",
            ]
            rows.append(row)
            for i, key in enumerate(
                ["pit_area_m2", "excavation_volume_m3", "mineral_volume_m3",
                 "mineral_tonnes", "saleable_tonnes", "topsoil_m3", "overburden_m3",
                 "backfill_m3", "stripping_ratio"]):
                totals[i] += (r.get(key) or 0)
        # totals row (skip stripping ratio average — not meaningful)
        rows.append([
            "Σ",
            *[f"{x:,.0f}" for x in totals[:-1]],
            "—",
        ])
        flow.append(_table(rows))
        flow.append(Spacer(1, 4 * mm))

    # ---- Formulas ----
    flow.append(PageBreak())
    flow.append(Paragraph("Calculation formulas", s["h1"]))
    flow.append(Paragraph(
        "All quantities derive from the formulas below (spec Section 6). The "
        "geometric model is an inward-buffer concentric pit slicer in EPSG:32643. "
        "It is conceptual and does not replace a Lerchs-Grossmann / Whittle "
        "block-model optimisation.", s["body"]))
    flow.append(Spacer(1, 3 * mm))
    formulas = [
        "Excavation Volume  =  Pit Area × Bench Height",
        "Mineral Volume      =  Excavation Volume   (one bench → ~all mineral, MWP assumption)",
        "Mineral Tonnage    =  Mineral Volume × Bulk Density",
        "Saleable Mineral   =  ROM × Mineral Recovery %",
        "Topsoil Quantity    =  Disturbed Area × Topsoil Thickness",
        "Overburden Qty.    =  Disturbed Area × OB Thickness",
        "Backfill Volume     =  40 % of Mineral Volume, starting Year 3",
        "Plantation Area      =  10 % of Disturbed Area",
        "Stripping Ratio       =  (Topsoil + OB) / Mineral Volume",
        "7.5 m Statutory Barrier  =  Lease.buffer(−7.5 m, in UTM 43 N)",
    ]
    for line in formulas:
        flow.append(Paragraph(f"<font face='Courier'>{line}</font>", s["body"]))

    # ---- Validation ----
    warnings = project.get("validation_warnings") or []
    if warnings:
        flow.append(PageBreak())
        flow.append(Paragraph("Validation warnings", s["h1"]))
        rows = [["Severity", "Code", "Approach", "Message"]]
        for w in warnings:
            rows.append([
                w.get("severity", ""), w.get("code", ""),
                w.get("alternative", ""), w.get("message", ""),
            ])
        flow.append(_table(rows))

    # ---- Closing certification ----
    flow.append(Spacer(1, 8 * mm))
    flow.append(Paragraph("Final reminder", s["h2"]))
    flow.append(Paragraph(CERTIFICATION_TEXT, s["cert"]))

    doc.build(flow)
    return buf.getvalue()
