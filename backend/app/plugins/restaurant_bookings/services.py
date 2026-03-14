"""Restaurant bookings business logic."""
from typing import List, Optional
from datetime import date


async def check_availability(db, instance_id: int, target_date: date, time: str, party_size: int) -> dict:
    reservations = await db.fetch(
        "SELECT SUM(party_size) as total FROM ancora_crm.plugin_restaurant_reservations WHERE instance_id = $1 AND date = $2 AND time = $3 AND status != 'cancelada'",
        instance_id, target_date, time)
    total_booked = reservations[0]["total"] or 0
    zones = await db.fetch("SELECT SUM(capacity) as total FROM ancora_crm.plugin_restaurant_zones WHERE instance_id = $1 AND is_active = true", instance_id)
    total_capacity = zones[0]["total"] or 50
    available = total_capacity - total_booked
    return {"date": target_date.isoformat(), "time": time, "party_size": party_size, "available_seats": available, "can_book": available >= party_size}


async def create_reservation(db, instance_id: int, client_name: str, client_phone: str, target_date: date, time: str, party_size: int, notes: str = None, allergies: str = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_restaurant_reservations (instance_id, client_name, client_phone, date, time, party_size, notes, allergies)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
        instance_id, client_name, client_phone, target_date, time, party_size, notes, allergies)
    return dict(row)


async def find_by_phone(db, instance_id: int, phone: str, upcoming_only: bool = True) -> List[dict]:
    cond = "instance_id = $1 AND client_phone = $2"
    if upcoming_only:
        cond += " AND date >= CURRENT_DATE AND status != 'cancelada'"
    return [dict(r) for r in await db.fetch(f"SELECT * FROM ancora_crm.plugin_restaurant_reservations WHERE {cond} ORDER BY date, time", instance_id, phone)]


async def cancel_reservation(db, instance_id: int, reservation_id: int) -> bool:
    result = await db.execute("UPDATE ancora_crm.plugin_restaurant_reservations SET status = 'cancelada', updated_at = NOW() WHERE id = $1 AND instance_id = $2", reservation_id, instance_id)
    return int(result.split(" ")[1]) > 0


async def list_reservations(db, instance_id: int, target_date: date = None, limit: int = 50) -> List[dict]:
    if target_date:
        return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_restaurant_reservations WHERE instance_id = $1 AND date = $2 ORDER BY time", instance_id, target_date)]
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_restaurant_reservations WHERE instance_id = $1 AND date >= CURRENT_DATE ORDER BY date, time LIMIT $2", instance_id, limit)]


async def list_zones(db, instance_id: int) -> List[dict]:
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_restaurant_zones WHERE instance_id = $1 ORDER BY name", instance_id)]


async def create_zone(db, instance_id: int, name: str, capacity: int) -> dict:
    row = await db.fetchrow("INSERT INTO ancora_crm.plugin_restaurant_zones (instance_id, name, capacity) VALUES ($1, $2, $3) RETURNING *", instance_id, name, capacity)
    return dict(row)
