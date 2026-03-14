"""Daily menus plugin API routes."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db
from app.plugins.base import require_plugin
from app.services.chatbot_auth import get_current_chatbot_user
from app.plugins.daily_menus import services as svc

router = APIRouter()


class MenuCreate(BaseModel):
    date: date
    name: str
    price: Optional[float] = None
    is_active: bool = True


class MenuUpdate(BaseModel):
    date: Optional[date] = None
    name: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    course_type: Optional[str] = None
    allergens: Optional[str] = None
    sort_order: int = 0


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    course_type: Optional[str] = None
    allergens: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("/dashboard/{instance_id}/daily-menus/menus")
async def list_menus(
    instance_id: int = require_plugin("daily_menus"),
    target_date: Optional[date] = None,
    active_only: bool = False,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_menus(db, instance_id, target_date=target_date, active_only=active_only)


@router.post("/dashboard/{instance_id}/daily-menus/menus", status_code=201)
async def create_menu(
    data: MenuCreate,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.create_menu(db, instance_id, data.date, data.name, data.price, data.is_active)


@router.get("/dashboard/{instance_id}/daily-menus/menus/{menu_id}")
async def get_menu(
    menu_id: int,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.get_menu(db, instance_id, menu_id)
    if not result:
        raise HTTPException(status_code=404, detail="Menu no encontrado")
    return result


@router.put("/dashboard/{instance_id}/daily-menus/menus/{menu_id}")
async def update_menu(
    menu_id: int,
    data: MenuUpdate,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_menu(db, instance_id, menu_id, **data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Menu no encontrado")
    return result


@router.delete("/dashboard/{instance_id}/daily-menus/menus/{menu_id}", status_code=204)
async def delete_menu(
    menu_id: int,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_menu(db, instance_id, menu_id):
        raise HTTPException(status_code=404, detail="Menu no encontrado")


@router.get("/dashboard/{instance_id}/daily-menus/menus/{menu_id}/items")
async def list_menu_items(
    menu_id: int,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.list_menu_items(db, instance_id, menu_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Menu no encontrado")
    return result


@router.post("/dashboard/{instance_id}/daily-menus/menus/{menu_id}/items", status_code=201)
async def create_menu_item(
    menu_id: int,
    data: MenuItemCreate,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.create_menu_item(
        db, instance_id, menu_id, data.name, data.description,
        data.course_type, data.allergens, data.sort_order,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Menu no encontrado")
    return result


@router.put("/dashboard/{instance_id}/daily-menus/menus/{menu_id}/items/{item_id}")
async def update_menu_item(
    menu_id: int,
    item_id: int,
    data: MenuItemUpdate,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_menu_item(db, instance_id, menu_id, item_id, **data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Plato no encontrado")
    return result


@router.delete("/dashboard/{instance_id}/daily-menus/menus/{menu_id}/items/{item_id}", status_code=204)
async def delete_menu_item(
    menu_id: int,
    item_id: int,
    instance_id: int = require_plugin("daily_menus"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_menu_item(db, instance_id, menu_id, item_id):
        raise HTTPException(status_code=404, detail="Plato no encontrado")
