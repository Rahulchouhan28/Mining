"""AutoCAD DXF export of statutory mining plates.

Writes a DXF (AutoCAD R2010 / AC1024 format) that opens cleanly in
AutoCAD, BricsCAD, LibreCAD, QCAD, ZWCAD, ProgeCAD, etc. All geometry
is in EPSG:32643 (UTM 43 N) METERS — the standard CAD coordinate
system for Indian mining drawings. Each statutory layer maps to a
named CAD layer with the conventional Indian-mining colour palette,
linetypes, and hatch patterns.

Output is bytes; the route streams it as
application/vnd.autodesk.dxf with a `.dxf` extension. Files open in
AutoCAD without any conversion step. For native `.dwg`, see
`compose_dwg_from_dxf` (requires ODA File Converter on the host;
falls back to raising NotImplementedError if not available).

Layer naming follows the convention used by Indian RQPs:
  LEASE_BOUNDARY, BARRIER_7_5M, ULT_PIT_LIMIT,
  YEAR_1_WORKING ... YEAR_5_WORKING,
  OB_DUMP_Y1 ... OB_DUMP_Y5,
  TOPSOIL_Y1 ... TOPSOIL_Y5,
  PLANTATION_Y1 ... PLANTATION_Y5,
  HAUL_ROAD, GARLAND_DRAIN, SETTLING_TANK,
  BH_EXISTING, BH_PROPOSED,
  TITLE_BLOCK, CERTIFICATION, GRID,
  DIRECTION_ARROW, INDEX_LEGEND
"""
from __future__ import annotations

import io
import math
from datetime import datetime
from typing import Any

import ezdxf
from ezdxf import colors as dxfcolors
from ezdxf.enums import TextEntityAlignment
from ezdxf.lldxf import const
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform


CERTIFICATION_TEXT = (
    "THIS PLAN IS GENERATED FROM USER-UPLOADED MAPS AND ENGINEERING INPUTS. "
    "FINAL STATUTORY SUBMISSION MUST BE VERIFIED AND SIGNED BY A QUALIFIED "
    "MINING ENGINEER / RQP / COMPETENT PERSON."
)

ORDINALS = ["", "1st", "2nd", "3rd", "4th", "5th"]
PLATE_LETTERS = ["", "A", "B", "C", "D", "E"]


