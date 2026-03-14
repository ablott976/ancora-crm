"""Consent forms business logic."""
from typing import List, Optional
from datetime import date, timedelta


async def list_templates(db, instance_id: int) -> List[dict]:
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_consent_templates WHERE instance_id = $1 AND is_active = true ORDER BY name", instance_id)]


async def create_template(db, instance_id: int, name: str, content_html: str, service_id: int = None, requires_id: bool = False, requires_signature: bool = True) -> dict:
    row = await db.fetchrow(
        "INSERT INTO ancora_crm.plugin_consent_templates (instance_id, name, content_html, service_id, requires_id_number, requires_signature) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
        instance_id, name, content_html, service_id, requires_id, requires_signature)
    return dict(row)


async def create_consent_record(db, instance_id: int, template_id: int, client_name: str, client_phone: str = None, appointment_id: int = None, retention_years: int = 3) -> dict:
    retention = date.today() + timedelta(days=retention_years * 365)
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_consent_records (instance_id, template_id, appointment_id, client_name, client_phone, retention_until)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
        instance_id, template_id, appointment_id, client_name, client_phone, retention)
    return dict(row)


async def sign_consent(db, record_id: int, signature_data: str = None, id_number: str = None, ip_address: str = None) -> Optional[dict]:
    row = await db.fetchrow(
        "UPDATE ancora_crm.plugin_consent_records SET status = 'signed', signed_at = NOW(), signature_data = $2, client_id_number = $3, ip_address = $4 WHERE id = $1 RETURNING *",
        record_id, signature_data, id_number, ip_address)
    return dict(row) if row else None


async def pending_for_phone(db, instance_id: int, phone: str) -> List[dict]:
    return [dict(r) for r in await db.fetch(
        """SELECT cr.*, ct.name as template_name FROM ancora_crm.plugin_consent_records cr
           JOIN ancora_crm.plugin_consent_templates ct ON cr.template_id = ct.id
           WHERE cr.instance_id = $1 AND cr.client_phone = $2 AND cr.status = 'pending'
           ORDER BY cr.created_at""", instance_id, phone)]


async def list_records(db, instance_id: int, status: str = None, limit: int = 50) -> List[dict]:
    cond = "cr.instance_id = $1"
    params = [instance_id]
    if status:
        cond += " AND cr.status = $2"
        params.append(status)
    return [dict(r) for r in await db.fetch(
        f"""SELECT cr.*, ct.name as template_name FROM ancora_crm.plugin_consent_records cr
            JOIN ancora_crm.plugin_consent_templates ct ON cr.template_id = ct.id
            WHERE {cond} ORDER BY cr.created_at DESC LIMIT {limit}""", *params)]
