"""Borehole CSV importer + KML extraction round-trip."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.extract import (  # noqa: E402
    _boreholes_from_csv,
    _largest_polygon_from_kml,
)


def test_borehole_csv_with_lat_lon_columns() -> None:
    csv = (
        "BH_ID,Lat,Lon,Depth_m,RL\n"
        "BH-01,27.2005,73.6505,15.0,210.4\n"
        "BH-02,27.2010,73.6510,12.5,209.1\n"
        "junk_row,not_a_number,73.65,5,200\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
        fh.write(csv)
        path = Path(fh.name)
    try:
        features = _boreholes_from_csv(path, source="bh.csv")
    finally:
        path.unlink()

    assert len(features) == 2, "should skip the row with invalid lat"
    for f in features:
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "Point"
        assert f["properties"]["layer_type"] == "proposed_borehole"
        assert f["properties"]["auto_extracted"] is True
    # Lon/lat order in GeoJSON
    assert features[0]["geometry"]["coordinates"] == [73.6505, 27.2005]
    # Extra columns kept as bh_* metadata
    assert features[0]["properties"]["bh_depth_m"] == "15.0"


def test_kml_polygon_extraction() -> None:
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>
73.6488,27.1998,0 73.6512,27.1998,0 73.6512,27.2018,0 73.6488,27.2018,0 73.6488,27.1998,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>"""
    poly = _largest_polygon_from_kml(kml.encode("utf-8"))
    assert poly is not None
    minx, miny, maxx, maxy = poly.bounds
    assert abs(minx - 73.6488) < 1e-6 and abs(maxx - 73.6512) < 1e-6
    assert abs(miny - 27.1998) < 1e-6 and abs(maxy - 27.2018) < 1e-6
