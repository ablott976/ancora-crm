"""Bookings business logic - availability engine, CRUD."""
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import pytz

TZ = pytz.timezone("Europe/Madrid")


# ──────────────────────────────── Availability ────────────────────────────────

async def get_schedule_for_day(db, instance_id: int, target_date: date) -> Optional[dict]:
    """Get the business schedule for a specific weekday."""
    weekday = target_date.weekday()  # 0=Monday
    row = await db.fetchrow(
        "SELECT hora_apertura, hora_cierre, abierto FROM ancora_crm.chatbot_schedule "
        "WHERE instance_id = $1 AND dia_semana = $2",
        instance_id, weekday,
    )
    return dict(row) if row else None


async def is_holiday(db, instance_id: int, target_date: date) -> bool:
    """Check if target_date is a holiday."""
    row = await db.fetchrow(
        "SELECT 1 FROM ancora_crm.chatbot_holidays WHERE instance_id = $1 AND fecha = $2",
        instance_id, target_date,
    )
    return row is not None


async def get_availability_override(db, instance_id: int, professional_id: int, target_date: date) -> Optional[dict]:
    """Check if there's an override for this professional on this date."""
    row = await db.fetchrow(
        "SELECT available, start_time, end_time, reason FROM ancora_crm.plugin_bookings_availability_overrides "
        "WHERE instance_id = $1 AND professional_id = $2 AND date = $3",
        instance_id, professional_id, target_date,
    )
    return dict(row) if row else None


async def get_booked_slots(db, instance_id: int, professional_id: int, target_date: date) -> List[dict]:
    """Get all booked appointments for a professional on a date."""
    rows = await db.fetch(
        "SELECT start_time, end_time FROM ancora_crm.plugin_bookings_appointments "
        "WHERE instance_id = $1 AND professional_id = $2 AND date = $3 "
        "AND status NOT IN ('cancelada')",
        instance_id, professional_id, target_date,
    )
    return [dict(r) for r in rows]


def generate_slots(open_time: str, close_time: str, duration_minutes: int, booked: List[dict]) -> List[str]:
    """Generate available time slots given opening hours, duration, and already-booked slots."""
    slots = []
    open_h, open_m = map(int, open_time.split(":"))
    close_h, close_m = map(int, close_time.split(":"))

    current = open_h * 60 + open_m
    end = close_h * 60 + close_m

    booked_ranges = []
    for b in booked:
        bh1, bm1 = map(int, b["start_time"].split(":"))
        bh2, bm2 = map(int, b["end_time"].split(":"))
        booked_ranges.append((bh1 * 60 + bm1, bh2 * 60 + bm2))

    while current + duration_minutes <= end:
        slot_end = current + duration_minutes
        conflict = any(
            not (slot_end <= bs or current >= be)
            for bs, be in booked_ranges
        )
        if not conflict:
            h, m = divmod(current, 60)
            slots.append(f"{h:02d}:{m:02d}")
        current += 30  # slots every 30 min
    return slots


async def get_availability(
    db, instance_id: int, professional_id: int, target_date: date, service_id: Optional[int] = None
) -> Dict[str, Any]:
    """Full availability check for a professional on a date."""
    # Check holiday
    if await is_holiday(db, instance_id, target_date):
        return {"available": False, "reason": "Es dia festivo", "slots": []}

    # Check schedule
    schedule = await get_schedule_for_day(db, instance_id, target_date)
    if not schedule or not schedule["abierto"]:
        return {"available": False, "reason": "Cerrado ese dia", "slots": []}

    # Check override
    override = await get_availability_override(db, instance_id, professional_id, target_date)
    if override and not override["available"]:
        return {"available": False, "reason": override.get("reason", "No disponible"), "slots": []}

    open_time = override.get("start_time") if override and override.get("start_time") else schedule["hora_apertura"]
    close_time = override.get("end_time") if override and override.get("end_time") else schedule["hora_cierre"]

    # Get service duration
    duration = 60
    if service_id:
        svc = await db.fetchrow(
            "SELECT duration_minutes FROM ancora_crm.plugin_bookings_services WHERE id = $1", service_id
        )
        if svc:
            duration = svc["duration_minutes"]

    booked = await get_booked_slots(db, instance_id, professional_id, target_date)
    slots = generate_slots(open_time, close_time, duration, booked)

    return {"available": len(slots) > 0, "slots": slots, "open": open_time, "close": close_time}