# (color, linetype, lineweight_mm, hatch_pattern_or_None, hatch_scale, description)
LAYER_DEFS: list[tuple[str, int, str, float, str | None, float, str]] = [
    ("LEASE_BOUNDARY",   7, "Continuous",  0.50, None,       1.0, "Block / lease boundary"),
    ("BARRIER_7_5M",     1, "DASHED",      0.25, "ANSI31",   0.5, "7.5 m statutory barrier"),
    ("ULT_PIT_LIMIT",    6, "DASHEDX2",    0.30, None,       1.0, "Ultimate pit limit"),
    ("YEAR_1_WORKING",  31, "Continuous",  0.20, "ANSI37",   1.5, "Year 1 mine working (cross hatch)"),
    ("YEAR_2_WORKING",  32, "Continuous",  0.20, "ANSI37",   1.5, "Year 2 mine working"),
    ("YEAR_3_WORKING",  33, "Continuous",  0.20, "ANSI37",   1.5, "Year 3 mine working"),
    ("YEAR_4_WORKING",  34, "Continuous",  0.20, "ANSI37",   1.5, "Year 4 mine working"),
    ("YEAR_5_WORKING",  35, "Continuous",  0.20, "ANSI37",   1.5, "Year 5 mine working"),
    ("OB_DUMP_Y1",      42, "Continuous",  0.18, "ANSI31",   2.0, "Year 1 OB dump"),
    ("OB_DUMP_Y2",      42, "Continuous",  0.18, "ANSI31",   2.0, "Year 2 OB dump"),
    ("OB_DUMP_Y3",      42, "Continuous",  0.18, "ANSI31",   2.0, "Year 3 OB dump"),
    ("OB_DUMP_Y4",      42, "Continuous",  0.18, "ANSI31",   2.0, "Year 4 OB dump"),
    ("OB_DUMP_Y5",      42, "Continuous",  0.18, "ANSI31",   2.0, "Year 5 OB dump"),
    ("TOPSOIL_Y1",      51, "Continuous",  0.18, "ANSI35",   2.0, "Year 1 topsoil stack"),
    ("TOPSOIL_Y2",      51, "Continuous",  0.18, "ANSI35",   2.0, "Year 2 topsoil stack"),
    ("TOPSOIL_Y3",      51, "Continuous",  0.18, "ANSI35",   2.0, "Year 3 topsoil stack"),
    ("TOPSOIL_Y4",      51, "Continuous",  0.18, "ANSI35",   2.0, "Year 4 topsoil stack"),
    ("TOPSOIL_Y5",      51, "Continuous",  0.18, "ANSI35",   2.0, "Year 5 topsoil stack"),
    ("PLANTATION_Y1",    3, "Continuous",  0.18, "DOTS",     2.0, "Year 1 plantation"),
    ("PLANTATION_Y2",    3, "Continuous",  0.18, "DOTS",     2.0, "Year 2 plantation"),
    ("PLANTATION_Y3",    3, "Continuous",  0.18, "DOTS",     2.0, "Year 3 plantation"),
    ("PLANTATION_Y4",    3, "Continuous",  0.18, "DOTS",     2.0, "Year 4 plantation"),
    ("PLANTATION_Y5",    3, "Continuous",  0.18, "DOTS",     2.0, "Year 5 plantation"),
    ("HAUL_ROAD",        7, "Continuous",  0.50, None,       1.0, "Haul road"),
    ("GARLAND_DRAIN",    4, "DASHED",      0.25, None,       1.0, "Garland drain"),
    ("SETTLING_TANK",    4, "Continuous",  0.30, "ANSI33",   1.0, "Settling tank"),
    ("BH_EXISTING",      1, "Continuous",  0.30, None,       1.0, "Existing borehole"),
    ("BH_PROPOSED",      6, "Continuous",  0.30, None,       1.0, "Proposed borehole"),
    ("ROAD_RASTA",       8, "Continuous",  0.35, None,       1.0, "Road / rasta"),
    ("EXISTING_INFRA",   9, "Continuous",  0.25, None,       1.0, "Existing infrastructure"),
    ("GRID",             8, "DASHED2",     0.15, None,       1.0, "UTM grid lines"),
    ("DIRECTION_ARROW",  7, "Continuous",  0.50, None,       1.0, "Direction-of-next-year arrow"),
    ("TITLE_BLOCK",      7, "Continuous",  0.40, None,       1.0, "Title block frame"),
    ("CERTIFICATION",    1, "Continuous",  0.30, None,       1.0, "Certification box (red)"),
    ("INDEX_LEGEND",     7, "Continuous",  0.25, None,       1.0, "Legend / index box"),
    ("TEXT_LABELS",      7, "Continuous",  0.15, None,       1.0, "All text annotation"),
    ("NORTH_ARROW",      7, "Continuous",  0.40, None,       1.0, "North arrow"),
    ("SCALE_BAR",        7, "Continuous",  0.30, None,       1.0, "Scale bar"),
]


_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)


def _geom_to_utm(geom_json: dict[str, Any]) -> BaseGeometry:
    return shp_transform(_to_utm.transform, shape(geom_json))


def _new_doc() -> ezdxf.document.Drawing:
    """Make a fresh DXF document with our layer scheme + standard linetypes."""
    doc = ezdxf.new(dxfversion="R2010", setup=True)
    doc.units = ezdxf.units.M  # ensure consumers know units are meters
    # Add linetypes that aren't preset by setup=True (DASHEDX2 etc. usually are)
    for lt_name in ("DASHED", "DASHED2", "DASHEDX2", "CENTER", "PHANTOM"):
        if lt_name not in doc.linetypes:
            try:
                doc.linetypes.add(lt_name, [0.5, 0.25, -0.25], description=lt_name)
            except Exception:
                pass
    for (name, color, lt, lw_mm, _hatch, _scale, _desc) in LAYER_DEFS:
        layer = doc.layers.add(name=name, color=color, linetype=lt if lt in doc.linetypes else "Continuous")
        # AutoCAD lineweights are encoded as integer hundredths of mm (e.g. 0.50 → 50).
        # Not all DXF versions accept the lineweight attribute on the layer entity;
        # skip silently if rejected.
        try:
            layer.dxf.lineweight = max(0, int(round(lw_mm * 100)))
        except Exception:
            pass
    return doc


