"""Broadcasts business logic."""
import asyncio
import logging
from typing import List, Optional

from app.services.chatbot_whatsapp import send_message


logger = logging.getLogger(__name__)


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


async def resolve_audience(db, instance_id: int, campaign: dict) -> List[dict]:
    target_tags = campaign.get("target_tags") or []
    if target_tags:
        rows = await db.fetch(
            """SELECT phone, name
               FROM ancora_crm.plugin_broadcasts_recipients
               WHERE instance_id = $1
                 AND opt_in_marketing = true
                 AND opted_out_at IS NULL
                 AND tags && $2::text[]
               ORDER BY created_at DESC""",
            instance_id,
            target_tags,
        )
    else:
        rows = await db.fetch(
            """SELECT phone, name
               FROM ancora_crm.plugin_broadcasts_recipients
               WHERE instance_id = $1
                 AND opt_in_marketing = true
                 AND opted_out_at IS NULL
               ORDER BY created_at DESC""",
            instance_id,
        )
    return [dict(row) for row in rows]


async def send_campaign(db, instance_id: int, campaign_id: int) -> dict:
    campaign = await get_campaign(db, instance_id, campaign_id)
    if not campaign:
        raise ValueError("Campaign not found")
    if campaign["status"] not in {"draft", "scheduled"}:
        raise ValueError(f"Invalid campaign status: {campaign['status']}")

    creds = await db.fetchrow(
        """SELECT whatsapp_access_token, phone_number_id
           FROM ancora_crm.chatbot_instances
           WHERE id = $1""",
        instance_id,
    )
    creds = dict(creds) if creds else None
    if not creds or not creds.get("whatsapp_access_token") or not creds.get("phone_number_id"):
        raise ValueError("WhatsApp credentials not configured for this instance")

    await db.execute(
        """UPDATE ancora_crm.plugin_broadcasts_campaigns
           SET status = 'sending', updated_at = NOW()
           WHERE id = $1 AND instance_id = $2""",
        campaign_id,
        instance_id,
    )

    audience = await resolve_audience(db, instance_id, campaign)
    if not audience:
        await db.execute(
            """UPDATE ancora_crm.plugin_broadcasts_campaigns
               SET status = 'sent',
                   total_recipients = 0,
                   total_sent = 0,
                   total_delivered = 0,
                   total_failed = 0,
                   updated_at = NOW()
               WHERE id = $1 AND instance_id = $2""",
            campaign_id,
            instance_id,
        )
        return {
            "campaign_id": campaign_id,
            "status": "sent",
            "total_recipients": 0,
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
        }

    total_sent = 0
    total_delivered = 0
    total_failed = 0

    for recipient in audience:
        phone = recipient["phone"]
        try:
            response = await send_message(
                to=phone,
                body=campaign["message_template"],
                access_token=creds["whatsapp_access_token"],
                phone_number_id=str(creds["phone_number_id"]),
            )
            if not response:
                raise RuntimeError("WhatsApp send_message returned no response")

            await db.execute(
                """INSERT INTO ancora_crm.plugin_broadcasts_send_log
                   (campaign_id, recipient_phone, recipient_name, status, sent_at, delivered_at)
                   VALUES ($1, $2, $3, 'sent', NOW(), NOW())""",
                campaign_id,
                phone,
                recipient.get("name"),
            )
            total_sent += 1
            total_delivered += 1
        except Exception as exc:
            logger.exception("Campaign %s failed for %s", campaign_id, phone)
            await db.execute(
                """INSERT INTO ancora_crm.plugin_broadcasts_send_log
                   (campaign_id, recipient_phone, recipient_name, status, error_message)
                   VALUES ($1, $2, $3, 'failed', $4)""",
                campaign_id,
                phone,
                recipient.get("name"),
                str(exc),
            )
            total_failed += 1

        await asyncio.sleep(0.05)

    await db.execute(
        """UPDATE ancora_crm.plugin_broadcasts_campaigns
           SET status = 'sent',
               total_recipients = $3,
               total_sent = $4,
               total_delivered = $5,
               total_failed = $6,
               updated_at = NOW()
           WHERE id = $1 AND instance_id = $2""",
        campaign_id,
        instance_id,
        len(audience),
        total_sent,
        total_delivered,
        total_failed,
    )
    return {
        "campaign_id": campaign_id,
        "status": "sent",
        "total_recipients": len(audience),
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_failed": total_failed,
    }


async def check_scheduled_campaigns(db) -> List[dict]:
    rows = await db.fetch(
        """SELECT id, instance_id
           FROM ancora_crm.plugin_broadcasts_campaigns
           WHERE status = 'scheduled'
             AND scheduled_at IS NOT NULL
             AND scheduled_at <= NOW()
           ORDER BY scheduled_at ASC"""
    )

    results = []
    for row in rows:
        try:
            results.append(await send_campaign(db, row["instance_id"], row["id"]))
        except Exception as exc:
            logger.exception("Scheduled campaign %s failed", row["id"])
            results.append(
                {
                    "campaign_id": row["id"],
                    "instance_id": row["instance_id"],
                    "status": "failed",
                    "error": str(exc),
                }
            )
    return results


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


async def get_send_log(db, instance_id: int, campaign_id: int, limit: int = 100) -> List[dict]:
    return [
        dict(r) for r in await db.fetch(
            """SELECT l.*
               FROM ancora_crm.plugin_broadcasts_send_log l
               INNER JOIN ancora_crm.plugin_broadcasts_campaigns c ON c.id = l.campaign_id
               WHERE l.campaign_id = $1 AND c.instance_id = $2
               ORDER BY l.created_at DESC
               LIMIT $3""",
            campaign_id,
            instance_id,
            limit,
        )
    ]