# ────────────────────────────── Appointments CRUD ─────────────────────────────

async def create_appointment(
    db,
    instance_id: int,
    professional_id: int,
    service_id: int,
    client_name: str,
    client_phone: str,
    appt_date: date,
    start_time: str,
    contact_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create a new appointment with conflict validation."""
    # Get service duration
    svc = await db.fetchrow(
        "SELECT duration_minutes FROM ancora_crm.plugin_bookings_services WHERE id = $1", service_id
    )
    duration = svc["duration_minutes"] if svc else 60

    # Calculate end_time
    sh, sm = map(int, start_time.split(":"))
    total_min = sh * 60 + sm + duration
    eh, em = divmod(total_min, 60)
    end_time = f"{eh:02d}:{em:02d}"

    # Check for conflicts
    booked = await get_booked_slots(db, instance_id, professional_id, appt_date)
    slot_start = sh * 60 + sm
    slot_end = total_min
    for b in booked:
        bh1, bm1 = map(int, b["start_time"].split(":"))
        bh2, bm2 = map(int, b["end_time"].split(":"))
        bs = bh1 * 60 + bm1
        be = bh2 * 60 + bm2
        if not (slot_end <= bs or slot_start >= be):
            raise ValueError(f"Conflicto: ya hay una cita de {b['start_time']} a {b['end_time']}")

    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_bookings_appointments
           (instance_id, contact_id, professional_id, service_id, client_name, client_phone,
            date, start_time, end_time, status, notes)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'confirmada', $10)
           RETURNING *""",
        instance_id, contact_id, professional_id, service_id, client_name, client_phone,
        appt_date, start_time, end_time, notes,
    )
    return dict(row)


