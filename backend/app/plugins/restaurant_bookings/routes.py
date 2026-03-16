"""Restaurant bookings dashboard routes."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db
from app.plugins.base import require_plugin
from app.plugins.restaurant_bookings import services as svc
from app.services.chatbot_auth import get_current_chatbot_user

router = APIRouter()


class ReservationCreate(BaseModel):
    client_name: str
    client_phone: str
    date: date
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    party_size: int = Field(..., ge=1)
    zone_id: Optional[int] = None
    table_id: Optional[int] = None
    notes: Optional[str] = None
    allergies: Optional[str] = None


class ReservationUpdate(BaseModel):
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    date: Optional[date] = None
    time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    party_size: Optional[int] = Field(None, ge=1)
    zone_id: Optional[int] = None
    table_id: Optional[int] = None
    notes: Optional[str] = None
    allergies: Optional[str] = None
    status: Optional[str] = None


class ZoneCreate(BaseModel):
    name: str
    capacity: int = Field(default=20, ge=1)


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class TableCreate(BaseModel):
    table_number: str
    seats: int = Field(default=4, ge=1)


class TableUpdate(BaseModel):
    table_number: Optional[str] = None
    seats: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


@router.get("/dashboard/{instance_id}/restaurant/reservations")
async def list_reservations(
    instance_id: int = require_plugin("restaurant_bookings"),
    date_filter: Optional[date] = None,
    limit: int = 50,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_reservations(db, instance_id, target_date=date_filter, limit=limit)


@router.post("/dashboard/{instance_id}/restaurant/reservations", status_code=201)
async def create_reservation(
    data: ReservationCreate,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        return await svc.create_reservation(
            db,
            instance_id,
            client_name=data.client_name,
            client_phone=data.client_phone,
            target_date=data.date,
            time=data.time,
            party_size=data.party_size,
            notes=data.notes,
            allergies=data.allergies,
            zone_id=data.zone_id,
            table_id=data.table_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put("/dashboard/{instance_id}/restaurant/reservations/{reservation_id}")
async def update_reservation(
    reservation_id: int,
    data: ReservationUpdate,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        result = await svc.update_reservation(db, instance_id, reservation_id, **data.dict(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.post("/dashboard/{instance_id}/restaurant/reservations/{reservation_id}/confirm")
async def confirm_reservation(
    reservation_id: int,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        result = await svc.confirm_reservation(db, instance_id, reservation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.post("/dashboard/{instance_id}/restaurant/reservations/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: int,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        result = await svc.cancel_reservation_dashboard(db, instance_id, reservation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.post("/dashboard/{instance_id}/restaurant/reservations/{reservation_id}/noshow")
async def mark_noshow(
    reservation_id: int,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        result = await svc.mark_noshow(db, instance_id, reservation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.get("/dashboard/{instance_id}/restaurant/zones")
async def list_zones(
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_zones(db, instance_id)


@router.post("/dashboard/{instance_id}/restaurant/zones", status_code=201)
async def create_zone(
    data: ZoneCreate,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.create_zone(db, instance_id, data.name, data.capacity)


@router.put("/dashboard/{instance_id}/restaurant/zones/{zone_id}")
async def update_zone(
    zone_id: int,
    data: ZoneUpdate,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_zone(db, instance_id, zone_id, **data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    return result


@router.delete("/dashboard/{instance_id}/restaurant/zones/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: int,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_zone(db, instance_id, zone_id):
        raise HTTPException(status_code=404, detail="Zona no encontrada")


@router.get("/dashboard/{instance_id}/restaurant/zones/{zone_id}/tables")
async def list_tables(
    zone_id: int,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_tables(db, instance_id, zone_id)


@router.post("/dashboard/{instance_id}/restaurant/zones/{zone_id}/tables", status_code=201)
async def create_table(
    zone_id: int,
    data: TableCreate,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        return await svc.create_table(db, instance_id, zone_id, data.table_number, data.seats)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put("/dashboard/{instance_id}/restaurant/tables/{table_id}")
async def update_table(
    table_id: int,
    data: TableUpdate,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_table(db, instance_id, table_id, **data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return result


@router.delete("/dashboard/{instance_id}/restaurant/tables/{table_id}", status_code=204)
async def delete_table(
    table_id: int,
    instance_id: int = require_plugin("restaurant_bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_table(db, instance_id, table_id):
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
