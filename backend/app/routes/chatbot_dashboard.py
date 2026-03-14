from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from datetime import timedelta, date
from itertools import groupby

from app.database import get_db
from app.models.chatbot import (
    BusinessInfo, ChatUser, ChatUserCreate, Prompt, ScheduleDay, ScheduleUpdate,
    Holiday, HolidayCreate, Contact, ContactUpdate, ConversationDay, ConversationMessage, Token, PromptConfigUpdate
)
from app.services.chatbot_auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_current_chatbot_user,
    get_password_hash, verify_password
)

router = APIRouter()

# Dependency to check if the instance exists
async def get_instance(instance_id: int, db=Depends(get_db)):
    instance = await db.fetchrow("SELECT id FROM ancora_crm.chatbot_instances WHERE id = $1", instance_id)
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot instance not found")
    return instance_id

# --- Auth ---
@router.post("/dashboard/{instance_id}/auth/login")
async def login_for_access_token(
    instance_id: int = Depends(get_instance),
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db=Depends(get_db)
):
    user = await db.fetchrow(
        "SELECT * FROM ancora_crm.chatbot_dashboard_users WHERE username = $1 AND instance_id = $2",
        form_data.username, instance_id
    )
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username'], "instance_id": instance_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/dashboard/{instance_id}/auth/change-password")
async def change_password(
    new_password: str,
    instance_id: int = Depends(get_instance),
    current_user = Depends(get_current_chatbot_user),
    db=Depends(get_db)
):
    hashed_password = get_password_hash(new_password)
    await db.execute(
        "UPDATE ancora_crm.chatbot_dashboard_users SET password_hash = $1 WHERE id = $2 AND instance_id = $3",
        hashed_password, current_user['id'], instance_id
    )
    return {"message": "Password changed successfully"}

# --- Business Info ---
@router.get("/dashboard/{instance_id}/settings")
async def get_settings(instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    info = await db.fetchrow("SELECT * FROM ancora_crm.chatbot_business_info WHERE instance_id = $1", instance_id)
    if not info:
        raise HTTPException(status_code=404, detail="Business info not found")
    return dict(info) if info else {}

@router.put("/dashboard/{instance_id}/settings")
async def update_settings(info: BusinessInfo, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    # Create a dict of the fields to update, excluding None values
    update_data = info.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
        
    set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(update_data.keys())])
    
    query = f"UPDATE ancora_crm.chatbot_business_info SET {set_clause} WHERE instance_id = $1 RETURNING *"
    
    updated_info = await db.fetchrow(query, instance_id, *update_data.values())
    if not updated_info:
        raise HTTPException(status_code=404, detail="Business info not found to update")
    return dict(updated_info) if updated_info else {}

