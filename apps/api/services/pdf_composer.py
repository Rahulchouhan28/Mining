"""A3 statutory-style PDF plate composer (spec Section 8).

Renders a complete cartographic plate at fixed scale using Matplotlib +
Cartopy in EPSG:32643. The output is a true vector PDF; scale bar accuracy
is preserved because the axes extent is computed from the requested scale.
"""
from __future__ import annotations

import io
import math
from datetime import datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.geometry import LineString, MultiPolygon, Polygon, shape  # noqa: E402

CERTIFICATION_TEXT = (
    "THIS PLAN IS GENERATED FROM USER-UPLOADED MAPS AND ENGINEERING INPUTS. "
    "FINAL STATUTORY SUBMISSION MUST BE VERIFIED AND SIGNED BY A QUALIFIED "
    "MINING ENGINEER / RQP / COMPETENT PERSON."
)

# Layer styling matches frontend LAYER_STYLES (kept in sync manually for v1).
LAYER_STYLE: dict[str, dict[str, Any]] = {
    "lease_boundary":         {"edgecolor": "#0f172a", "facecolor": "none",     "linewidth": 1.4, "zorder": 5},
    "statutory_barrier_7_5m": {"edgecolor": "#dc2626", "facecolor": "#dc2626",  "linewidth": 0.7, "alpha": 0.18, "linestyle": (0, (4, 2)), "zorder": 4},
    "ultimate_pit_limit":     {"edgecolor": "#7c2d12", "facecolor": "none",     "linewidth": 1.0, "linestyle": (0, (6, 2)), "zorder": 6},
    "year_pit":               {"edgecolor": "#9a3412", "facecolor": "#fed7aa",  "linewidth": 0.6, "alpha": 0.55, "zorder": 7},
    "overburden_dump":        {"edgecolor": "#78350f", "facecolor": "#d6a575",  "linewidth": 0.5, "alpha": 0.6,  "hatch": "//",  "zorder": 4},
    "topsoil_stack":          {"edgecolor": "#92400e", "facecolor": "#fbbf24",  "linewidth": 0.5, "alpha": 0.6,  "hatch": "\\\\",  "zorder": 4},
    "backfill":               {"edgecolor": "#365314", "facecolor": "#a3e635",  "linewidth": 0.5, "alpha": 0.55, "hatch": "..", "zorder": 5},
    "plantation":             {"edgecolor": "#166534", "facecolor": "#86efac",  "linewidth": 0.5, "alpha": 0.7,  "hatch": "++", "zorder": 5},
    "haul_road":              {"edgecolor": "#1f2937", "facecolor": "none",     "linewidth": 1.8, "zorder": 6},
    "garland_drain":          {"edgecolor": "#0284c7", "facecolor": "none",     "linewidth": 1.0, "linestyle": (0, (4, 2)), "zorder": 5},
    "settling_tank":          {"edgecolor": "#0369a1", "facecolor": "#7dd3fc",  "linewidth": 0.7, "alpha": 0.6,  "zorder": 5},
    "mineral_stack_yard":     {"edgecolor": "#7e22ce", "facecolor": "#d8b4fe",  "linewidth": 0.7, "alpha": 0.6,  "zorder": 5},
}

# Year-specific colors (override the generic year_pit fill).
YEAR_COLORS = ["#fde68a", "#fdba74", "#fb923c", "#f97316", "#ea580c"]

LAYER_LABEL: dict[str, str] = {
    "lease_boundary": "Lease Boundary",
    "statutory_barrier_7_5m": "7.5 m Statutory Barrier",
    "ultimate_pit_limit": "Ultimate Pit Limit",
    "year_pit": "Year Pit (year-coded)",
    "overburden_dump": "Overburden Dump",
    "topsoil_stack": "Topsoil Stack",
    "backfill": "Backfill",
    "plantation": "Plantation",
    "haul_road": "Haul Road",
    "garland_drain": "Garland Drain",
    "settling_tank": "Settling Tank",
    "mineral_stack_yard": "Mineral Stack Yard",
}

