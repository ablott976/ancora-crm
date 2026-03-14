"""Daily menus business logic."""
from datetime import date, datetime
from typing import List, Optional
import pytz

TZ = pytz.timezone("Europe/Madrid")


async def _get_menu_items(db, menu_id: int) -> List[dict]:
    rows = await db.fetch(
        """SELECT *
           FROM ancora_crm.plugin_daily_menu_items
           WHERE menu_id = $1
           ORDER BY sort_order ASC, id ASC""",
        menu_id,
    )
    return [dict(r) for r in rows]


async def _attach_items(db, menu: dict) -> dict:
    menu["items"] = await _get_menu_items(db, menu["id"])
    return menu


async def list_menus(
    db,
    instance_id: int,
    target_date: Optional[date] = None,
    active_only: bool = False,
) -> List[dict]:
    conditions = ["instance_id = $1"]
    params: list = [instance_id]
    idx = 2

    if target_date:
        conditions.append(f"date = ${idx}")
        params.append(target_date)
        idx += 1

    if active_only:
        conditions.append("is_active = true")

    where = " AND ".join(conditions)
    rows = await db.fetch(
        f"""SELECT *
            FROM ancora_crm.plugin_daily_menus
            WHERE {where}
            ORDER BY date DESC, created_at DESC, id DESC""",
        *params,
    )
    menus = [dict(r) for r in rows]
    for menu in menus:
        menu["items"] = await _get_menu_items(db, menu["id"])
    return menus


async def get_menu(db, instance_id: int, menu_id: int) -> Optional[dict]:
    row = await db.fetchrow(
        """SELECT *
           FROM ancora_crm.plugin_daily_menus
           WHERE id = $1 AND instance_id = $2""",
        menu_id, instance_id,
    )
    if not row:
        return None
    return await _attach_items(db, dict(row))


async def get_menu_for_date(
    db,
    instance_id: int,
    target_date: date,
    active_only: bool = True,
) -> Optional[dict]:
    row = await db.fetchrow(
        f"""SELECT *
            FROM ancora_crm.plugin_daily_menus
            WHERE instance_id = $1 AND date = $2
            {"AND is_active = true" if active_only else ""}
            ORDER BY created_at DESC, id DESC
            LIMIT 1""",
        instance_id, target_date,
    )
    if not row:
        return None
    return await _attach_items(db, dict(row))


async def get_todays_menu(db, instance_id: int) -> Optional[dict]:
    today = datetime.now(TZ).date()
    return await get_menu_for_date(db, instance_id, today, active_only=True)


async def create_menu(
    db,
    instance_id: int,
    target_date: date,
    name: str,
    price: Optional[float] = None,
    is_active: bool = True,
) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_daily_menus
           (instance_id, date, name, price, is_active)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING *""",
        instance_id, target_date, name, price, is_active,
    )
    return await _attach_items(db, dict(row))


async def update_menu(db, instance_id: int, menu_id: int, **kwargs) -> Optional[dict]:
    allowed = {"date", "name", "price", "is_active"}
    updates = []
    params = []
    idx = 3
    for key, val in kwargs.items():
        if key in allowed and val is not None:
            updates.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1
    if not updates:
        return await get_menu(db, instance_id, menu_id)

    row = await db.fetchrow(
        f"""UPDATE ancora_crm.plugin_daily_menus
            SET {", ".join(updates)}
            WHERE id = $1 AND instance_id = $2
            RETURNING *""",
        menu_id, instance_id, *params,
    )
    if not row:
        return None
    return await _attach_items(db, dict(row))


async def delete_menu(db, instance_id: int, menu_id: int) -> bool:
    result = await db.execute(
        "DELETE FROM ancora_crm.plugin_daily_menus WHERE id = $1 AND instance_id = $2",
        menu_id, instance_id,
    )
    return int(result.split(" ")[1]) > 0


async def list_menu_items(db, instance_id: int, menu_id: int) -> Optional[List[dict]]:
    menu = await db.fetchrow(
        "SELECT 1 FROM ancora_crm.plugin_daily_menus WHERE id = $1 AND instance_id = $2",
        menu_id, instance_id,
    )
    if not menu:
        return None
    return await _get_menu_items(db, menu_id)


async def create_menu_item(
    db,
    instance_id: int,
    menu_id: int,
    name: str,
    description: Optional[str] = None,
    course_type: Optional[str] = None,
    allergens: Optional[str] = None,
    sort_order: int = 0,
) -> Optional[dict]:
    menu = await db.fetchrow(
        "SELECT 1 FROM ancora_crm.plugin_daily_menus WHERE id = $1 AND instance_id = $2",
        menu_id, instance_id,
    )
    if not menu:
        return None

    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_daily_menu_items
           (menu_id, name, description, course_type, allergens, sort_order)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING *""",
        menu_id, name, description, course_type, allergens, sort_order,
    )
    return dict(row)


async def update_menu_item(db, instance_id: int, menu_id: int, item_id: int, **kwargs) -> Optional[dict]:
    allowed = {"name", "description", "course_type", "allergens", "sort_order"}
    updates = []
    params = []
    idx = 4
    for key, val in kwargs.items():
        if key in allowed and val is not None:
            updates.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1
    if not updates:
        row = await db.fetchrow(
            """SELECT i.*
               FROM ancora_crm.plugin_daily_menu_items i
               JOIN ancora_crm.plugin_daily_menus m ON i.menu_id = m.id
               WHERE i.id = $1 AND i.menu_id = $2 AND m.instance_id = $3""",
            item_id, menu_id, instance_id,
        )
        return dict(row) if row else None

    row = await db.fetchrow(
        f"""UPDATE ancora_crm.plugin_daily_menu_items i
            SET {", ".join(updates)}
            FROM ancora_crm.plugin_daily_menus m
            WHERE i.id = $1 AND i.menu_id = $2 AND i.menu_id = m.id AND m.instance_id = $3
            RETURNING i.*""",
        item_id, menu_id, instance_id, *params,
    )
    return dict(row) if row else None


async def delete_menu_item(db, instance_id: int, menu_id: int, item_id: int) -> bool:
    result = await db.execute(
        """DELETE FROM ancora_crm.plugin_daily_menu_items i
           USING ancora_crm.plugin_daily_menus m
           WHERE i.id = $1 AND i.menu_id = $2 AND i.menu_id = m.id AND m.instance_id = $3""",
        item_id, menu_id, instance_id,
    )
    return int(result.split(" ")[1]) > 0
