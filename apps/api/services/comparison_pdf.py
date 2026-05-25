"""Alternative-comparison plate (one A3 sheet, all approaches side-by-side).

Useful for stakeholder review: each alternative renders as a small map at the
same scale, with a quantity-delta table below. The certification clause is
preserved verbatim.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from services.pdf_composer import (  # noqa: E402
    CERTIFICATION_TEXT, LAYER_STYLE, YEAR_COLORS, _draw_geom, _geom_to_utm,
)

A3_LANDSCAPE = (16.54, 11.69)


def compose_comparison(project: dict[str, Any]) -> bytes:
    plans = project.get("generated_plans") or []
    if not plans:
        raise ValueError("No generated plans to compare.")

    details = project.get("project_details") or {}
    qtables = {qt["alternative"]: qt for qt in (project.get("quantity_tables") or [])}

    n = len(plans)
    fig = plt.figure(figsize=A3_LANDSCAPE, dpi=200)
    fig.patch.set_facecolor("white")

    border = fig.add_axes((0.02, 0.02, 0.96, 0.96))
    border.axis("off")
    border.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=border.transAxes,
                                        edgecolor="#0f172a", facecolor="none", linewidth=1.5))

    fig.text(0.5, 0.95, f"ALTERNATIVE COMPARISON — {details.get('project_name', '').upper()}",
             ha="center", va="top", fontsize=14, fontweight="bold", color="#0f172a")
    fig.text(0.5, 0.92, f"Area {details.get('area_ha', '?')} ha · plates rendered {datetime.now().strftime('%d-%m-%Y')}",
             ha="center", va="top", fontsize=9, color="#475569")

    # one mini-map per plan, evenly spaced across the top half
    map_top, map_bottom = 0.88, 0.50
    map_width = (0.93 - 0.05) / n
    extents = [_extent_for(plan) for plan in plans]
    # use the largest extent so all minis show the same area
    bx = (min(e[0] for e in extents), min(e[1] for e in extents),
          max(e[2] for e in extents), max(e[3] for e in extents))

    for i, plan in enumerate(plans):
        left = 0.05 + i * map_width
        ax = fig.add_axes((left + 0.005, map_bottom, map_width - 0.012, map_top - map_bottom),
                          projection=ccrs.epsg(32643))
        ax.set_facecolor("#f8fafc")
        pad_x = (bx[2] - bx[0]) * 0.08
        pad_y = (bx[3] - bx[1]) * 0.08
        ax.set_xlim(bx[0] - pad_x, bx[2] + pad_x)
        ax.set_ylim(bx[1] - pad_y, bx[3] + pad_y)
        try:
            gl = ax.gridlines(draw_labels=False, linewidth=0.3, color="#cbd5e1", alpha=0.6)
            gl.top_labels = False; gl.right_labels = False
        except Exception:
            pass

        for feat in plan["features"]["features"]:
            lt = feat["properties"].get("layer_type")
            style = LAYER_STYLE.get(lt)
            if not style:
                continue
            style = dict(style)
            if lt == "year_pit":
                yr = feat["properties"].get("year") or 1
                if 1 <= yr <= len(YEAR_COLORS):
                    style["facecolor"] = YEAR_COLORS[yr - 1]
            _draw_geom(ax, _geom_to_utm(feat["geometry"]), style)
        # also lease
        for feat in (project.get("digitized_layers") or {}).get("features") or []:
            if feat["properties"].get("layer_type") == "lease_boundary":
                _draw_geom(ax, _geom_to_utm(feat["geometry"]), dict(LAYER_STYLE["lease_boundary"]))

        ax.set_title(plan["alternative"].replace("_", " ").upper(),
                     fontsize=10, fontweight="bold", color="#0f172a", pad=6)

    # Quantity-comparison table at the bottom
    ax_tbl = fig.add_axes((0.05, 0.06, 0.90, 0.38))
    ax_tbl.axis("off")
    ax_tbl.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=ax_tbl.transAxes,
                                        edgecolor="#0f172a", facecolor="white", linewidth=0.8))
    ax_tbl.text(0.01, 0.96, "QUANTITY COMPARISON — totals across the plan period",
                fontsize=10, fontweight="bold", color="#0f172a", va="top")

    headers = ["Approach", "Years", "Total saleable (t)", "Cumulative pit (m²)",
               "Total OB (m³)", "Total topsoil (m³)", "Total backfill (m³)"]
    rows: list[list[str]] = []
    for plan in plans:
        alt = plan["alternative"]
        qt = qtables.get(alt, {}).get("rows") or []
        total_saleable = sum(r.get("saleable_tonnes") or 0 for r in qt)
        total_area = sum(r.get("pit_area_m2") or 0 for r in qt)
        total_ob = sum(r.get("overburden_m3") or 0 for r in qt)
        total_ts = sum(r.get("topsoil_m3") or 0 for r in qt)
        total_bf = sum(r.get("backfill_m3") or 0 for r in qt)
        rows.append([
            alt, str(len(qt)),
            f"{total_saleable:,.0f}", f"{total_area:,.0f}",
            f"{total_ob:,.0f}", f"{total_ts:,.0f}", f"{total_bf:,.0f}",
        ])

    table = ax_tbl.table(
        cellText=rows, colLabels=headers, loc="upper left",
        bbox=(0.01, 0.05, 0.98, 0.85),
        cellLoc="right", colLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    # left-align first column
    for r in range(1, len(rows) + 1):
        cell = table[r, 0]
        cell.set_text_props(ha="left", fontweight="bold")
    # header styling
    for c in range(len(headers)):
        cell = table[0, c]
        cell.set_facecolor("#0f172a")
        cell.set_text_props(color="white", fontweight="bold")

    # Certification footer
    cert = fig.add_axes((0.05, 0.005, 0.90, 0.045))
    cert.axis("off")
    cert.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=cert.transAxes,
                                      edgecolor="#b91c1c", facecolor="#fef2f2", linewidth=0.8))
    cert.text(0.01, 0.55, "CERTIFICATION:", fontsize=8, fontweight="bold", color="#b91c1c", va="center")
    cert.text(0.13, 0.55, CERTIFICATION_TEXT, fontsize=7, color="#7f1d1d", va="center")

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches=None, dpi=300)
    plt.close(fig)
    return buf.getvalue()


def _extent_for(plan: dict[str, Any]) -> tuple[float, float, float, float]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for feat in plan["features"]["features"]:
        g = _geom_to_utm(feat["geometry"])
        bx = g.bounds
        minx = min(minx, bx[0]); miny = min(miny, bx[1])
        maxx = max(maxx, bx[2]); maxy = max(maxy, bx[3])
    if minx == float("inf"):
        return (0, 0, 1, 1)
    return (minx, miny, maxx, maxy)
