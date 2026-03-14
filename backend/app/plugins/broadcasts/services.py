"""Broadcasts business logic."""
from typing import List, Optional
from datetime import datetime


async def list_campaigns(db, instance_id: int, status: Optional[str] = None, limit: int = 50) -> List[dict]:
    conditions = ["instance_id = $1"]
    params = [instance_id]
    if status:
        conditions.append("status = $2")
        params.append(status)
    query = f"SELECT * FROM ancora_crm.plugin_broadcasts_campaigns WHERE {' AND '.join(conditions)} ORDER BY created_at DESC LIMIT {limit}"
    return [dict(r) for r in await db.fetch(query, *params)]


async def get_campaign(db, instance_id: int, campaign_id: int) -> Optional[dict]:
    row = await db.fetchrow("SELECT * FROM ancora_crm.plugin_broadcasts_campaigns WHERE id = $1 AND instance_id = $2", campaign_id, instance_id)
    return dict(row) if row else None


async def create_campaign(db, instance_id: int, name: str, message_template: str, target_tags: list = None, scheduled_at=None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_broadcasts_campaigns (instance_id, name, message_template, target_tags, scheduled_at)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        instance_id, name, message_template, target_tags or [], scheduled_at)
    return dict(row)


async def update_campaign(db, instance_id: int, campaign_id: int, **kwargs) -> Optional[dict]:
    allowed = {"name", "message_template", "target_tags", "scheduled_at", "status"}
    updates, params = [], []
    idx = 3
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            updates.append(f"{k} = ${idx}")
            params.append(v)
            idx += 1
    if not updates:
        return await get_campaign(db, instance_id, campaign_id)
    updates.append("updated_at = NOW()")
    row = await db.fetchrow(f"UPDATE ancora_crm.plugin_broadcasts_campaigns SET {', '.join(updates)} WHERE id = $1 AND instance_id = $2 RETURNING *", campaign_id, instance_id, *params)
    return dict(row) if row else None


async def delete_campaign(db, instance_id: int, campaign_id: int) -> bool:
    result = await db.execute("DELETE FROM ancora_crm.plugin_broadcasts_campaigns WHERE id = $1 AND instance_id = $2 AND status = 'draft'", campaign_id, instance_id)
    return int(result.split(" ")[1]) > 0


async def list_recipients(db, instance_id: int, opted_in_only: bool = False, limit: int = 200) -> List[dict]:
    cond = "instance_id = $1"
    if opted_in_only:
        cond += " AND opt_in_marketing = true AND opted_out_at IS NULL"
    return [dict(r) for r in await db.fetch(f"SELECT * FROM ancora_crm.plugin_broadcasts_recipients WHERE {cond} ORDER BY created_at DESC LIMIT {limit}", instance_id)]


async def add_recipient(db, instance_id: int, phone: str, name: str = None, tags: list = None, opt_in: bool = False) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_broadcasts_recipients (instance_id, phone, name, tags, opt_in_marketing, opt_in_at)
           VALUES ($1, $2, $3, $4, $5, CASE WHEN $5 THEN NOW() ELSE NULL END)
           ON CONFLICT (instance_id, phone) DO UPDATE SET name = COALESCE(EXCLUDED.name, plugin_broadcasts_recipients.name), tags = EXCLUDED.tags, opt_in_marketing = EXCLUDED.opt_in_marketing, opt_in_at = CASE WHEN EXCLUDED.opt_in_marketing THEN NOW() ELSE plugin_broadcasts_recipients.opt_in_at END
           RETURNING *""",
        instance_id, phone, name, tags or [], opt_in)
    return dict(row)


async def opt_out_recipient(db, instance_id: int, phone: str) -> bool:
    result = await db.execute("UPDATE ancora_crm.plugin_broadcasts_recipients SET opt_in_marketing = false, opted_out_at = NOW() WHERE instance_id = $1 AND phone = $2", instance_id, phone)
    return int(result.split(" ")[1]) > 0


async def get_send_log(db, campaign_id: int, limit: int = 100) -> List[dict]:
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_broadcasts_send_log WHERE campaign_id = $1 ORDER BY created_at DESC LIMIT $2", campaign_id, limit)]
