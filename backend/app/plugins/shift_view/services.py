"""Shift view business logic."""
from typing import List, Optional
from datetime import date


async def get_shifts(db, instance_id: int, professional_id: int = None) -> List[dict]:
    if professional_id:
        return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_shifts WHERE instance_id = $1 AND professional_id = $2 AND is_active = true ORDER BY day_of_week, start_time", instance_id, professional_id)]
    return [dict(r) for r in await db.fetch("SELECT s.*, p.name as professional_name FROM ancora_crm.plugin_shifts s JOIN ancora_crm.plugin_bookings_professionals p ON s.professional_id = p.id WHERE s.instance_id = $1 AND s.is_active = true ORDER BY s.professional_id, s.day_of_week, s.start_time", instance_id)]


async def set_shift(db, instance_id: int, professional_id: int, day_of_week: int, start_time: str, end_time: str) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_shifts (instance_id, professional_id, day_of_week, start_time, end_time)
           VALUES ($1, $2, $3, $4, $5)
           ON CONFLICT (instance_id, professional_id, day_of_week, start_time) DO UPDATE SET end_time = $5, is_active = true
           RETURNING *""",
        instance_id, professional_id, day_of_week, start_time, end_time)
    return dict(row)


async def get_day_agenda(db, instance_id: int, professional_id: int, target_date: date) -> dict:
    dow = target_date.weekday()
    shifts = await db.fetch("SELECT * FROM ancora_crm.plugin_shifts WHERE instance_id = $1 AND professional_id = $2 AND day_of_week = $3 AND is_active = true ORDER BY start_time", instance_id, professional_id, dow)
    override = await db.fetchrow("SELECT * FROM ancora_crm.plugin_shift_overrides WHERE instance_id = $1 AND professional_id = $2 AND date = $3", instance_id, professional_id, target_date)
    if override and override["is_off"]:
        return {"date": target_date.isoformat(), "professional_id": professional_id, "is_off": True, "reason": override.get("reason"), "appointments": []}
    appointments = await db.fetch(
        "SELECT * FROM ancora_crm.plugin_bookings_appointments WHERE instance_id = $1 AND professional_id = $2 AND date = $3 AND status != 'cancelada' ORDER BY start_time",
        instance_id, professional_id, target_date)
    return {
        "date": target_date.isoformat(), "professional_id": professional_id, "is_off": False,
        "shifts": [dict(s) for s in shifts],
        "override": dict(override) if override else None,
        "appointments": [dict(a) for a in appointments],
    }


async def set_override(db, instance_id: int, professional_id: int, target_date: date, is_off: bool = False, start_time: str = None, end_time: str = None, reason: str = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_shift_overrides (instance_id, professional_id, date, start_time, end_time, is_off, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           ON CONFLICT (instance_id, professional_id, date) DO UPDATE SET start_time = $4, end_time = $5, is_off = $6, reason = $7
           RETURNING *""",
        instance_id, professional_id, target_date, start_time, end_time, is_off, reason)
    return dict(row)