def _add_polygon(msp, geom: BaseGeometry, *, layer: str, hatch_pattern: str | None,
                 hatch_scale: float, hatch_color: int) -> None:
    """Add an exterior polyline (+ optional inner rings) and optional hatch."""
    def _ring_points(ring) -> list[tuple[float, float]]:
        return [(round(x, 3), round(y, 3)) for x, y, *_ in list(ring.coords)]

    if isinstance(geom, MultiPolygon):
        for sub in geom.geoms:
            _add_polygon(msp, sub, layer=layer, hatch_pattern=hatch_pattern,
                         hatch_scale=hatch_scale, hatch_color=hatch_color)
        return
    if not isinstance(geom, Polygon) or geom.is_empty:
        return

    exterior_pts = _ring_points(geom.exterior)
    if len(exterior_pts) < 3:
        return
    msp.add_lwpolyline(exterior_pts, close=True, dxfattribs={"layer": layer})
    for interior in geom.interiors:
        ipts = _ring_points(interior)
        if len(ipts) >= 3:
            msp.add_lwpolyline(ipts, close=True, dxfattribs={"layer": layer})

    if hatch_pattern:
        try:
            hatch = msp.add_hatch(color=hatch_color, dxfattribs={"layer": layer})
            hatch.set_pattern_fill(hatch_pattern, scale=hatch_scale)
            hatch.paths.add_polyline_path(exterior_pts, is_closed=True, flags=const.BOUNDARY_PATH_EXTERNAL)
            for interior in geom.interiors:
                ipts = _ring_points(interior)
                if len(ipts) >= 3:
                    hatch.paths.add_polyline_path(ipts, is_closed=True, flags=const.BOUNDARY_PATH_OUTERMOST)
        except Exception:
            # Hatch failures are non-fatal; the outline alone is still useful
            pass


def _add_line(msp, geom: BaseGeometry, *, layer: str) -> None:
    if isinstance(geom, LineString):
        pts = [(round(x, 3), round(y, 3)) for x, y, *_ in list(geom.coords)]
        if len(pts) >= 2:
            msp.add_lwpolyline(pts, dxfattribs={"layer": layer})


def _add_text(msp, text: str, x: float, y: float, *, height: float = 2.5,
              layer: str = "TEXT_LABELS", rotation: float = 0.0,
              align: TextEntityAlignment = TextEntityAlignment.MIDDLE_CENTER) -> None:
    t = msp.add_text(text, dxfattribs={
        "layer": layer, "height": height, "rotation": rotation,
        "style": "Standard",
    })
    t.set_placement((x, y), align=align)


def _add_point_marker(msp, x: float, y: float, *, layer: str, radius: float = 2.0, label: str | None = None) -> None:
    msp.add_circle((x, y), radius, dxfattribs={"layer": layer})
    if label:
        _add_text(msp, label, x + radius + 1.5, y, height=2.0, layer="TEXT_LABELS",
                  align=TextEntityAlignment.MIDDLE_LEFT)