PAPER_INCHES: dict[str, tuple[float, float]] = {
    "A4_landscape":  (11.69,  8.27),
    "A4_portrait":   ( 8.27, 11.69),
    "A3_landscape":  (16.54, 11.69),
    "A3_portrait":   (11.69, 16.54),
    "A2_landscape":  (23.39, 16.54),
}

_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)


def _geom_to_utm(geom_json: dict[str, Any]):
    g = shape(geom_json)
    from shapely.ops import transform
    return transform(_to_utm.transform, g)


def _polygon_path(poly: Polygon) -> MplPath:
    exterior = list(poly.exterior.coords)
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(exterior) - 2) + [MplPath.CLOSEPOLY]
    verts = list(exterior)
    for interior in poly.interiors:
        interior_coords = list(interior.coords)
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(interior_coords) - 2) + [MplPath.CLOSEPOLY]
        verts += interior_coords
    return MplPath(verts, codes)


def _draw_geom(ax, geom, style: dict[str, Any]) -> None:
    if isinstance(geom, Polygon):
        patch = PathPatch(_polygon_path(geom), **style)
        ax.add_patch(patch)
    elif isinstance(geom, MultiPolygon):
        for sub in geom.geoms:
            _draw_geom(ax, sub, style)
    elif isinstance(geom, LineString):
        xs, ys = zip(*list(geom.coords))
        line_style = {
            "color": style.get("edgecolor", "#0f172a"),
            "linewidth": style.get("linewidth", 1.0),
            "linestyle": style.get("linestyle", "-"),
            "zorder": style.get("zorder", 1),
        }
        ax.plot(xs, ys, **line_style)


def _draw_north_arrow(fig, x_norm: float, y_norm: float) -> None:
    ax = fig.add_axes((x_norm, y_norm, 0.04, 0.06))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.add_patch(mpatches.FancyArrow(0.5, 0.15, 0, 0.6, width=0.04, head_width=0.25,
                                     head_length=0.18, fc="#0f172a", ec="#0f172a"))
    ax.text(0.5, -0.05, "N", ha="center", va="top", fontsize=10, fontweight="bold")


def _draw_scale_bar(ax, length_m: float, label: str) -> None:
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    pad_x = (xmax - xmin) * 0.04
    pad_y = (ymax - ymin) * 0.04
    x0 = xmin + pad_x
    y0 = ymin + pad_y
    segs = 4
    seg_len = length_m / segs
    for i in range(segs):
        color = "#0f172a" if i % 2 == 0 else "#ffffff"
        ax.add_patch(mpatches.Rectangle((x0 + i * seg_len, y0), seg_len, length_m * 0.05,
                                        edgecolor="#0f172a", facecolor=color, linewidth=0.8, zorder=10))
    for i in range(segs + 1):
        tick_x = x0 + i * seg_len
        ax.plot([tick_x, tick_x], [y0, y0 - length_m * 0.02], color="#0f172a", linewidth=0.8, zorder=10)
        ax.text(tick_x, y0 - length_m * 0.035, f"{int(i * seg_len)}", ha="center", va="top",
                fontsize=7, zorder=10)
    ax.text(x0 + length_m * 0.5, y0 + length_m * 0.08, label, ha="center", va="bottom",
            fontsize=8, fontweight="bold", zorder=10)


