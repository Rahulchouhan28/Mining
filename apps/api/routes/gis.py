from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from services.projection import geom_to_utm, geom_to_wgs, geojson_to_shape, shape_to_geojson

router = APIRouter()


@router.post("/buffer")
def buffer_polygon(payload: dict[str, Any]) -> dict[str, Any]:
    """Buffer a GeoJSON geometry by `distance_m` METERS in UTM 43N.

    Positive distance grows outward, negative shrinks inward (used for the
    7.5 m statutory barrier: pass distance_m = -7.5).
    """
    geom_json = payload.get("geometry")
    distance_m = payload.get("distance_m")
    if geom_json is None or distance_m is None:
        raise HTTPException(400, "geometry and distance_m are required")

    geom = geojson_to_shape(geom_json)
    geom_utm = geom_to_utm(geom)
    buffered = geom_utm.buffer(float(distance_m))
    if buffered.is_empty:
        return {"geometry": None, "area_m2": 0.0}
    out_wgs = geom_to_wgs(buffered)
    return {
        "geometry": shape_to_geojson(out_wgs),
        "area_m2": buffered.area,
    }


@router.post("/area")
def polygon_area(payload: dict[str, Any]) -> dict[str, float]:
    """Return area of a GeoJSON polygon in m² and hectares (computed in UTM 43N)."""
    geom = geojson_to_shape(payload["geometry"])
    area_m2 = geom_to_utm(geom).area
    return {"area_m2": area_m2, "area_ha": area_m2 / 10_000.0}
