"""Bookings plugin API routes."""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.database import get_db
from app.plugins.base import require_plugin
from app.services.chatbot_auth import get_current_chatbot_user
from app.plugins.bookings import services as svc

router = APIRouter()


# ── Pydantic models ──

class AppointmentCreate(BaseModel):
    professional_id: int
    service_id: int
    client_name: str
    client_phone: str
    date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    notes: Optional[str] = None

class AppointmentReschedule(BaseModel):
    new_date: date
    new_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")

class ProfessionalCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    service_ids: Optional[list[int]] = None

class ProfessionalUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    service_ids: Optional[list[int]] = None

class ServiceCreate(BaseModel):
    name: str
    duration_minutes: int = 60
    description: Optional[str] = None
    price: Optional[float] = None

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    duration_minutes: Optional[int] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


# ── Availability ──

@router.get("/dashboard/{instance_id}/bookings/availability")
async def get_availability(
    instance_id: int = require_plugin("bookings"),
    professional_id: int = Query(...),
    target_date: date = Query(..., alias="date"),
    service_id: Optional[int] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.get_availability(db, instance_id, professional_id, target_date, service_id)
    return result


# ── Appointments ──

@router.get("/dashboard/{instance_id}/bookings/appointments")
async def list_appointments(
    instance_id: int = require_plugin("bookings"),
    phone: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    professional_id: Optional[int] = None,
    status: Optional[str] = None,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.search_appointments(
        db, instance_id, phone=phone, from_date=from_date, to_date=to_date,
        professional_id=professional_id, status=status,
    )


@router.post("/dashboard/{instance_id}/bookings/appointments", status_code=201)
async def create_appointment(
    data: AppointmentCreate,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        return await svc.create_appointment(
            db, instance_id,
            professional_id=data.professional_id,
            service_id=data.service_id,
            client_name=data.client_name,
            client_phone=data.client_phone,
            appt_date=data.date,
            start_time=data.start_time,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/dashboard/{instance_id}/bookings/appointments/{appt_id}")
async def get_appointment(
    appt_id: int,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    rows = await svc.search_appointments(db, instance_id)
    appt = next((a for a in rows if a["id"] == appt_id), None)
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return appt


@router.post("/dashboard/{instance_id}/bookings/appointments/{appt_id}/cancel")
async def cancel_appointment(
    appt_id: int,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.cancel_appointment(db, instance_id, appt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cita no encontrada o ya cancelada")
    return result


@router.post("/dashboard/{instance_id}/bookings/appointments/{appt_id}/reschedule")
async def reschedule_appointment(
    appt_id: int,
    data: AppointmentReschedule,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        result = await svc.reschedule_appointment(db, instance_id, appt_id, data.new_date, data.new_start_time)
        if not result:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ── Professionals ──

@router.get("/dashboard/{instance_id}/bookings/professionals")
async def list_professionals(
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_professionals(db, instance_id, active_only=False)


@router.post("/dashboard/{instance_id}/bookings/professionals", status_code=201)
async def create_professional(
    data: ProfessionalCreate,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.create_professional(db, instance_id, data.name, data.phone, data.email, data.service_ids)


@router.put("/dashboard/{instance_id}/bookings/professionals/{prof_id}")
async def update_professional(
    prof_id: int,
    data: ProfessionalUpdate,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_professional(
        db, instance_id, prof_id,
        name=data.name, phone=data.phone, email=data.email,
        is_active=data.is_active, service_ids=data.service_ids,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return result


@router.delete("/dashboard/{instance_id}/bookings/professionals/{prof_id}", status_code=204)
async def delete_professional(
    prof_id: int,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_professional(db, instance_id, prof_id):
        raise HTTPException(status_code=404, detail="Profesional no encontrado")


# ── Services ──

@router.get("/dashboard/{instance_id}/bookings/services")
async def list_services(
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_services(db, instance_id, active_only=False)


@router.post("/dashboard/{instance_id}/bookings/services", status_code=201)
async def create_service(
    data: ServiceCreate,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.create_service(db, instance_id, data.name, data.duration_minutes, data.description, data.price)


@router.put("/dashboard/{instance_id}/bookings/services/{service_id}")
async def update_service_endpoint(
    service_id: int,
    data: ServiceUpdate,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_service(db, instance_id, service_id, **data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return result


@router.delete("/dashboard/{instance_id}/bookings/services/{service_id}", status_code=204)
async def delete_service_endpoint(
    service_id: int,
    instance_id: int = require_plugin("bookings"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_service(db, instance_id, service_id):
        raise HTTPException(status_code=404, detail="Servicio no encontrado")


# ── Calendar ──

@router.get("/dashboard/{instance_id}/bookings/calendar")
async def get_calendar(
    instance_id: int = require_plugin("bookings"),
    month: Optional[int] = None,
    year: Optional[int] = None,
    professional_id: Optional[int] = None,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    """Get appointments for a full month for calendar view."""
    from datetime import date as dt_date
    today = dt_date.today()
    m = month or today.month
    y = year or today.year
    first_day = dt_date(y, m, 1)
    if m == 12:
        last_day = dt_date(y + 1, 1, 1)
    else:
        last_day = dt_date(y, m + 1, 1)

    return await svc.search_appointments(
        db, instance_id, from_date=first_day, to_date=last_day,
        professional_id=professional_id, limit=500,
    )
