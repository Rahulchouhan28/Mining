"""Plan validation rules (spec Section 6). Each rule produces 0..N
ValidationWarning records keyed by `code` for stable client-side display.
"""
from __future__ import annotations

from typing import Any

from shapely.geometry.base import BaseGeometry


def _warning(severity: str, code: str, message: str, **kw: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, **{k: v for k, v in kw.items() if v is not None}}


def validate_engineering_inputs(ei: dict[str, Any], alternative: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    mw = ei.get("mineral_waste") or {}
    if not mw.get("bulk_density_t_per_m3"):
        out.append(_warning("error", "MISSING_DENSITY", "Bulk density missing — quantity tables will be zero.", alternative=alternative))
    if not mw.get("topsoil_thickness_m"):
        out.append(_warning("warning", "MISSING_TOPSOIL", "Topsoil thickness missing — assuming 0.", alternative=alternative))
    if not mw.get("overburden_thickness_m"):
        out.append(_warning("warning", "MISSING_OB", "Overburden thickness missing — assuming 0.", alternative=alternative))
    if not mw.get("mineral_recovery_percent"):
        out.append(_warning("warning", "MISSING_RECOVERY", "Recovery % missing — assuming 100.", alternative=alternative))

    bench = ei.get("bench") or {}
    if not bench.get("bench_height_m"):
        out.append(_warning("error", "MISSING_BENCH_H", "Bench height missing — required for pit volume.", alternative=alternative))

    prod = ei.get("production") or {}
    target = prod.get("annual_production_target_tonnes") or 0
    approved = prod.get("approved_capacity_tonnes_per_year") or 0
    if approved and target and target > approved * 1.05:
        out.append(_warning(
            "error", "OVER_CAPACITY",
            f"Annual target {target:,.0f} t/y exceeds approved capacity {approved:,.0f} t/y.",
            alternative=alternative,
        ))

    if not (ei.get("grade") or {}):
        out.append(_warning("info", "NO_GRADE", "No chemical-analysis grade fields provided.", alternative=alternative))

    return out


def validate_geometry(
    *,
    lease: BaseGeometry | None,
    barrier: BaseGeometry | None,
    pits: list[BaseGeometry],
    alternative: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if lease is None:
        out.append(_warning("error", "NO_LEASE", "No lease boundary digitized. Draw it in Step 3.", alternative=alternative))
        return out
    if barrier is None:
        out.append(_warning("warning", "NO_BARRIER", "7.5 m statutory barrier missing.", alternative=alternative))

    available = barrier if barrier is not None else lease
    for i, pit in enumerate(pits, start=1):
        if not available.contains(pit):
            out.append(_warning(
                "warning", "PIT_OUTSIDE_BARRIER",
                f"Year {i} pit extends outside the 7.5 m statutory barrier.",
                alternative=alternative,
            ))

    for i in range(len(pits)):
        for j in range(i + 1, len(pits)):
            if pits[i].intersection(pits[j]).area > 1.0:
                out.append(_warning(
                    "warning", "PIT_OVERLAP",
                    f"Year {i+1} and Year {j+1} pits overlap.",
                    alternative=alternative,
                ))
                break

    return out
