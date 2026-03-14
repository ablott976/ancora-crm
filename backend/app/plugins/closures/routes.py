"""Closures plugin API routes."""
from datetime import date
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db
from app.plugins.base import require_plugin
from app.services.chatbot_auth import get_current_chatbot_user
from app.plugins.closures import services as svc

router = APIRouter()


class ClosureCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None
    closure_type: Literal["holiday", "vacation", "maintenance", "other"] = "other"
    affects_all_services: bool = True


class ClosureUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    closure_type: Optional[Literal["holiday", "vacation", "maintenance", "other"]] = None
    affects_all_services: Optional[bool] = None


@router.get("/dashboard/{instance_id}/closures")
async def list_closures(
    instance_id: int = require_plugin("closures"),
    from_date: Optional[date] = None,
    include_past: bool = True,
    limit: int = 100,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_closures(
        db, instance_id, from_date=from_date, include_past=include_past, limit=limit,
    )


@router.post("/dashboard/{instance_id}/closures", status_code=201)
async def create_closure(
    data: ClosureCreate,
    instance_id: int = require_plugin("closures"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        return await svc.create_closure(
            db, instance_id,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
            closure_type=data.closure_type,
            affects_all=data.affects_all_services,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dashboard/{instance_id}/closures/{closure_id}")
async def get_closure(
    closure_id: int,
    instance_id: int = require_plugin("closures"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.get_closure(db, instance_id, closure_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return result


@router.put("/dashboard/{instance_id}/closures/{closure_id}")
async def update_closure(
    closure_id: int,
    data: ClosureUpdate,
    instance_id: int = require_plugin("closures"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    payload = data.dict(exclude_unset=True)
    if "affects_all_services" in payload:
        payload["affects_all"] = payload.pop("affects_all_services")

    try:
        result = await svc.update_closure(db, instance_id, closure_id, **payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return result


@router.delete("/dashboard/{instance_id}/closures/{closure_id}", status_code=204)
async def delete_closure(
    closure_id: int,
    instance_id: int = require_plugin("closures"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_closure(db, instance_id, closure_id):
        raise HTTPException(status_code=404, detail="Cierre no encontrado")


@router.get("/dashboard/{instance_id}/closures/check/{target_date}")
async def check_closure_date(
    target_date: date,
    instance_id: int = require_plugin("closures"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.check_closures(db, instance_id, target_date)


@router.get("/dashboard/{instance_id}/closures/upcoming")
async def get_upcoming_closures(
    instance_id: int = require_plugin("closures"),
    limit: int = 10,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_upcoming_closures(db, instance_id, limit)
