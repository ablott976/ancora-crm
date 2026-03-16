"""Restaurant bookings business logic."""
from __future__ import annotations

from datetime import date
from typing import Any, List, Optional


ACTIVE_RESERVATION_STATUSES = ("pendiente", "confirmada")
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pendiente": {"confirmada", "cancelada"},
    "confirmada": {"completada", "cancelada", "noshow"},
    "completada": set(),
    "cancelada": set(),
    "noshow": set(),
}


def _row_to_dict(row: Any) -> Optional[dict]:
    return dict(row) if row else None


def _normalize_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    aliases = {
        "confirmed": "confirmada",
        "cancelled": "cancelada",
        "canceled": "cancelada",
        "no-show": "noshow",
        "pending": "pendiente",
        "completed": "completada",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in VALID_TRANSITIONS:
        raise ValueError(f"Estado no soportado: {status}")
    return normalized


def _validate_transition(current: str, new: str) -> None:
    current_status = _normalize_status(current)
    new_status = _normalize_status(new)
    if new_status not in VALID_TRANSITIONS[current_status]:
        raise ValueError(f"No se puede cambiar de {current_status} a {new_status}")


async def _get_zone(db, instance_id: int, zone_id: int, *, active_only: bool = False) -> Optional[dict]:
    query = (
        "SELECT * FROM ancora_crm.plugin_restaurant_zones "
        "WHERE id = $1 AND instance_id = $2"
    )
    if active_only:
        query += " AND is_active = true"
    return _row_to_dict(await db.fetchrow(query, zone_id, instance_id))


async def _get_table(db, instance_id: int, table_id: int, *, active_only: bool = False) -> Optional[dict]:
    query = (
        "SELECT t.*, z.instance_id, z.is_active AS zone_active "
        "FROM ancora_crm.plugin_restaurant_tables t "
        "INNER JOIN ancora_crm.plugin_restaurant_zones z ON z.id = t.zone_id "
        "WHERE t.id = $1 AND z.instance_id = $2"
    )
    if active_only:
        query += " AND t.is_active = true AND z.is_active = true"
    return _row_to_dict(await db.fetchrow(query, table_id, instance_id))


async def _load_reservation(db, instance_id: int, reservation_id: int) -> Optional[dict]:
    return _row_to_dict(
        await db.fetchrow(
            "SELECT * FROM ancora_crm.plugin_restaurant_reservations WHERE id = $1 AND instance_id = $2",
            reservation_id,
            instance_id,
        )
    )


async def _validate_capacity(
    db,
    instance_id: int,
    target_date: date,
    time: str,
    party_size: int,
    zone_id: Optional[int] = None,
    reservation_id: Optional[int] = None,
) -> None:
    if party_size < 1:
        raise ValueError("El número de comensales debe ser al menos 1")

    params: list[Any] = [instance_id, target_date, time]
    reservation_filter = ""
    if reservation_id is not None:
        reservation_filter = " AND id != $4"
        params.append(reservation_id)

    if zone_id is not None:
        zone = await _get_zone(db, instance_id, zone_id, active_only=True)
        if not zone:
            raise ValueError("Zona no encontrada o inactiva")
        if party_size > zone["capacity"]:
            raise ValueError("La reserva supera la capacidad de la zona")

        booked = await db.fetchval(
            "SELECT COALESCE(SUM(party_size), 0) "
            "FROM ancora_crm.plugin_restaurant_reservations "
            "WHERE instance_id = $1 AND date = $2 AND time = $3 "
            "AND zone_id = $4 AND status = ANY($5::text[])"
            + (f" AND id != ${len(params) + 2}" if reservation_id is not None else ""),
            *([instance_id, target_date, time, zone_id, list(ACTIVE_RESERVATION_STATUSES)] + ([reservation_id] if reservation_id is not None else [])),
        )
        if (booked or 0) + party_size > zone["capacity"]:
            raise ValueError("No hay capacidad suficiente en la zona para esa franja")
        return

    total_capacity = await db.fetchval(
        "SELECT COALESCE(SUM(capacity), 0) "
        "FROM ancora_crm.plugin_restaurant_zones "
        "WHERE instance_id = $1 AND is_active = true",
        instance_id,
    )
    if not total_capacity:
        raise ValueError("No hay zonas activas configuradas")

    booked = await db.fetchval(
        "SELECT COALESCE(SUM(party_size), 0) "
        "FROM ancora_crm.plugin_restaurant_reservations "
        "WHERE instance_id = $1 AND date = $2 AND time = $3 "
        "AND status = ANY($4::text[])"
        + (f" AND id != $5" if reservation_id is not None else ""),
        *([instance_id, target_date, time, list(ACTIVE_RESERVATION_STATUSES)] + ([reservation_id] if reservation_id is not None else [])),
    )
    if (booked or 0) + party_size > total_capacity:
        raise ValueError("No hay capacidad suficiente para esa franja")


async def _validate_table_assignment(
    db,
    instance_id: int,
    table_id: Optional[int],
    zone_id: Optional[int],
    party_size: int,
    target_date: date,
    time: str,
    reservation_id: Optional[int] = None,
) -> Optional[dict]:
    if table_id is None:
        return None

    table = await _get_table(db, instance_id, table_id, active_only=True)
    if not table:
        raise ValueError("Mesa no encontrada o inactiva")
    if zone_id is not None and table["zone_id"] != zone_id:
        raise ValueError("La mesa no pertenece a la zona seleccionada")
    if party_size > table["seats"]:
        raise ValueError("La reserva supera la capacidad de la mesa")

    query = (
        "SELECT 1 FROM ancora_crm.plugin_restaurant_reservations "
        "WHERE instance_id = $1 AND table_id = $2 AND date = $3 AND time = $4 "
        "AND status = ANY($5::text[])"
    )
    params: list[Any] = [instance_id, table_id, target_date, time, list(ACTIVE_RESERVATION_STATUSES)]
    if reservation_id is not None:
        query += " AND id != $6"
        params.append(reservation_id)
    query += " LIMIT 1"

    if await db.fetchrow(query, *params):
        raise ValueError("La mesa ya está reservada en esa franja")
    return table


async def check_availability(db, instance_id: int, target_date: date, time: str, party_size: int) -> dict:
    booked = await db.fetchval(
        "SELECT COALESCE(SUM(party_size), 0) "
        "FROM ancora_crm.plugin_restaurant_reservations "
        "WHERE instance_id = $1 AND date = $2 AND time = $3 AND status = ANY($4::text[])",
        instance_id,
        target_date,
        time,
        list(ACTIVE_RESERVATION_STATUSES),
    )
    total_capacity = await db.fetchval(
        "SELECT COALESCE(SUM(capacity), 0) "
        "FROM ancora_crm.plugin_restaurant_zones "
        "WHERE instance_id = $1 AND is_active = true",
        instance_id,
    )
    available = max((total_capacity or 0) - (booked or 0), 0)
    return {
        "date": target_date.isoformat(),
        "time": time,
        "party_size": party_size,
        "available_seats": available,
        "can_book": available >= party_size,
    }


async def create_reservation(
    db,
    instance_id: int,
    client_name: str,
    client_phone: str,
    target_date: date,
    time: str,
    party_size: int,
    notes: str = None,
    allergies: str = None,
    zone_id: Optional[int] = None,
    table_id: Optional[int] = None,
) -> dict:
    await _validate_capacity(db, instance_id, target_date, time, party_size, zone_id)
    table = await _validate_table_assignment(db, instance_id, table_id, zone_id, party_size, target_date, time)
    if zone_id is None and table is not None:
        zone_id = table["zone_id"]

    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_restaurant_reservations
           (instance_id, client_name, client_phone, date, time, party_size, zone_id, table_id, status, notes, allergies, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pendiente', $9, $10, NOW())
           RETURNING *""",
        instance_id,
        client_name,
        client_phone,
        target_date,
        time,
        party_size,
        zone_id,
        table_id,
        notes,
        allergies,
    )
    return dict(row)


async def update_reservation(db, instance_id: int, reservation_id: int, **kwargs) -> Optional[dict]:
    reservation = await _load_reservation(db, instance_id, reservation_id)
    if not reservation:
        return None

    updates = dict(kwargs)
    if "status" in updates and updates["status"] is not None:
        next_status = _normalize_status(updates["status"])
        _validate_transition(reservation["status"], next_status)
        updates["status"] = next_status

    target_date = updates.get("date", reservation["date"])
    time = updates.get("time", reservation["time"])
    party_size = updates.get("party_size", reservation["party_size"])
    zone_id = updates.get("zone_id", reservation.get("zone_id"))
    table_id = updates.get("table_id", reservation.get("table_id"))

    await _validate_capacity(db, instance_id, target_date, time, party_size, zone_id, reservation_id)
    table = await _validate_table_assignment(db, instance_id, table_id, zone_id, party_size, target_date, time, reservation_id)
    if zone_id is None and table is not None:
        updates["zone_id"] = table["zone_id"]

    allowed_fields = {
        "client_name",
        "client_phone",
        "date",
        "time",
        "party_size",
        "zone_id",
        "table_id",
        "notes",
        "allergies",
        "status",
    }
    assignments = []
    params: list[Any] = []
    index = 1
    for field, value in updates.items():
        if field not in allowed_fields:
            continue
        assignments.append(f"{field} = ${index}")
        params.append(value)
        index += 1

    if not assignments:
        return reservation

    assignments.append("updated_at = NOW()")
    params.extend([reservation_id, instance_id])
    row = await db.fetchrow(
        f"""UPDATE ancora_crm.plugin_restaurant_reservations
            SET {", ".join(assignments)}
            WHERE id = ${index} AND instance_id = ${index + 1}
            RETURNING *""",
        *params,
    )
    return dict(row) if row else None


async def confirm_reservation(db, instance_id: int, reservation_id: int) -> Optional[dict]:
    reservation = await _load_reservation(db, instance_id, reservation_id)
    if not reservation:
        return None
    _validate_transition(reservation["status"], "confirmada")
    return await update_reservation(db, instance_id, reservation_id, status="confirmada")


async def cancel_reservation_dashboard(db, instance_id: int, reservation_id: int) -> Optional[dict]:
    reservation = await _load_reservation(db, instance_id, reservation_id)
    if not reservation:
        return None
    _validate_transition(reservation["status"], "cancelada")
    return await update_reservation(db, instance_id, reservation_id, status="cancelada")


async def mark_noshow(db, instance_id: int, reservation_id: int) -> Optional[dict]:
    reservation = await _load_reservation(db, instance_id, reservation_id)
    if not reservation:
        return None
    _validate_transition(reservation["status"], "noshow")
    return await update_reservation(db, instance_id, reservation_id, status="noshow")


async def find_by_phone(db, instance_id: int, phone: str, upcoming_only: bool = True) -> List[dict]:
    cond = "instance_id = $1 AND client_phone = $2"
    if upcoming_only:
        cond += " AND date >= CURRENT_DATE AND status != 'cancelada'"
    rows = await db.fetch(
        f"SELECT * FROM ancora_crm.plugin_restaurant_reservations WHERE {cond} ORDER BY date, time",
        instance_id,
        phone,
    )
    return [dict(r) for r in rows]


async def cancel_reservation(db, instance_id: int, reservation_id: int) -> bool:
    result = await cancel_reservation_dashboard(db, instance_id, reservation_id)
    return result is not None


async def list_reservations(db, instance_id: int, target_date: date = None, limit: int = 50) -> List[dict]:
    if target_date:
        rows = await db.fetch(
            """SELECT r.*, z.name AS zone_name, t.table_number
               FROM ancora_crm.plugin_restaurant_reservations r
               LEFT JOIN ancora_crm.plugin_restaurant_zones z ON z.id = r.zone_id
               LEFT JOIN ancora_crm.plugin_restaurant_tables t ON t.id = r.table_id
               WHERE r.instance_id = $1 AND r.date = $2
               ORDER BY r.time, r.created_at DESC""",
            instance_id,
            target_date,
        )
    else:
        rows = await db.fetch(
            """SELECT r.*, z.name AS zone_name, t.table_number
               FROM ancora_crm.plugin_restaurant_reservations r
               LEFT JOIN ancora_crm.plugin_restaurant_zones z ON z.id = r.zone_id
               LEFT JOIN ancora_crm.plugin_restaurant_tables t ON t.id = r.table_id
               WHERE r.instance_id = $1 AND r.date >= CURRENT_DATE
               ORDER BY r.date, r.time, r.created_at DESC
               LIMIT $2""",
            instance_id,
            limit,
        )
    return [dict(r) for r in rows]


async def list_zones(db, instance_id: int) -> List[dict]:
    rows = await db.fetch(
        """SELECT z.*,
                  COALESCE(COUNT(t.id) FILTER (WHERE t.is_active = true), 0) AS active_tables,
                  COALESCE(SUM(t.seats) FILTER (WHERE t.is_active = true), 0) AS active_table_seats
           FROM ancora_crm.plugin_restaurant_zones z
           LEFT JOIN ancora_crm.plugin_restaurant_tables t ON t.zone_id = z.id
           WHERE z.instance_id = $1
           GROUP BY z.id
           ORDER BY z.name""",
        instance_id,
    )
    return [dict(r) for r in rows]


async def create_zone(db, instance_id: int, name: str, capacity: int) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_restaurant_zones (instance_id, name, capacity)
           VALUES ($1, $2, $3)
           RETURNING *""",
        instance_id,
        name,
        capacity,
    )
    return dict(row)


async def update_zone(db, instance_id: int, zone_id: int, **kwargs) -> Optional[dict]:
    if not await _get_zone(db, instance_id, zone_id):
        return None

    allowed_fields = {"name", "capacity", "is_active"}
    params: list[Any] = []
    assignments = []
    index = 1
    for field, value in kwargs.items():
        if field not in allowed_fields:
            continue
        assignments.append(f"{field} = ${index}")
        params.append(value)
        index += 1
    if not assignments:
        return await _get_zone(db, instance_id, zone_id)

    params.extend([zone_id, instance_id])
    row = await db.fetchrow(
        f"""UPDATE ancora_crm.plugin_restaurant_zones
            SET {", ".join(assignments)}
            WHERE id = ${index} AND instance_id = ${index + 1}
            RETURNING *""",
        *params,
    )
    return dict(row) if row else None


async def delete_zone(db, instance_id: int, zone_id: int) -> bool:
    result = await db.execute(
        """UPDATE ancora_crm.plugin_restaurant_zones
           SET is_active = false
           WHERE id = $1 AND instance_id = $2 AND is_active = true""",
        zone_id,
        instance_id,
    )
    return int(result.split(" ")[1]) > 0


async def create_table(db, instance_id: int, zone_id: int, table_number: str, seats: int) -> dict:
    zone = await _get_zone(db, instance_id, zone_id, active_only=True)
    if not zone:
        raise ValueError("Zona no encontrada o inactiva")

    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_restaurant_tables (zone_id, table_number, seats)
           VALUES ($1, $2, $3)
           RETURNING *""",
        zone_id,
        table_number,
        seats,
    )
    return dict(row)


async def list_tables(db, instance_id: int, zone_id: int) -> List[dict]:
    rows = await db.fetch(
        """SELECT t.*, z.name AS zone_name
           FROM ancora_crm.plugin_restaurant_tables t
           INNER JOIN ancora_crm.plugin_restaurant_zones z ON z.id = t.zone_id
           WHERE z.instance_id = $1 AND z.id = $2
           ORDER BY t.table_number""",
        instance_id,
        zone_id,
    )
    return [dict(r) for r in rows]


async def update_table(db, instance_id: int, table_id: int, **kwargs) -> Optional[dict]:
    if not await _get_table(db, instance_id, table_id):
        return None

    allowed_fields = {"table_number", "seats", "is_active"}
    params: list[Any] = []
    assignments = []
    index = 1
    for field, value in kwargs.items():
        if field not in allowed_fields:
            continue
        assignments.append(f"{field} = ${index}")
        params.append(value)
        index += 1
    if not assignments:
        return await _get_table(db, instance_id, table_id)

    params.extend([table_id, instance_id])
    row = await db.fetchrow(
        f"""UPDATE ancora_crm.plugin_restaurant_tables AS t
            SET {", ".join(assignments)}
            FROM ancora_crm.plugin_restaurant_zones AS z
            WHERE t.zone_id = z.id AND t.id = ${index} AND z.instance_id = ${index + 1}
            RETURNING t.*, z.instance_id, z.is_active AS zone_active""",
        *params,
    )
    return dict(row) if row else None


async def delete_table(db, instance_id: int, table_id: int) -> bool:
    result = await db.execute(
        """UPDATE ancora_crm.plugin_restaurant_tables AS t
           SET is_active = false
           FROM ancora_crm.plugin_restaurant_zones AS z
           WHERE t.zone_id = z.id AND t.id = $1 AND z.instance_id = $2 AND t.is_active = true""",
        table_id,
        instance_id,
    )
    return int(result.split(" ")[1]) > 0
