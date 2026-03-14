"""Advanced CRM business logic."""
from typing import List, Optional
import secrets
import string


def _gen_code(prefix="CL") -> str:
    nums = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"{prefix}-{nums}"


async def lookup_customer(db, instance_id: int, phone: str = None, customer_code: str = None) -> Optional[dict]:
    if phone:
        row = await db.fetchrow("SELECT * FROM ancora_crm.plugin_crm_customer_profiles WHERE instance_id = $1 AND phone = $2", instance_id, phone)
    elif customer_code:
        row = await db.fetchrow("SELECT * FROM ancora_crm.plugin_crm_customer_profiles WHERE instance_id = $1 AND customer_code = $2", instance_id, customer_code)
    else:
        return None
    return dict(row) if row else None


async def get_or_create_profile(db, instance_id: int, phone: str, name: str = None) -> dict:
    existing = await lookup_customer(db, instance_id, phone=phone)
    if existing:
        return existing
    code = _gen_code()
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_crm_customer_profiles (instance_id, phone, name, customer_code)
           VALUES ($1, $2, $3, $4) RETURNING *""",
        instance_id, phone, name, code)
    return dict(row)


async def update_profile(db, instance_id: int, profile_id: int, **kwargs) -> Optional[dict]:
    allowed = {"name", "tags", "notes", "vip_status", "total_visits", "total_spent", "last_visit_at"}
    updates, params = [], []
    idx = 3
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            updates.append(f"{k} = ${idx}")
            params.append(v)
            idx += 1
    if not updates:
        return None
    updates.append("updated_at = NOW()")
    row = await db.fetchrow(f"UPDATE ancora_crm.plugin_crm_customer_profiles SET {', '.join(updates)} WHERE id = $1 AND instance_id = $2 RETURNING *", profile_id, instance_id, *params)
    return dict(row) if row else None


async def list_profiles(db, instance_id: int, vip_only: bool = False, search: str = None, limit: int = 100) -> List[dict]:
    cond = ["instance_id = $1"]
    params = [instance_id]
    idx = 2
    if vip_only:
        cond.append("vip_status = true")
    if search:
        cond.append(f"(name ILIKE ${idx} OR phone ILIKE ${idx} OR customer_code ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1
    query = f"SELECT * FROM ancora_crm.plugin_crm_customer_profiles WHERE {' AND '.join(cond)} ORDER BY updated_at DESC LIMIT {limit}"
    return [dict(r) for r in await db.fetch(query, *params)]


async def add_interaction(db, profile_id: int, interaction_type: str, description: str = None, amount: float = None) -> dict:
    row = await db.fetchrow(
        "INSERT INTO ancora_crm.plugin_crm_interactions (profile_id, interaction_type, description, amount) VALUES ($1, $2, $3, $4) RETURNING *",
        profile_id, interaction_type, description, amount)
    # Update visit count and spending
    await db.execute(
        """UPDATE ancora_crm.plugin_crm_customer_profiles
           SET total_visits = total_visits + 1, total_spent = total_spent + COALESCE($2, 0), last_visit_at = NOW(), updated_at = NOW()
           WHERE id = $1""", profile_id, amount or 0)
    return dict(row)


async def get_customer_history(db, profile_id: int, limit: int = 20) -> List[dict]:
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_crm_interactions WHERE profile_id = $1 ORDER BY created_at DESC LIMIT $2", profile_id, limit)]
