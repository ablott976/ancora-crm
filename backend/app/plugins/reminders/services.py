"""Reminders business logic."""
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional
import pytz
import logging

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Madrid")


async def list_templates(db, instance_id: int) -> List[dict]:
    rows = await db.fetch(
        "SELECT * FROM ancora_crm.plugin_reminders_templates WHERE instance_id = $1 ORDER BY type, hours_before",
        instance_id,
    )
    return [dict(r) for r in rows]


async def create_template(
    db, instance_id: int, name: str, type: str, hours_before: int,
    template_text: str, send_to: str = "client",
) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_reminders_templates
           (instance_id, name, type, hours_before, template_text, send_to)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
        instance_id, name, type, hours_before, template_text, send_to,
    )
    return dict(row)


async def update_template(db, instance_id: int, template_id: int, **kwargs) -> Optional[dict]:
    allowed = {"name", "type", "hours_before", "template_text", "is_active", "send_to"}
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
        f"UPDATE ancora_crm.plugin_reminders_templates SET {set_clause} WHERE id = $1 AND instance_id = $2 RETURNING *",
        template_id, instance_id, *params,
    )
    return dict(row) if row else None


async def delete_template(db, instance_id: int, template_id: int) -> bool:
    result = await db.execute(
        "DELETE FROM ancora_crm.plugin_reminders_templates WHERE id = $1 AND instance_id = $2",
        template_id, instance_id,
    )
    return int(result.split(" ")[1]) > 0


async def get_reminder_log(db, instance_id: int, limit: int = 50) -> List[dict]:
    rows = await db.fetch(
        """SELECT rl.*, rt.name as template_name
           FROM ancora_crm.plugin_reminders_log rl
           LEFT JOIN ancora_crm.plugin_reminders_templates rt ON rl.template_id = rt.id
           WHERE rl.instance_id = $1
           ORDER BY rl.created_at DESC LIMIT $2""",
        instance_id, limit,
    )
    return [dict(r) for r in rows]


def render_template(template_text: str, appointment: dict) -> str:
    """Replace placeholders in template text with appointment data."""
    replacements = {
        "{nombre_cliente}": appointment.get("client_name", ""),
        "{telefono_cliente}": appointment.get("client_phone", ""),
        "{fecha}": str(appointment.get("date", "")),
        "{hora}": appointment.get("start_time", ""),
        "{servicio}": appointment.get("service_name", ""),
        "{profesional}": appointment.get("professional_name", ""),
    }
    text = template_text
    for key, val in replacements.items():
        text = text.replace(key, str(val))
    return text


async def check_and_send_reminders(db, instance_id: int, send_func=None):
    """Check for appointments needing reminders and create log entries.
    
    send_func: async function(phone, message, instance_config) to send WA messages.
    If None, just creates log entries without sending.
    """
    now = datetime.now(TZ)
    
    # Get active templates
    templates = await db.fetch(
        "SELECT * FROM ancora_crm.plugin_reminders_templates WHERE instance_id = $1 AND is_active = true AND type = 'pre'",
        instance_id,
    )
    
    if not templates:
        return 0
    
    sent_count = 0
    
    for template in templates:
        # Calculate target time window
        target_time = now + timedelta(hours=template["hours_before"])
        target_date = target_time.date()
        target_hour = target_time.strftime("%H:%M")
        
        # Find appointments in this window (within 30 min)
        window_start = (target_time - timedelta(minutes=15)).strftime("%H:%M")
        window_end = (target_time + timedelta(minutes=15)).strftime("%H:%M")
        
        appointments = await db.fetch(
            """SELECT a.*, p.name as professional_name, s.name as service_name
               FROM ancora_crm.plugin_bookings_appointments a
               LEFT JOIN ancora_crm.plugin_bookings_professionals p ON a.professional_id = p.id
               LEFT JOIN ancora_crm.plugin_bookings_services s ON a.service_id = s.id
               WHERE a.instance_id = $1 AND a.date = $2
               AND a.start_time >= $3 AND a.start_time <= $4
               AND a.status IN ('confirmada', 'pendiente')""",
            instance_id, target_date, window_start, window_end,
        )
        
        for appt in appointments:
            # Check if already sent
            existing = await db.fetchrow(
                """SELECT 1 FROM ancora_crm.plugin_reminders_log
                   WHERE instance_id = $1 AND appointment_id = $2 AND template_id = $3
                   AND status IN ('sent', 'pending')""",
                instance_id, appt["id"], template["id"],
            )
            if existing:
                continue
            
            # Render message
            message = render_template(template["template_text"], dict(appt))
            
            # Determine recipient
            if template["send_to"] == "client":
                phone = appt["client_phone"]
            else:
                phone = appt.get("professional_phone") or ""
            
            if not phone:
                continue
            
            # Create log entry
            status = "pending"
            error_msg = None
            
            if send_func:
                try:
                    await send_func(phone, message, instance_id)
                    status = "sent"
                except Exception as e:
                    status = "failed"
                    error_msg = str(e)
                    logger.error(f"Reminder send error: {e}")
            
            await db.execute(
                """INSERT INTO ancora_crm.plugin_reminders_log
                   (instance_id, appointment_id, template_id, recipient_phone, message_text, status, sent_at, error_message)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                instance_id, appt["id"], template["id"], phone, message,
                status, datetime.now(TZ) if status == "sent" else None, error_msg,
            )
            sent_count += 1
    
    return sent_count