def _draw_title_block(fig, details: dict[str, Any], scale: int, alternative: str, plate_type: str) -> None:
    ax = fig.add_axes((0.62, 0.04, 0.36, 0.22))
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                                    edgecolor="#0f172a", facecolor="white", linewidth=1.2))
    lines = [
        f"{plate_type.replace('_', ' ').upper()} OF {details.get('project_name', '').upper()}",
        f"N/v – {details.get('village', '')}, Tehsil – {details.get('tehsil', '')}, Distt. – {details.get('district', '')} ({details.get('state', '')})",
        f"Mineral – {details.get('mineral', '')}",
        f"Applicant – {details.get('applicant_name', '')}",
        f"Area – {details.get('area_ha', '')} Hect.",
        f"Scale – 1:{scale}",
        f"Alternative – {alternative}",
        f"Survey date – {details.get('survey_date', '—')}",
        f"Plate prepared – {datetime.now().strftime('%d-%m-%Y')}",
    ]
    y = 0.93
    for i, ln in enumerate(lines):
        ax.text(0.04, y, ln, transform=ax.transAxes,
                fontsize=9 if i > 0 else 10,
                fontweight="bold" if i == 0 else "normal",
                va="top")
        y -= 0.10


def _draw_certification(fig) -> None:
    ax = fig.add_axes((0.04, 0.04, 0.55, 0.10))
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                                    edgecolor="#b91c1c", facecolor="#fef2f2", linewidth=1.0))
    ax.text(0.02, 0.85, "CERTIFICATION", transform=ax.transAxes,
            fontsize=9, fontweight="bold", color="#b91c1c", va="top")
    ax.text(0.02, 0.65, CERTIFICATION_TEXT, transform=ax.transAxes,
            fontsize=7.5, color="#7f1d1d", va="top", wrap=True)


def _draw_legend(fig, used_keys: list[str]) -> None:
    handles = []
    labels = []
    for k in used_keys:
        st = LAYER_STYLE.get(k)
        if not st:
            continue
        if k == "year_pit":
            for i, col in enumerate(YEAR_COLORS):
                handles.append(mpatches.Patch(facecolor=col, edgecolor="#9a3412", linewidth=0.6))
                labels.append(f"Year {i + 1} Pit")
            continue
        if "facecolor" in st and st["facecolor"] != "none":
            handles.append(mpatches.Patch(
                facecolor=st["facecolor"],
                edgecolor=st["edgecolor"],
                alpha=st.get("alpha", 1.0),
                hatch=st.get("hatch"),
                linewidth=st.get("linewidth", 1),
            ))
        else:
            handles.append(Line2D([], [], color=st["edgecolor"], linewidth=st["linewidth"],
                                  linestyle=st.get("linestyle", "-")))
        labels.append(LAYER_LABEL.get(k, k))
    ax = fig.add_axes((0.84, 0.28, 0.14, 0.58))
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                                    edgecolor="#475569", facecolor="white", linewidth=0.8))
    ax.text(0.5, 0.97, "LEGEND", transform=ax.transAxes, fontsize=10, fontweight="bold",
            ha="center", va="top")
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.05, 0.93),
              frameon=False, fontsize=7.5, handlelength=2, labelspacing=0.6)


def _compute_extent(features_utm, paper_inches, scale: int) -> tuple[float, float, float, float]:
    minx = min(g.bounds[0] for g in features_utm)
    miny = min(g.bounds[1] for g in features_utm)
    maxx = max(g.bounds[2] for g in features_utm)
    maxy = max(g.bounds[3] for g in features_utm)

    # Map axes occupies ~58% width x ~70% height of the paper (rest is title/legend/cert)
    map_w_in = paper_inches[0] * 0.58
    map_h_in = paper_inches[1] * 0.70
    map_w_m = map_w_in * 0.0254 * scale
    map_h_m = map_h_in * 0.0254 * scale

    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    pad_w = max(map_w_m, (maxx - minx) * 1.15) / 2
    pad_h = max(map_h_m, (maxy - miny) * 1.15) / 2
    return cx - pad_w, cy - pad_h, cx + pad_w, cy + pad_h


