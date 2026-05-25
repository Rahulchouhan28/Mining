"""KML / KMZ export via simplekml."""
from __future__ import annotations

from typing import Any

import simplekml
from shapely.geometry import LineString, MultiPolygon, Polygon, shape


COLOR_KML: dict[str, str] = {
    # KML uses ABGR hex
    "lease_boundary":         "ff0a1729",
    "statutory_barrier_7_5m": "802626dc",
    "ultimate_pit_limit":     "ff122d7c",
    "year_pit":               "80aa84fe",
    "overburden_dump":        "8075a5d6",
    "topsoil_stack":          "8024bffb",
    "backfill":               "80356ba3",
    "plantation":             "808fef86",
    "haul_road":              "ff37291f",
    "garland_drain":          "ffc78402",
    "settling_tank":          "807cd37d",
}


def project_to_kml(project: dict[str, Any]) -> str:
    kml = simplekml.Kml()
    details = project.get("project_details") or {}
    kml.document.name = details.get("project_name") or "Mining Plan"

    dig = (project.get("digitized_layers") or {}).get("features") or []
    folder_dig = kml.newfolder(name="Digitized Layers")
    for f in dig:
        _add_feature(folder_dig, f)

    for plan in project.get("generated_plans") or []:
        folder = kml.newfolder(name=f"Generated — {plan.get('alternative', 'plan')}")
        for f in (plan.get("features") or {}).get("features") or []:
            _add_feature(folder, f)

    return kml.kml()


def _add_feature(folder: simplekml.Folder, feat: dict[str, Any]) -> None:
    props = feat.get("properties") or {}
    geom_json = feat.get("geometry")
    if not geom_json:
        return
    try:
        geom = shape(geom_json)
    except Exception:
        return
    layer_type = props.get("layer_type") or "other"
    label_bits = [props.get("label") or layer_type]
    if props.get("year"):
        label_bits.append(f"Year {props['year']}")
    name = " — ".join(label_bits)
    color = COLOR_KML.get(layer_type, "ff333333")

    if isinstance(geom, Polygon):
        _add_polygon(folder, geom, name, color)
    elif isinstance(geom, MultiPolygon):
        for sub in geom.geoms:
            _add_polygon(folder, sub, name, color)
    elif isinstance(geom, LineString):
        ls = folder.newlinestring(name=name, coords=list(geom.coords))
        ls.style.linestyle.color = color
        ls.style.linestyle.width = 2


def _add_polygon(folder: simplekml.Folder, poly: Polygon, name: str, color: str) -> None:
    p = folder.newpolygon(name=name)
    p.outerboundaryis = list(poly.exterior.coords)
    for interior in poly.interiors:
        p.innerboundaryis = [list(interior.coords)]
    p.style.linestyle.color = color
    p.style.linestyle.width = 1.5
    # darker outline, lighter fill (50% alpha)
    if len(color) == 8:
        fill = "80" + color[2:]
    else:
        fill = color
    p.style.polystyle.color = fill