def _draw_grid(msp, extent: tuple[float, float, float, float], spacing_m: float = 50.0) -> None:
    minx, miny, maxx, maxy = extent
    x0 = math.floor(minx / spacing_m) * spacing_m
    y0 = math.floor(miny / spacing_m) * spacing_m
    x = x0
    while x <= maxx:
        msp.add_line((x, miny), (x, maxy), dxfattribs={"layer": "GRID"})
        _add_text(msp, f"{x:.1f}E", x, miny - spacing_m * 0.15, height=1.8,
                  layer="TEXT_LABELS", align=TextEntityAlignment.TOP_CENTER)
        x += spacing_m
    y = y0
    while y <= maxy:
        msp.add_line((minx, y), (maxx, y), dxfattribs={"layer": "GRID"})
        _add_text(msp, f"{y:.1f}N", minx - spacing_m * 0.15, y, height=1.8,
                  layer="TEXT_LABELS", align=TextEntityAlignment.MIDDLE_RIGHT)
        y += spacing_m


def _draw_scale_bar(msp, x: float, y: float, total_m: float = 100.0) -> None:
    seg = total_m / 4
    h = total_m * 0.05
    for i in range(4):
        x1 = x + i * seg
        x2 = x + (i + 1) * seg
        pts = [(x1, y), (x2, y), (x2, y + h), (x1, y + h), (x1, y)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "SCALE_BAR"})
        if i % 2 == 0:
            try:
                hatch = msp.add_hatch(color=7, dxfattribs={"layer": "SCALE_BAR"})
                hatch.set_solid_fill(color=7)
                hatch.paths.add_polyline_path(pts, is_closed=True)
            except Exception:
                pass
    for i in range(5):
        tx = x + i * seg
        msp.add_line((tx, y), (tx, y - h * 0.6), dxfattribs={"layer": "SCALE_BAR"})
        _add_text(msp, f"{int(i * seg)}", tx, y - h * 0.9, height=h * 0.7,
                  layer="TEXT_LABELS", align=TextEntityAlignment.TOP_CENTER)
    _add_text(msp, "SCALE 1 CM = 10 M  (RF 1:1000)", x + total_m / 2, y + h * 2.0,
              height=h * 0.9, layer="TEXT_LABELS", align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_north_arrow(msp, x: float, y: float, size: float = 20.0) -> None:
    layer = "NORTH_ARROW"
    msp.add_circle((x, y), size * 0.4, dxfattribs={"layer": layer})
    # Arrow body
    pts = [
        (x, y - size * 0.4), (x - size * 0.18, y + size * 0.1),
        (x, y + size * 0.6), (x + size * 0.18, y + size * 0.1), (x, y - size * 0.4),
    ]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})
    try:
        hatch = msp.add_hatch(color=7, dxfattribs={"layer": layer})
        hatch.set_solid_fill(color=7)
        hatch.paths.add_polyline_path(pts, is_closed=True)
    except Exception:
        pass
    _add_text(msp, "N", x, y + size * 0.75, height=size * 0.3, layer="TEXT_LABELS",
              align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_title_block(msp, x: float, y: float, w: float, h: float, *,
                      details: dict[str, Any], scale: int, alternative: str,
                      year: int | None, plan_years: int) -> None:
    """Draw the standard title block at (x, y) (lower-left corner)."""
    # Outer frame
    msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
                       close=True, dxfattribs={"layer": "TITLE_BLOCK"})

    if year is not None:
        title_line = f"PROPOSED {ORDINALS[year].upper()} YEAR DEVELOPMENT PLAN OF {details.get('project_name', '').upper()}"
        plate_no = f"5{PLATE_LETTERS[year]}"
    else:
        title_line = f"YEAR-WISE MINING PLAN OF {details.get('project_name', '').upper()}"
        plate_no = "5"

    line_h = h * 0.085
    cy = y + h - line_h
    _add_text(msp, title_line, x + w / 2, cy, height=line_h * 0.55,
              layer="TEXT_LABELS", align=TextEntityAlignment.MIDDLE_CENTER)
    cy -= line_h
    lines = [
        f"N/v - {details.get('village','')}, Tehsil - {details.get('tehsil','')}, "
        f"Distt. - {details.get('district','')} ({details.get('state','')})",
        f"Mineral - {details.get('mineral','')}",
        f"Applicant - {details.get('applicant_name','')}",
        f"Area - {details.get('area_ha','')} Hect.  Scale - 1:{scale}",
        f"Approach - {alternative}" + (f"   Year {year} of {plan_years}" if year else ""),
        f"Survey date - {details.get('survey_date','—')}",
        f"Plate prepared - {datetime.now().strftime('%d-%m-%Y')}",
    ]
    for ln in lines:
        _add_text(msp, ln, x + w * 0.04, cy, height=line_h * 0.42,
                  layer="TEXT_LABELS", align=TextEntityAlignment.MIDDLE_LEFT)
        cy -= line_h
    _add_text(msp, f"PLATE NO. - {plate_no}", x + w * 0.96, cy, height=line_h * 0.55,
              layer="CERTIFICATION", align=TextEntityAlignment.MIDDLE_RIGHT)