def compose_plate(
    project: dict[str, Any],
    *,
    alternative: str,
    plate_type: str = "year_wise_mining_plan",
    paper: str = "A3",
    orientation: str = "landscape",
    scale: int = 1000,
) -> bytes:
    """Render an A3 landscape statutory-style plate and return PDF bytes."""
    key = f"{paper}_{orientation}"
    if key not in PAPER_INCHES:
        raise ValueError(f"Unsupported paper/orientation: {key}")
    fig_size = PAPER_INCHES[key]

    details = project.get("project_details") or {}

    # Collect features for this alternative
    plan = next((p for p in (project.get("generated_plans") or []) if p["alternative"] == alternative), None)
    if plan is None:
        raise ValueError(f"No generated plan for alternative {alternative}")
    features = list(plan["features"]["features"])
    for f in (project.get("digitized_layers") or {}).get("features", []):
        if f["properties"]["layer_type"] == "lease_boundary":
            features.append(f)

    if not features:
        raise ValueError("No features to plot.")

    # Convert each feature to UTM 43N
    utm_features = []
    for f in features:
        try:
            utm_features.append((f["properties"], _geom_to_utm(f["geometry"])))
        except Exception:
            continue

    fig = plt.figure(figsize=fig_size, dpi=200)
    fig.patch.set_facecolor("white")

    # Page border
    border_ax = fig.add_axes((0.02, 0.02, 0.96, 0.96))
    border_ax.axis("off")
    border_ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=border_ax.transAxes,
                                           edgecolor="#0f172a", facecolor="none", linewidth=1.5))

    # Map axes — Cartopy UTM 43 N projection
    ax = fig.add_axes((0.04, 0.28, 0.78, 0.66), projection=ccrs.epsg(32643))
    ax.set_facecolor("#f8fafc")
    extent = _compute_extent([g for (_, g) in utm_features], fig_size, scale)
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])

    # Graticule (light grey grid)
    try:
        gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="#94a3b8", alpha=0.7)
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {"size": 7, "color": "#475569"}
        gl.ylabel_style = {"size": 7, "color": "#475569"}
    except Exception:
        pass

    used_keys: list[str] = []
    year_idx = 0
    for props, geom in utm_features:
        lt = props.get("layer_type")
        if lt not in LAYER_STYLE:
            continue
        style = dict(LAYER_STYLE[lt])
        if lt == "year_pit":
            yr = props.get("year")
            if yr and 1 <= yr <= len(YEAR_COLORS):
                style["facecolor"] = YEAR_COLORS[yr - 1]
            else:
                style["facecolor"] = YEAR_COLORS[year_idx % len(YEAR_COLORS)]
                year_idx += 1
        _draw_geom(ax, geom, style)
        if lt not in used_keys:
            used_keys.append(lt)

    # Year labels on year_pit polygons
    for props, geom in utm_features:
        if props.get("layer_type") == "year_pit" and props.get("year"):
            c = geom.centroid
            ax.text(c.x, c.y, f"Y{props['year']}", fontsize=9, fontweight="bold",
                    color="#7c2d12", ha="center", va="center", zorder=20)

    # Title and chrome
    ax.set_title(f"{plate_type.replace('_', ' ').upper()} — Scale 1:{scale}",
                 fontsize=12, fontweight="bold", color="#0f172a", pad=10)

    # Scale bar — pick a round length, ~1/5 of the map width
    map_width_m = extent[2] - extent[0]
    raw = map_width_m * 0.18
    round_m = _round_scale_length(raw)
    _draw_scale_bar(ax, round_m, f"{int(round_m)} m")

    _draw_north_arrow(fig, x_norm=0.045, y_norm=0.88)
    _draw_legend(fig, used_keys)
    _draw_title_block(fig, details, scale, alternative, plate_type)
    _draw_certification(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches=None, dpi=300)
    plt.close(fig)
    return buf.getvalue()


def _round_scale_length(raw_m: float) -> float:
    if raw_m <= 0:
        return 100.0
    exp = math.floor(math.log10(raw_m))
    base = raw_m / (10 ** exp)
    if base < 1.5:
        nice = 1
    elif base < 3.5:
        nice = 2
    elif base < 7.5:
        nice = 5
    else:
        nice = 10
    return nice * (10 ** exp)