async def search_appointments(
    db, instance_id: int, phone: Optional[str] = None,
    from_date: Optional[date] = None, to_date: Optional[date] = None,
    professional_id: Optional[int] = None, status: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """Search appointments with filters."""
    conditions = ["a.instance_id = $1"]
    params: list = [instance_id]
    idx = 2

    if phone:
        conditions.append(f"a.client_phone ILIKE ${idx}")
        params.append(f"%{phone}%")
        idx += 1
    if from_date:
        conditions.append(f"a.date >= ${idx}")
        params.append(from_date)
        idx += 1
    if to_date:
        conditions.append(f"a.date <= ${idx}")
        params.append(to_date)
        idx += 1
    if professional_id:
        conditions.append(f"a.professional_id = ${idx}")
        params.append(professional_id)
        idx += 1
    if status:
        conditions.append(f"a.status = ${idx}")
        params.append(status)
        idx += 1

    where = " AND ".join(conditions)
    query = f"""
        SELECT a.*, p.name as professional_name, s.name as service_name
        FROM ancora_crm.plugin_bookings_appointments a
        LEFT JOIN ancora_crm.plugin_bookings_professionals p ON a.professional_id = p.id
        LEFT JOIN ancora_crm.plugin_bookings_services s ON a.service_id = s.id
        WHERE {where}
        ORDER BY a.date DESC, a.start_time DESC
        LIMIT {limit}
    """
    rows = await db.fetch(query, *params)
    return [dict(r) for r in rows]


async def cancel_appointment(db, instance_id: int, appointment_id: int) -> Optional[dict]:
    """Cancel an appointment."""
    row = await db.fetchrow(
        """UPDATE ancora_crm.plugin_bookings_appointments
           SET status = 'cancelada', updated_at = NOW()
           WHERE id = $1 AND instance_id = $2 AND status != 'cancelada'
           RETURNING *""",
        appointment_id, instance_id,
    )
    return dict(row) if row else None


async def reschedule_appointment(
    db, instance_id: int, appointment_id: int,
    new_date: date, new_start_time: str,
) -> Optional[dict]:
    """Reschedule an appointment to a new date/time."""
    # Get current appointment
    current = await db.fetchrow(
        "SELECT * FROM ancora_crm.plugin_bookings_appointments WHERE id = $1 AND instance_id = $2",
        appointment_id, instance_id,
    )
    if not current:
        return None

    # Get service duration
    svc = await db.fetchrow(
        "SELECT duration_minutes FROM ancora_crm.plugin_bookings_services WHERE id = $1",
        current["service_id"],
    )
    duration = svc["duration_minutes"] if svc else 60

    sh, sm = map(int, new_start_time.split(":"))
    total_min = sh * 60 + sm + duration
    eh, em = divmod(total_min, 60)
    new_end_time = f"{eh:02d}:{em:02d}"

    # Check conflicts (excluding this appointment)
    booked = await db.fetch(
        "SELECT start_time, end_time FROM ancora_crm.plugin_bookings_appointments "
        "WHERE instance_id = $1 AND professional_id = $2 AND date = $3 AND id != $4 "
        "AND status NOT IN ('cancelada')",
        instance_id, current["professional_id"], new_date, appointment_id,
    )
    slot_start = sh * 60 + sm
    slot_end = total_min
    for b in booked:
        bh1, bm1 = map(int, b["start_time"].split(":"))
        bh2, bm2 = map(int, b["end_time"].split(":"))
        bs, be = bh1 * 60 + bm1, bh2 * 60 + bm2
        if not (slot_end <= bs or slot_start >= be):
            raise ValueError(f"Conflicto con cita existente de {b['start_time']} a {b['end_time']}")

    row = await db.fetchrow(
        """UPDATE ancora_crm.plugin_bookings_appointments
           SET date = $1, start_time = $2, end_time = $3, updated_at = NOW()
           WHERE id = $4 AND instance_id = $5 RETURNING *""",
        new_date, new_start_time, new_end_time, appointment_id, instance_id,
    )
    return dict(row) if row else None


# ──────────────────────────── Professionals CRUD ──────────────────────────────

async def list_professionals(db, instance_id: int, active_only: bool = True) -> List[dict]:
    condition = " AND is_active = true" if active_only else ""
    rows = await db.fetch(
        f"SELECT * FROM ancora_crm.plugin_bookings_professionals WHERE instance_id = $1{condition} ORDER BY name",
        instance_id,
    )
    result = []
    for r in rows:
        prof = dict(r)
        # Get assigned services
        svcs = await db.fetch(
            """SELECT s.id, s.name FROM ancora_crm.plugin_bookings_professional_services ps
               JOIN ancora_crm.plugin_bookings_services s ON ps.service_id = s.id
               WHERE ps.professional_id = $1""",
            prof["id"],
        )
        prof["services"] = [dict(s) for s in svcs]
        result.append(prof)
    return result


async def create_professional(db, instance_id: int, name: str, phone: str = None, email: str = None, service_ids: list = None) -> dict:
    row = await db.fetchrow(
        "INSERT INTO ancora_crm.plugin_bookings_professionals (instance_id, name, phone, email) "
        "VALUES ($1, $2, $3, $4) RETURNING *",
        instance_id, name, phone, email,
    )
    prof = dict(row)
    if service_ids:
        for sid in service_ids:
            await db.execute(
                "INSERT INTO ancora_crm.plugin_bookings_professional_services (professional_id, service_id) "
                "VALUES ($1, $2) ON CONFLICT DO NOTHING",
                prof["id"], sid,
            )
    return prof


async def update_professional(db, instance_id: int, prof_id: int, name: str = None, phone: str = None, email: str = None, is_active: bool = None, service_ids: list = None) -> Optional[dict]:
    updates = []
    params = []
    idx = 3
    if name is not None:
        updates.append(f"name = ${idx}")
        params.append(name)
        idx += 1
    if phone is not None:
        updates.append(f"phone = ${idx}")
        params.append(phone)
        idx += 1
    if email is not None:
        updates.append(f"email = ${idx}")
        params.append(email)
        idx += 1
    if is_active is not None:
        updates.append(f"is_active = ${idx}")
        params.append(is_active)
        idx += 1

    if not updates:
        row = await db.fetchrow(
            "SELECT * FROM ancora_crm.plugin_bookings_professionals WHERE id = $1 AND instance_id = $2",
            prof_id, instance_id,
        )
    else:
        set_clause = ", ".join(updates)
        row = await db.fetchrow(
            f"UPDATE ancora_crm.plugin_bookings_professionals SET {set_clause} "
            f"WHERE id = $1 AND instance_id = $2 RETURNING *",
            prof_id, instance_id, *params,
        )

    if not row:
        return None

    if service_ids is not None:
        await db.execute("DELETE FROM ancora_crm.plugin_bookings_professional_services WHERE professional_id = $1", prof_id)
        for sid in service_ids:
            await db.execute(
                "INSERT INTO ancora_crm.plugin_bookings_professional_services (professional_id, service_id) "
                "VALUES ($1, $2) ON CONFLICT DO NOTHING",
                prof_id, sid,
            )

    return dict(row)


async def delete_professional(db, instance_id: int, prof_id: int) -> bool:
    result = await db.execute(
        "DELETE FROM ancora_crm.plugin_bookings_professionals WHERE id = $1 AND instance_id = $2",
        prof_id, instance_id,
    )
    return int(result.split(" ")[1]) > 0


# ──────────────────────────────── Services CRUD ───────────────────────────────

async def list_services(db, instance_id: int, active_only: bool = True) -> List[dict]:
    condition = " AND is_active = true" if active_only else ""
    rows = await db.fetch(
        f"SELECT * FROM ancora_crm.plugin_bookings_services WHERE instance_id = $1{condition} ORDER BY name",
        instance_id,
    )
    return [dict(r) for r in rows]


async def create_service(db, instance_id: int, name: str, duration_minutes: int = 60, description: str = None, price: float = None) -> dict:
    row = await db.fetchrow(
        "INSERT INTO ancora_crm.plugin_bookings_services (instance_id, name, duration_minutes, description, price) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING *",
        instance_id, name, duration_minutes, description, price,
    )
    return dict(row)


async def update_service(db, instance_id: int, service_id: int, **kwargs) -> Optional[dict]:
    allowed = {"name", "duration_minutes", "description", "price", "is_active"}
    updates = []
    params = []
    idx = 3
    for key, val in kwargs.items():
        if key in allowed and val is not None:
            updates.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1

    if not updates:
        return None

    set_clause = ", ".join(updates)
    row = await db.fetchrow(
        f"UPDATE ancora_crm.plugin_bookings_services SET {set_clause} "
        f"WHERE id = $1 AND instance_id = $2 RETURNING *",
        service_id, instance_id, *params,
    )
    return dict(row) if row else None


async def delete_service(db, instance_id: int, service_id: int) -> bool:
    result = await db.execute(
        "DELETE FROM ancora_crm.plugin_bookings_services WHERE id = $1 AND instance_id = $2",
        service_id, instance_id,
    )
    return int(result.split(" ")[1]) > 0


# ──────────────────────────── Professionals by service ────────────────────────

async def get_professionals_for_service(db, instance_id: int, service_id: int) -> List[dict]:
    rows = await db.fetch(
        """SELECT p.id, p.name, p.phone
           FROM ancora_crm.plugin_bookings_professionals p
           JOIN ancora_crm.plugin_bookings_professional_services ps ON p.id = ps.professional_id
           WHERE ps.service_id = $1 AND p.instance_id = $2 AND p.is_active = true
           ORDER BY p.name""",
        service_id, instance_id,
    )
    return [dict(r) for r in rows]
