"""Closures business logic."""
from datetime import date
from typing import List, Optional


def _serialize_closure(row) -> dict:
    closure = dict(row)
    closure["affects_all_services"] = closure.get("affects_all")
    return closure


async def list_closures(
    db,
    instance_id: int,
    from_date: Optional[date] = None,
    include_past: bool = True,
    limit: int = 100,
) -> List[dict]:
    conditions = ["instance_id = $1"]
    params: list = [instance_id]
    idx = 2

    if from_date:
        conditions.append(f"end_date >= ${idx}")
        params.append(from_date)
        idx += 1
    elif not include_past:
        conditions.append("end_date >= CURRENT_DATE")

    query = f"""
        SELECT *
        FROM ancora_crm.plugin_closures
        WHERE {" AND ".join(conditions)}
        ORDER BY start_date ASC, end_date ASC
        LIMIT {limit}
    """
    rows = await db.fetch(query, *params)
    return [_serialize_closure(r) for r in rows]


async def get_closure(db, instance_id: int, closure_id: int) -> Optional[dict]:
    row = await db.fetchrow(
        "SELECT * FROM ancora_crm.plugin_closures WHERE id = $1 AND instance_id = $2",
        closure_id, instance_id,
    )
    return _serialize_closure(row) if row else None


async def create_closure(
    db,
    instance_id: int,
    start_date: date,
    end_date: date,
    reason: Optional[str],
    closure_type: str = "other",
    affects_all: bool = True,
) -> dict:
    if end_date < start_date:
        raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")

    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_closures
           (instance_id, start_date, end_date, reason, closure_type, affects_all)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING *""",
        instance_id, start_date, end_date, reason, closure_type, affects_all,
    )
    return _serialize_closure(row)


async def update_closure(db, instance_id: int, closure_id: int, **kwargs) -> Optional[dict]:
    allowed = {"start_date", "end_date", "reason", "closure_type", "affects_all"}
    existing = await db.fetchrow(
        "SELECT * FROM ancora_crm.plugin_closures WHERE id = $1 AND instance_id = $2",
        closure_id, instance_id,
    )
    if not existing:
        return None

    new_start = kwargs.get("start_date", existing["start_date"])
    new_end = kwargs.get("end_date", existing["end_date"])
    if new_end < new_start:
        raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")

    updates = []
    params = []
    idx = 3
    for key, val in kwargs.items():
        if key in allowed and val is not None:
            updates.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1
    if not updates:
        return _serialize_closure(existing)

    row = await db.fetchrow(
        f"UPDATE ancora_crm.plugin_closures SET {', '.join(updates)} WHERE id = $1 AND instance_id = $2 RETURNING *",
        closure_id, instance_id, *params,
    )
    return _serialize_closure(row) if row else None


async def delete_closure(db, instance_id: int, closure_id: int) -> bool:
    result = await db.execute(
        "DELETE FROM ancora_crm.plugin_closures WHERE id = $1 AND instance_id = $2",
        closure_id, instance_id,
    )
    return int(result.split(" ")[1]) > 0


async def get_closure_for_date(db, instance_id: int, target_date: date) -> Optional[dict]:
    row = await db.fetchrow(
        """SELECT *
           FROM ancora_crm.plugin_closures
           WHERE instance_id = $1
             AND start_date <= $2
             AND end_date >= $2
           ORDER BY start_date ASC, created_at ASC
           LIMIT 1""",
        instance_id, target_date,
    )
    return _serialize_closure(row) if row else None


async def check_closures(db, instance_id: int, target_date: date) -> dict:
    closure = await get_closure_for_date(db, instance_id, target_date)
    if not closure:
        return {"closed": False, "date": target_date.isoformat()}

    return {
        "closed": True,
        "date": target_date.isoformat(),
        "closure": closure,
        "reason": closure.get("reason"),
        "closure_type": closure.get("closure_type"),
        "affects_all_services": closure.get("affects_all"),
    }


async def list_upcoming_closures(db, instance_id: int, limit: int = 10) -> List[dict]:
    rows = await db.fetch(
        """SELECT *
           FROM ancora_crm.plugin_closures
           WHERE instance_id = $1
             AND end_date >= CURRENT_DATE
           ORDER BY start_date ASC, end_date ASC
           LIMIT $2""",
        instance_id, limit,
    )
    return [_serialize_closure(r) for r in rows]
