from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

import storage
from services.year_planner import generate_for_project

router = APIRouter()


@router.post("/{slug}/generate")
def generate_plan(slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        project = storage.load_project(slug)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e

    alternatives = payload.get("alternatives") or project.get("selected_alternatives") or ["base"]
    result = generate_for_project(project, alternatives)

    project["selected_alternatives"] = alternatives
    project["generated_plans"] = result["generated_plans"]
    project["quantity_tables"] = result["quantity_tables"]
    project["validation_warnings"] = result["validation_warnings"]
    storage.save_project(slug, project)

    return {
        "slug": slug,
        "alternatives": alternatives,
        "plan_count": len(result["generated_plans"]),
        "warning_count": len(result["validation_warnings"]),
    }