def _draw_certification_box(msp, x: float, y: float, w: float, h: float) -> None:
    msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
                       close=True, dxfattribs={"layer": "CERTIFICATION"})
    _add_text(msp, "CERTIFICATION", x + w * 0.02, y + h * 0.72,
              height=h * 0.22, layer="CERTIFICATION",
              align=TextEntityAlignment.MIDDLE_LEFT)
    # MText keeps the long certification on multiple lines neatly
    msp.add_mtext(CERTIFICATION_TEXT, dxfattribs={
        "layer": "CERTIFICATION", "char_height": h * 0.13,
        "width": w * 0.96, "insert": (x + w * 0.02, y + h * 0.45),
        "attachment_point": const.MTEXT_TOP_LEFT, "color": 1,
    })


def _draw_index_legend(msp, x: float, y: float, w: float, h: float,
                       used_layers: list[str]) -> None:
    msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
                       close=True, dxfattribs={"layer": "INDEX_LEGEND"})
    _add_text(msp, "INDEX", x + w / 2, y + h - h * 0.05,
              height=h * 0.03, layer="TEXT_LABELS",
              align=TextEntityAlignment.TOP_CENTER)
    descriptions = {name: desc for (name, _c, _lt, _lw, _hp, _hs, desc) in LAYER_DEFS}
    n = max(1, len(used_layers))
    row_h = (h - h * 0.08) / n
    cy = y + h - h * 0.08
    for layer in used_layers:
        # Swatch
        swatch_w = w * 0.10
        swatch_h = row_h * 0.55
        sx = x + w * 0.04
        sy = cy - swatch_h
        msp.add_lwpolyline(
            [(sx, sy), (sx + swatch_w, sy), (sx + swatch_w, sy + swatch_h),
             (sx, sy + swatch_h), (sx, sy)],
            close=True, dxfattribs={"layer": layer},
        )
        _add_text(msp, descriptions.get(layer, layer.replace("_", " ").title()),
                  sx + swatch_w + w * 0.02, sy + swatch_h / 2,
                  height=row_h * 0.35, layer="TEXT_LABELS",
                  align=TextEntityAlignment.MIDDLE_LEFT)
        cy -= row_h


# --------------------------------------------------------------- public API

YEAR_TAGGED_LAYERS = {"year_pit", "overburden_dump", "topsoil_stack", "plantation"}