# --- Users ---
@router.get("/dashboard/{instance_id}/users")
async def get_users(instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    users = await db.fetch("SELECT id, username, role FROM ancora_crm.chatbot_dashboard_users WHERE instance_id = $1", instance_id)
    return [dict(u) for u in users]

@router.post("/dashboard/{instance_id}/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_data: ChatUserCreate, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    existing_user = await db.fetchrow("SELECT id FROM ancora_crm.chatbot_dashboard_users WHERE username = $1 AND instance_id = $2", user_data.username, instance_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = get_password_hash(user_data.password)
    new_user = await db.fetchrow(
        "INSERT INTO ancora_crm.chatbot_dashboard_users (instance_id, username, password_hash, role) VALUES ($1, $2, $3, 'admin') RETURNING id, username, role",
        instance_id, user_data.username, hashed_password
    )
    return dict(new_user)

@router.put("/dashboard/{instance_id}/users/{user_id}")
async def update_user(user_id: int, user_data: ChatUserCreate, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    hashed_password = get_password_hash(user_data.password) if user_data.password else None
    
    if hashed_password:
        query = "UPDATE ancora_crm.chatbot_dashboard_users SET username = $1, password_hash = $2 WHERE id = $3 AND instance_id = $4 RETURNING id, username, role"
        params = (user_data.username, hashed_password, user_id, instance_id)
    else:
        query = "UPDATE ancora_crm.chatbot_dashboard_users SET username = $1 WHERE id = $2 AND instance_id = $3 RETURNING id, username, role"
        params = (user_data.username, user_id, instance_id)
        
    updated_user = await db.fetchrow(query, *params)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(updated_user) if updated_user else {}

@router.delete("/dashboard/{instance_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, instance_id: int = Depends(get_instance), db = Depends(get_db), current_user = Depends(get_current_chatbot_user)):
    if user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own user")
    
    deleted = await db.execute("DELETE FROM ancora_crm.chatbot_dashboard_users WHERE id = $1 AND instance_id = $2", user_id, instance_id)
    if not int(deleted.split(" ")[1]):
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Prompts ---
@router.get("/dashboard/{instance_id}/prompts")
async def get_prompts(instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    prompts = await db.fetch("SELECT * FROM ancora_crm.chatbot_prompts WHERE instance_id = $1", instance_id)
    return [dict(p) for p in prompts]

@router.put("/dashboard/{instance_id}/prompts/{prompt_id}")
async def update_prompt(prompt_id: int, prompt_data: Prompt, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    updated_prompt = await db.fetchrow(
        "UPDATE ancora_crm.chatbot_prompts SET content = $1, updated_at = NOW() WHERE id = $2 AND instance_id = $3 RETURNING *",
        prompt_data.content, prompt_id, instance_id
    )
    if not updated_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return dict(updated_prompt) if updated_prompt else {}

# --- Schedule ---
@router.get("/dashboard/{instance_id}/schedule")
async def get_schedule(instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    schedule = await db.fetch("SELECT * FROM ancora_crm.chatbot_schedule WHERE instance_id = $1 ORDER BY dia_semana", instance_id)
    return [dict(s) for s in schedule]

@router.put("/dashboard/{instance_id}/schedule")
async def update_schedule(schedule_data: ScheduleUpdate, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    async with db.transaction():
        for day in schedule_data.schedule:
            await db.execute(
                """
                INSERT INTO ancora_crm.chatbot_schedule (instance_id, dia_semana, hora_apertura, hora_cierre, abierto)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (instance_id, dia_semana) DO UPDATE SET
                    hora_apertura = EXCLUDED.hora_apertura,
                    hora_cierre = EXCLUDED.hora_cierre,
                    abierto = EXCLUDED.abierto
                """,
                instance_id, day.dia_semana, day.hora_apertura, day.hora_cierre, day.abierto
            )
    return await get_schedule(instance_id, db, user)

# --- Holidays ---
@router.get("/dashboard/{instance_id}/holidays")
async def get_holidays(instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    holidays = await db.fetch("SELECT * FROM ancora_crm.chatbot_holidays WHERE instance_id = $1 ORDER BY fecha", instance_id)
    return [dict(h) for h in holidays]

@router.post("/dashboard/{instance_id}/holidays", status_code=status.HTTP_201_CREATED)
async def create_holiday(holiday_data: HolidayCreate, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    new_holiday = await db.fetchrow(
        "INSERT INTO ancora_crm.chatbot_holidays (instance_id, fecha, nombre) VALUES ($1, $2, $3) RETURNING *",
        instance_id, holiday_data.fecha, holiday_data.nombre
    )
    return dict(new_holiday)

@router.delete("/dashboard/{instance_id}/holidays/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holiday(holiday_id: int, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    deleted = await db.execute("DELETE FROM ancora_crm.chatbot_holidays WHERE id = $1 AND instance_id = $2", holiday_id, instance_id)
    if not int(deleted.split(" ")[1]):
        raise HTTPException(status_code=404, detail="Holiday not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Contacts ---
@router.get("/dashboard/{instance_id}/contacts")
async def get_contacts(
    instance_id: int = Depends(get_instance), 
    db = Depends(get_db), 
    user = Depends(get_current_chatbot_user),
    search: str = None,
    page: int = 1,
    limit: int = 20
):
    offset = (page - 1) * limit
    if search:
        query = "SELECT * FROM ancora_crm.chatbot_contacts WHERE instance_id = $1 AND (name ILIKE $2 OR phone ILIKE $2) ORDER BY last_seen DESC LIMIT $3 OFFSET $4"
        params = (instance_id, f"%{search}%", limit, offset)
    else:
        query = "SELECT * FROM ancora_crm.chatbot_contacts WHERE instance_id = $1 ORDER BY last_seen DESC LIMIT $2 OFFSET $3"
        params = (instance_id, limit, offset)
    
    contacts = await db.fetch(query, *params)
    return [dict(c) for c in contacts]

@router.get("/dashboard/{instance_id}/contacts/{contact_id}")
async def get_contact(contact_id: int, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    contact = await db.fetchrow("SELECT * FROM ancora_crm.chatbot_contacts WHERE id = $1 AND instance_id = $2", contact_id, instance_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return dict(contact)

@router.put("/dashboard/{instance_id}/contacts/{contact_id}")
async def update_contact(contact_id: int, contact_data: ContactUpdate, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    update_data = contact_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    set_clause = ", ".join([f"{key} = ${i+3}" for i, key in enumerate(update_data.keys())])
    query = f"UPDATE ancora_crm.chatbot_contacts SET {set_clause} WHERE id = $1 AND instance_id = $2 RETURNING *"
    
    updated_contact = await db.fetchrow(query, contact_id, instance_id, *update_data.values())
    if not updated_contact:
        raise HTTPException(status_code=404, detail="Contact not found to update")
    return dict(updated_contact) if updated_contact else {}

@router.delete("/dashboard/{instance_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: int, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    # Note: ON DELETE CASCADE will handle conversations
    deleted = await db.execute("DELETE FROM ancora_crm.chatbot_contacts WHERE id = $1 AND instance_id = $2", contact_id, instance_id)
    if not int(deleted.split(" ")[1]):
        raise HTTPException(status_code=404, detail="Contact not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Conversations ---
@router.get("/dashboard/{instance_id}/contacts/{contact_id}/conversations")
async def get_conversations(contact_id: int, instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    query = "SELECT role, message, created_at FROM ancora_crm.chatbot_conversations WHERE contact_id = $1 AND instance_id = $2 ORDER BY created_at"
    messages = await db.fetch(query, contact_id, instance_id)
    
    grouped_by_day = []
    for key, group in groupby(messages, key=lambda m: m['created_at'].date()):
        grouped_by_day.append(ConversationDay(
            date=key,
            messages=[ConversationMessage(**dict(msg)) for msg in group]
        ))
    return grouped_by_day

@router.get("/dashboard/{instance_id}/conversations/recent")
async def get_recent_conversations(instance_id: int = Depends(get_instance), db = Depends(get_db), user = Depends(get_current_chatbot_user)):
    query = """
    SELECT c.*
    FROM ancora_crm.chatbot_contacts c
    JOIN (
        SELECT contact_id, MAX(created_at) as max_created_at
        FROM ancora_crm.chatbot_conversations
        WHERE instance_id = $1
        GROUP BY contact_id
    ) latest ON c.id = latest.contact_id
    WHERE c.instance_id = $1
    ORDER BY latest.max_created_at DESC
    LIMIT 10
    """
    recent_contacts = await db.fetch(query, instance_id)
    return [dict(c) for c in recent_contacts]

# --- Public info (no auth required) ---
@router.get("/dashboard/{instance_id}/public-info")
async def get_public_info(instance_id: int = Depends(get_instance), db=Depends(get_db)):
    """Return minimal public info (business name) for the login page - no auth required."""
    info = await db.fetchrow(
        "SELECT business_name FROM ancora_crm.chatbot_business_info WHERE instance_id = $1",
        instance_id
    )
    return {"business_name": info["business_name"] if info else ""}


# --- Plugins ---
@router.get("/dashboard/{instance_id}/plugins")
async def get_plugins(instance_id: int = Depends(get_instance), db=Depends(get_db), user=Depends(get_current_chatbot_user)):
    """List all available plugins with their enabled/disabled status for this instance."""
    from app.plugins import PluginRegistry
    all_plugins = PluginRegistry.get_plugin_info()
    enabled_rows = await db.fetch(
        "SELECT plugin_id, config FROM ancora_crm.instance_plugins WHERE instance_id = $1 AND enabled = true",
        instance_id,
    )
    enabled_ids = {r["plugin_id"] for r in enabled_rows}
    
    result = []
    for p in all_plugins:
        p["enabled"] = p["id"] in enabled_ids
        # Get frontend routes for enabled plugins
        plugin_obj = PluginRegistry.get(p["id"])
        if plugin_obj:
            p["routes"] = plugin_obj.get_frontend_routes()
        result.append(p)
    
    return {"plugins": result, "enabled": list(enabled_ids)}


@router.post("/dashboard/{instance_id}/plugins/{plugin_id}/toggle")
async def toggle_plugin(
    plugin_id: str,
    instance_id: int = Depends(get_instance),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    """Enable or disable a plugin for this instance."""
    from app.plugins import PluginRegistry
    
    plugin = PluginRegistry.get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' no existe")
    
    # Check dependencies
    for dep in plugin.dependencies:
        dep_enabled = await db.fetchrow(
            "SELECT 1 FROM ancora_crm.instance_plugins WHERE instance_id = $1 AND plugin_id = $2 AND enabled = true",
            instance_id, dep,
        )
        if not dep_enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Plugin '{plugin_id}' requiere que '{dep}' este habilitado primero",
            )
    
    # Check if already exists
    existing = await db.fetchrow(
        "SELECT id, enabled FROM ancora_crm.instance_plugins WHERE instance_id = $1 AND plugin_id = $2",
        instance_id, plugin_id,
    )
    
    if existing:
        new_state = not existing["enabled"]
        await db.execute(
            "UPDATE ancora_crm.instance_plugins SET enabled = $1 WHERE id = $2",
            new_state, existing["id"],
        )
    else:
        new_state = True
        await db.execute(
            "INSERT INTO ancora_crm.instance_plugins (instance_id, plugin_id, enabled) VALUES ($1, $2, $3)",
            instance_id, plugin_id, True,
        )
    
    # Run on_install when enabling for the first time
    if new_state and not existing:
        try:
            await plugin.on_install(db, instance_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Plugin install error: {e}")
    
    return {"plugin_id": plugin_id, "enabled": new_state}


# --- Prompt Config (Rich Prompt System) ---
@router.get("/dashboard/{instance_id}/prompt-config")
async def get_prompt_config(instance_id: int = Depends(get_instance), db=Depends(get_db), user=Depends(get_current_chatbot_user)):
    config = await db.fetchrow(
        "SELECT * FROM ancora_crm.chatbot_prompt_config WHERE instance_id = $1",
        instance_id
    )
    if not config:
        return {
            "instance_id": instance_id,
            "identity_name": "",
            "identity_company": "",
            "identity_tagline": "",
            "identity_tone": "profesional pero cercano",
            "business_context": "",
            "first_contact_behavior": "",
            "pricing_response": "",
            "off_topic_response": "",
            "custom_responses": [],
            "restrictions_max_chars": 1000,
            "restrictions_no_markdown": True,
            "restrictions_max_emojis": 2,
            "exists": False,
        }
    result = dict(config)
    result["exists"] = True
    # Convert custom_responses from JSON string if needed
    import json as _json
    if isinstance(result.get("custom_responses"), str):
        try:
            result["custom_responses"] = _json.loads(result["custom_responses"])
        except Exception:
            result["custom_responses"] = []
    return result


@router.put("/dashboard/{instance_id}/prompt-config")
async def update_prompt_config(
    config_data: PromptConfigUpdate,
    instance_id: int = Depends(get_instance),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    import json as _json

    update_data = config_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Convert custom_responses to JSON
    if "custom_responses" in update_data and update_data["custom_responses"] is not None:
        update_data["custom_responses"] = _json.dumps([cr.dict() if hasattr(cr, 'dict') else cr for cr in update_data["custom_responses"]])

    # Check if exists
    existing = await db.fetchrow(
        "SELECT id FROM ancora_crm.chatbot_prompt_config WHERE instance_id = $1",
        instance_id
    )

    if existing:
        set_parts = []
        values = [instance_id]
        for i, (key, val) in enumerate(update_data.items(), start=2):
            set_parts.append(f"{key} = ${i}")
            values.append(val)
        set_parts.append("updated_at = NOW()")
        
        query = f"UPDATE ancora_crm.chatbot_prompt_config SET {', '.join(set_parts)} WHERE instance_id = $1 RETURNING *"
        result = await db.fetchrow(query, *values)
    else:
        cols = ["instance_id"] + list(update_data.keys())
        placeholders = [f"${i+1}" for i in range(len(cols))]
        values = [instance_id] + list(update_data.values())
        
        query = f"INSERT INTO ancora_crm.chatbot_prompt_config ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING *"
        result = await db.fetchrow(query, *values)

    result_dict = dict(result)
    result_dict["exists"] = True
    if isinstance(result_dict.get("custom_responses"), str):
        try:
            result_dict["custom_responses"] = _json.loads(result_dict["custom_responses"])
        except Exception:
            result_dict["custom_responses"] = []
    return result_dict


@router.get("/dashboard/{instance_id}/prompt-preview")
async def preview_prompt(instance_id: int = Depends(get_instance), db=Depends(get_db), user=Depends(get_current_chatbot_user)):
    """Preview the generated system prompt for debugging."""
    from app.services.chatbot_engine import ChatbotEngine
    engine = await ChatbotEngine.create(instance_id, db)
    prompt = await engine.get_system_prompt()
    return {"prompt": prompt, "length": len(prompt)}
