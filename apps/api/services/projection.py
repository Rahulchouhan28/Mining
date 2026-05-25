"""Reprojection helpers. Rajasthan lies in EPSG:32643 (UTM zone 43N).

ALWAYS buffer / measure area in UTM, never in EPSG:4326 (degrees). The 7.5 m
statutory barrier in particular is silently wrong if computed in WGS84.
"""
from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

WGS84 = "EPSG:4326"
RAJASTHAN_UTM = "EPSG:32643"

_to_utm = Transformer.from_crs(WGS84, RAJASTHAN_UTM, always_xy=True)
_to_wgs = Transformer.from_crs(RAJASTHAN_UTM, WGS84, always_xy=True)


def geom_to_utm(geom: BaseGeometry) -> BaseGeometry:
    return transform(_to_utm.transform, geom)


def geom_to_wgs(geom: BaseGeometry) -> BaseGeometry:
    return transform(_to_wgs.transform, geom)


def geojson_to_shape(g: dict[str, Any]) -> BaseGeometry:
    return shape(g)


def shape_to_geojson(g: BaseGeometry) -> dict[str, Any]:
    return mapping(g)