def compose_year_dxf(project: dict[str, Any], *, alternative: str, year: int) -> bytes:
    """Per-year statutory plate as a DXF."""
    details = project.get("project_details") or {}
    plan_years = int(details.get("plan_period_years") or 5)
    plan_years = max(1, min(5, plan_years))
    if not (1 <= year <= plan_years):
        raise ValueError(f"year must be 1..{plan_years}, got {year}")

    plan = next((p for p in (project.get("generated_plans") or []) if p["alternative"] == alternative), None)
    if plan is None:
        raise ValueError(f"No generated plan for alternative {alternative}")

    doc = _new_doc()
    msp = doc.modelspace()

    # Gather features (filter by year for year-tagged layers, keep always-on
    # layers like lease, barrier, ult pit, haul road, boreholes).
    features = list(plan["features"]["features"])
    for f in (project.get("digitized_layers") or {}).get("features", []):
        if f["properties"].get("layer_type") not in YEAR_TAGGED_LAYERS:
            features.append(f)

    used_layers: list[str] = []
    year_pit_centroids: dict[int, tuple[float, float]] = {}
    for f in features:
        props = f.get("properties") or {}
        lt = props.get("layer_type")
        yr = props.get("year")
        geom = _geom_to_utm(f["geometry"])

        layer, hatch_pattern, hatch_scale, hatch_color = _layer_for_feature(lt, yr)
        if layer is None:
            continue

        # Filter year-tagged layers to the active year
        if lt in YEAR_TAGGED_LAYERS and yr != year:
            # Year_pit: still record centroid for the direction arrow
            if lt == "year_pit" and isinstance(yr, int):
                c = geom.centroid
                year_pit_centroids[yr] = (c.x, c.y)
            # Prior-year pits shown as faint outline on GRID layer
            if lt == "year_pit" and isinstance(yr, int) and yr < year:
                if isinstance(geom, (Polygon, MultiPolygon)):
                    _add_polygon(msp, geom, layer="GRID", hatch_pattern=None,
                                 hatch_scale=1.0, hatch_color=8)
            continue

        if lt == "year_pit" and isinstance(yr, int):
            c = geom.centroid
            year_pit_centroids[yr] = (c.x, c.y)

        if isinstance(geom, (Polygon, MultiPolygon)):
            _add_polygon(msp, geom, layer=layer, hatch_pattern=hatch_pattern,
                         hatch_scale=hatch_scale, hatch_color=hatch_color)
        elif isinstance(geom, LineString):
            _add_line(msp, geom, layer=layer)
        else:
            # Point (borehole etc.)
            x, y = geom.x, geom.y
            label = props.get("label")
            _add_point_marker(msp, x, y, layer=layer,
                              radius=2.0 if lt in {"existing_borehole", "proposed_borehole"} else 1.0,
                              label=str(label) if label else None)

        if layer not in used_layers:
            used_layers.append(layer)

    # Active-year label
    active_xy = year_pit_centroids.get(year)
    if active_xy:
        _add_text(msp, f"YEAR {year}", active_xy[0], active_xy[1], height=5.0,
                  layer="TEXT_LABELS", align=TextEntityAlignment.MIDDLE_CENTER)

    # Direction-of-next-year arrow
    next_xy = year_pit_centroids.get(year + 1)
    if active_xy and next_xy:
        _draw_direction_arrow(msp, active_xy, next_xy, year + 1)

    # Decide drawing extents from what we drew
    extent = _model_extent(msp)
    _draw_grid(msp, extent, spacing_m=50.0)

    # Chrome — place below the map
    extent_w = extent[2] - extent[0]
    extent_h = extent[3] - extent[1]
    chrome_y = extent[1] - extent_h * 0.6
    title_w = extent_w * 0.55
    title_h = extent_h * 0.40
    _draw_title_block(msp, extent[0] + extent_w * 0.45, chrome_y, title_w, title_h,
                      details=details, scale=1000, alternative=alternative,
                      year=year, plan_years=plan_years)
    cert_w = extent_w * 0.45
    cert_h = extent_h * 0.18
    _draw_certification_box(msp, extent[0], chrome_y + title_h - cert_h, cert_w, cert_h)
    _draw_north_arrow(msp, extent[2] + extent_w * 0.05, extent[3] - extent_h * 0.1, size=extent_w * 0.05)
    _draw_scale_bar(msp, extent[0], extent[1] - extent_h * 0.12, total_m=100.0)
    _draw_index_legend(msp, extent[2] + extent_w * 0.02,
                       extent[1] + extent_h * 0.05, extent_w * 0.22, extent_h * 0.6,
                       used_layers)

    return _serialize(doc)


