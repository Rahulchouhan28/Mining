"""Plan verification: a 100 m × 100 m square buffered by -7.5 m round-trips
correctly through WGS84 ↔ UTM 43N. This is the canary for the projection
plumbing — if this passes, the 7.5 m statutory barrier is trustworthy.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `import services.*` when pytest invoked from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.projection import geom_to_utm, geom_to_wgs  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402


def test_75m_barrier_round_trip() -> None:
    # Origin near Haripura, Rajasthan: roughly 27.20°N, 73.65°E
    # Build a ~100m square in UTM 43N, hop to WGS84, back, then buffer -7.5
    base_utm = Polygon([(700_000, 3_010_000), (700_100, 3_010_000),
                        (700_100, 3_010_100), (700_000, 3_010_100)])
    as_wgs = geom_to_wgs(base_utm)
    back_utm = geom_to_utm(as_wgs)

    # Round-trip precision should be sub-meter
    assert abs(back_utm.area - base_utm.area) < 1.0, (
        f"projection round-trip lost area: {base_utm.area} → {back_utm.area}"
    )

    # 100×100 square shrunk by 7.5m on each side → 85×85 = 7225 m²
    inner = back_utm.buffer(-7.5)
    assert abs(inner.area - 7_225.0) < 2.0, (
        f"expected 85m × 85m square area=7225, got {inner.area}"
    )
