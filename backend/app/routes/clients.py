from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
import secrets
from app.database import get_db
from app.models.domain import Client, ClientCreate, ClientUpdate, ClientService, ClientServiceCreate, ClientServiceCreateRequest, ClientServiceUpdate, ActivateChatbotRequest
from app.routes.auth import get_current_user
from app.services.chatbot_auth import get_password_hash

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("", response_model=List[Client])
async def get_clients(db = Depends(get_db)):
    rows = await db.fetch("SELECT * FROM ancora_crm.clients ORDER BY created_at DESC")
    return [dict(row) for row in rows]

@router.post("", response_model=Client)
async def create_client(client: ClientCreate, db = Depends(get_db)):
    query = """
    INSERT INTO ancora_crm.clients (name, slug, contact_name, contact_email, contact_phone, address, city, business_type, notes, status, dashboard_url, onboarding_date, offboarding_date)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    RETURNING *
    """
    try:
        row = await db.fetchrow(query, client.name, client.slug, client.contact_name, client.contact_email, client.contact_phone, client.address, client.city, client.business_type, client.notes, client.status, client.dashboard_url, client.onboarding_date, client.offboarding_date)
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/slug/{slug}")
async def get_client_by_slug(slug: str, db = Depends(get_db)):
    row = await db.fetchrow("SELECT * FROM ancora_crm.clients WHERE slug = $1", slug)
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return dict(row)