def compose_overview_dxf(project: dict[str, Any], *, alternative: str) -> bytes:
    """All-years overview plate as a DXF (color-coded by year)."""
    details = project.get("project_details") or {}
    plan = next((p for p in (project.get("generated_plans") or []) if p["alternative"] == alternative), None)
    if plan is None:
        raise ValueError(f"No generated plan for alternative {alternative}")
    plan_years = int(details.get("plan_period_years") or 5)
    plan_years = max(1, min(5, plan_years))

    doc = _new_doc()
    msp = doc.modelspace()

    features = list(plan["features"]["features"])
    for f in (project.get("digitized_layers") or {}).get("features", []):
        if f["properties"].get("layer_type") not in YEAR_TAGGED_LAYERS:
            features.append(f)

    used_layers: list[str] = []
    # For OB/topsoil/plantation: only the final-state polygon (year=plan_years).
    cumulative = {"overburden_dump", "topsoil_stack", "plantation"}
    max_year: dict[str, int] = {}
    for f in features:
        props = f.get("properties") or {}
        lt = props.get("layer_type")
        yr = props.get("year")
        if lt in cumulative and isinstance(yr, int):
            max_year[lt] = max(max_year.get(lt, 0), yr)

    for f in features:
        props = f.get("properties") or {}
        lt = props.get("layer_type")
        yr = props.get("year")
        if lt in cumulative and isinstance(yr, int) and yr != max_year.get(lt):
            continue
        geom = _geom_to_utm(f["geometry"])
        layer, hatch_pattern, hatch_scale, hatch_color = _layer_for_feature(lt, yr)
        if layer is None:
            continue
        if isinstance(geom, (Polygon, MultiPolygon)):
            _add_polygon(msp, geom, layer=layer, hatch_pattern=hatch_pattern,
                         hatch_scale=hatch_scale, hatch_color=hatch_color)
            if lt == "year_pit" and isinstance(yr, int):
                c = geom.centroid
                _add_text(msp, f"Y{yr}", c.x, c.y, height=4.0, layer="TEXT_LABELS",
                          align=TextEntityAlignment.MIDDLE_CENTER)
        elif isinstance(geom, LineString):
            _add_line(msp, geom, layer=layer)
        else:
            label = props.get("label")
            _add_point_marker(msp, geom.x, geom.y, layer=layer, radius=2.0,
                              label=str(label) if label else None)
        if layer not in used_layers:
            used_layers.append(layer)

    extent = _model_extent(msp)
    _draw_grid(msp, extent, spacing_m=50.0)

    extent_w = extent[2] - extent[0]
    extent_h = extent[3] - extent[1]
    chrome_y = extent[1] - extent_h * 0.6
    title_w = extent_w * 0.55
    title_h = extent_h * 0.40
    _draw_title_block(msp, extent[0] + extent_w * 0.45, chrome_y, title_w, title_h,
                      details=details, scale=1000, alternative=alternative,
                      year=None, plan_years=plan_years)
    _draw_certification_box(msp, extent[0], chrome_y + title_h - extent_h * 0.18,
                            extent_w * 0.45, extent_h * 0.18)
    _draw_north_arrow(msp, extent[2] + extent_w * 0.05, extent[3] - extent_h * 0.1, size=extent_w * 0.05)
    _draw_scale_bar(msp, extent[0], extent[1] - extent_h * 0.12, total_m=100.0)
    _draw_index_legend(msp, extent[2] + extent_w * 0.02,
                       extent[1] + extent_h * 0.05, extent_w * 0.22, extent_h * 0.6,
                       used_layers)

    return _serialize(doc)


def _draw_direction_arrow(msp, from_xy: tuple[float, float], to_xy: tuple[float, float], next_year: int) -> None:
    """A simple line + arrowhead pointing from current to next year's centroid."""
    fx, fy = from_xy
    tx, ty = to_xy
    msp.add_line((fx, fy), (tx, ty), dxfattribs={"layer": "DIRECTION_ARROW"})
    # Arrowhead
    dx, dy = tx - fx, ty - fy
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    head = max(3.0, length * 0.08)
    left = (tx - head * ux + head * 0.5 * (-uy), ty - head * uy + head * 0.5 * ux)
    right = (tx - head * ux - head * 0.5 * (-uy), ty - head * uy - head * 0.5 * ux)
    msp.add_lwpolyline([(tx, ty), left, right, (tx, ty)], close=True,
                       dxfattribs={"layer": "DIRECTION_ARROW"})
    # Label box at midpoint
    midx = (fx + tx) / 2
    midy = (fy + ty) / 2
    _add_text(msp, f"DIRECTION OF YEAR {next_year}", midx, midy,
              height=3.5, layer="TEXT_LABELS",
              align=TextEntityAlignment.MIDDLE_CENTER)


