"""Goals API — natural-language goal entries."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import require_auth
from db.database import create_goal, delete_goal, get_goal, list_goals, update_goal
from integrations.goal_extractor import extract_goal
from integrations.llm_client import is_llm_configured

router = APIRouter(prefix="/api/goals", tags=["goals"])


class GoalCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


class GoalUpdateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


def _goal_card(goal) -> dict:
    return {
        "id": goal.id,
        "title": goal.title,
        "summary": goal.summary,
        "extraction_status": goal.extraction_status,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
    }


def _goal_detail(goal) -> dict:
    detail = _goal_card(goal)
    detail["raw_text"] = goal.raw_text
    if goal.extracted_json:
        try:
            detail["extracted"] = json.loads(goal.extracted_json)
        except json.JSONDecodeError:
            detail["extracted"] = None
    return detail


@router.get("/status")
def goals_status(request: Request):
    require_auth(request)
    goals = list_goals()
    return {
        "count": len(goals),
        "llm_configured": is_llm_configured(),
    }


@router.get("")
def goals_list(request: Request):
    require_auth(request)
    return {"goals": [_goal_card(g) for g in list_goals()]}


@router.get("/{goal_id}")
def goal_detail(request: Request, goal_id: int):
    require_auth(request)
    goal = get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _goal_detail(goal)


@router.post("")
def goal_create(request: Request, body: GoalCreateRequest):
    require_auth(request)
    text = body.text.strip()
    try:
        extracted = extract_goal(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    goal = create_goal(
        raw_text=text,
        title=extracted.get("title") or "Goal",
        summary=extracted.get("summary"),
        extracted_json=extracted.get("extracted_json"),
        extraction_status=extracted.get("extraction_status") or "failed",
    )
    return _goal_detail(goal)


@router.put("/{goal_id}")
def goal_update(request: Request, goal_id: int, body: GoalUpdateRequest):
    require_auth(request)
    text = body.text.strip()
    try:
        extracted = extract_goal(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    goal = update_goal(
        goal_id,
        raw_text=text,
        title=extracted.get("title") or "Goal",
        summary=extracted.get("summary"),
        extracted_json=extracted.get("extracted_json"),
        extraction_status=extracted.get("extraction_status") or "failed",
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _goal_detail(goal)


@router.delete("/{goal_id}")
def goal_remove(request: Request, goal_id: int):
    require_auth(request)
    if not delete_goal(goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"ok": True}