@router.get("/{client_id}", response_model=Client)
async def get_client(client_id: int, db = Depends(get_db)):
    row = await db.fetchrow("SELECT * FROM ancora_crm.clients WHERE id = $1", client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return dict(row)

@router.put("/{client_id}", response_model=Client)
async def update_client(client_id: int, client: ClientUpdate, db = Depends(get_db)):
    update_data = client.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    values = []
    for i, (key, value) in enumerate(update_data.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(value)
    
    values.append(client_id)
    query = f"""
    UPDATE ancora_crm.clients
    SET {', '.join(set_clauses)}, updated_at = NOW()
    WHERE id = ${len(values)}
    RETURNING *
    """
    row = await db.fetchrow(query, *values)
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return dict(row)

@router.delete("/{client_id}")
async def delete_client(client_id: int, db = Depends(get_db)):
    # Soft delete
    row = await db.fetchrow("UPDATE ancora_crm.clients SET status = 'inactive', updated_at = NOW() WHERE id = $1 RETURNING id", client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted (soft)"}

# --- Client Services ---
@router.get("/{client_id}/services", response_model=List[dict])
async def get_client_services(client_id: int, db = Depends(get_db)):
    query = """
    SELECT cs.*, sc.name as service_name, sc.category
    FROM ancora_crm.client_services cs
    JOIN ancora_crm.service_catalog sc ON cs.service_id = sc.id
    WHERE cs.client_id = $1
    ORDER BY cs.created_at DESC
    """
    rows = await db.fetch(query, client_id)
    return [dict(row) for row in rows]

@router.post("/{client_id}/services", response_model=ClientService)
async def add_client_service(client_id: int, service: ClientServiceCreateRequest, db = Depends(get_db)):
    query = """
    INSERT INTO ancora_crm.client_services (client_id, service_id, monthly_price, setup_price)
    VALUES ($1, $2, $3, $4)
    RETURNING *
    """
    try:
        row = await db.fetchrow(query, client_id, service.service_id, service.monthly_price, service.setup_price)
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{client_id}/services/activate-chatbot")
async def activate_chatbot(client_id: int, req: ActivateChatbotRequest, request: Request, db = Depends(get_db)):
    try:
        # Create the client_service record first
        service_cat = await db.fetchrow(
            "SELECT * FROM ancora_crm.service_catalog WHERE id = $1", req.service_id
        )
        if not service_cat:
            raise HTTPException(status_code=404, detail="Service not found in catalog")
        await db.execute(
            """INSERT INTO ancora_crm.client_services (client_id, service_id, monthly_price, setup_price)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (client_id, service_id) DO NOTHING""",
            client_id, req.service_id,
            service_cat['default_monthly_price'] or 0,
            service_cat['default_setup_price'] or 0
        )
        # Create chatbot instance (uses service_type, is_active - actual DB columns)
        instance = await db.fetchrow(
            """INSERT INTO ancora_crm.chatbot_instances (client_id, service_type, phone_number_id, display_phone_number, whatsapp_access_token, is_active)
            VALUES ($1, $2, $3, $4, $5, true) RETURNING *""",
            client_id, 'whatsapp_basic', req.phone_number_id, req.display_phone_number, req.whatsapp_access_token
        )
        instance_id = instance['id']
        # chatbot_business_info - no system_prompt column, uses description instead
        await db.execute(
            """INSERT INTO ancora_crm.chatbot_business_info (instance_id, business_name, business_type, address, city, description)
            VALUES ($1, $2, $3, $4, $5, $6)""",
            instance_id, req.business_name, req.business_type, req.address, req.city, req.system_prompt
        )
        # chatbot_prompts - uses filename + content (no prompt_type/is_active columns)
        await db.execute(
            """INSERT INTO ancora_crm.chatbot_prompts (instance_id, filename, content)
            VALUES ($1, 'system.txt', $2)""",
            instance_id, req.system_prompt
        )
        # Create dashboard user for the client
        dashboard_password = secrets.token_urlsafe(12)
        await db.execute(
            """INSERT INTO ancora_crm.chatbot_dashboard_users (instance_id, username, password_hash, role)
            VALUES ($1, $2, $3, 'admin')""",
            instance_id, req.business_name.lower().replace(' ', '_'),
            get_password_hash(dashboard_password)
        )
        # Generate dashboard URL and update client
        base_url = str(request.base_url).rstrip('/')
        dashboard_url = f"{base_url}/chatbot/{instance_id}"
        await db.execute(
            "UPDATE ancora_crm.clients SET dashboard_url = $1, updated_at = NOW() WHERE id = $2",
            dashboard_url, client_id
        )
        result = dict(instance)
        result['dashboard_url'] = dashboard_url
        result['dashboard_username'] = req.business_name.lower().replace(' ', '_')
        result['dashboard_password'] = dashboard_password
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{client_id}/services/{service_id}", response_model=ClientService)
async def update_client_service(client_id: int, service_id: int, service: ClientServiceUpdate, db = Depends(get_db)):
    update_data = service.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    values = []
    for i, (key, value) in enumerate(update_data.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(value)
    
    values.extend([client_id, service_id])
    query = f"""
    UPDATE ancora_crm.client_services
    SET {', '.join(set_clauses)}
    WHERE client_id = ${len(values)-1} AND service_id = ${len(values)}
    RETURNING *
    """
    row = await db.fetchrow(query, *values)
    if not row:
        raise HTTPException(status_code=404, detail="Client service not found")
    return dict(row)

@router.delete("/{client_id}/services/{service_id}")
async def remove_client_service(client_id: int, service_id: int, db = Depends(get_db)):
    # First, clean up any chatbot data linked to this client
    # (chatbot_prompts and chatbot_business_info reference chatbot_instances.id)
    instance = await db.fetchrow(
        "SELECT id FROM ancora_crm.chatbot_instances WHERE client_id = $1", client_id
    )
    if instance:
        inst_id = instance["id"]
        await db.execute("DELETE FROM ancora_crm.chatbot_prompts WHERE instance_id = $1", inst_id)
        await db.execute("DELETE FROM ancora_crm.chatbot_business_info WHERE instance_id = $1", inst_id)
        await db.execute("DELETE FROM ancora_crm.chatbot_dashboard_users WHERE instance_id = $1", inst_id)
        await db.execute("DELETE FROM ancora_crm.chatbot_instances WHERE id = $1", inst_id)
    # Then remove the client_service itself
    row = await db.fetchrow("DELETE FROM ancora_crm.client_services WHERE client_id = $1 AND service_id = $2 RETURNING id", client_id, service_id)
    if not row:
        raise HTTPException(status_code=404, detail="Client service not found")
    return {"message": "Client service and associated chatbot data removed"}