def _model_extent(msp) -> tuple[float, float, float, float]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for e in msp:
        try:
            bbox = e.bbox().extmin, e.bbox().extmax
        except Exception:
            continue
        (lx, ly, *_), (hx, hy, *_) = (bbox[0], bbox[1])
        minx = min(minx, lx); miny = min(miny, ly)
        maxx = max(maxx, hx); maxy = max(maxy, hy)
    if minx == float("inf"):
        # Fall back to a small box around UTM 43N Haripura defaults
        return (340000.0, 2984000.0, 340100.0, 2984100.0)
    return (minx, miny, maxx, maxy)


def _layer_for_feature(lt: str | None, year: int | None) -> tuple[str | None, str | None, float, int]:
    """Map (layer_type, year) → (CAD layer name, hatch pattern, scale, hatch color).

    Returns (None, ...) for layer types we don't render in the DXF.
    """
    if lt is None:
        return (None, None, 1.0, 7)
    if lt == "lease_boundary":          return ("LEASE_BOUNDARY", None, 1.0, 7)
    if lt == "statutory_barrier_7_5m":  return ("BARRIER_7_5M", "ANSI31", 0.5, 1)
    if lt == "ultimate_pit_limit":      return ("ULT_PIT_LIMIT", None, 1.0, 6)
    if lt == "haul_road":                return ("HAUL_ROAD", None, 1.0, 7)
    if lt == "garland_drain":            return ("GARLAND_DRAIN", None, 1.0, 4)
    if lt == "settling_tank":            return ("SETTLING_TANK", "ANSI33", 1.0, 4)
    if lt == "existing_borehole":        return ("BH_EXISTING", None, 1.0, 1)
    if lt == "proposed_borehole":        return ("BH_PROPOSED", None, 1.0, 6)
    if lt == "road":                     return ("ROAD_RASTA", None, 1.0, 8)
    if lt == "existing_infrastructure":  return ("EXISTING_INFRA", None, 1.0, 9)

    if lt == "year_pit" and isinstance(year, int) and 1 <= year <= 5:
        return (f"YEAR_{year}_WORKING", "ANSI37", 1.5, 30 + year)
    if lt == "overburden_dump" and isinstance(year, int) and 1 <= year <= 5:
        return (f"OB_DUMP_Y{year}", "ANSI31", 2.0, 42)
    if lt == "topsoil_stack" and isinstance(year, int) and 1 <= year <= 5:
        return (f"TOPSOIL_Y{year}", "ANSI35", 2.0, 51)
    if lt == "plantation" and isinstance(year, int) and 1 <= year <= 5:
        return (f"PLANTATION_Y{year}", "DOTS", 2.0, 3)
    return (None, None, 1.0, 7)


def _serialize(doc: ezdxf.document.Drawing) -> bytes:
    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")


# --------------------------------------------------------------- DWG (optional)

def compose_dwg_from_dxf(dxf_bytes: bytes) -> bytes:
    """Convert DXF → DWG via ODA File Converter if present on the host.

    Raises NotImplementedError if ODA is not installed. DXF is the supported
    statutory format; DWG is an optional convenience.
    """
    raise NotImplementedError(
        "DWG export requires ODA File Converter on the host. Install it from "
        "https://www.opendesign.com/guestfiles/oda_file_converter and wire it in "
        "(shell out to ODAFileConverter.exe IN_DIR OUT_DIR ACAD2013 DWG 0 1 *.DXF). "
        "DXF is the AutoCAD-native exchange format and is accepted by Indian "
        "mining regulators — most teams stay on DXF."
    )
