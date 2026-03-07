from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database import get_db
from app.models.domain import Client, ClientCreate, ClientUpdate, ClientService, ClientServiceCreate, ClientServiceUpdate
from app.routes.auth import get_current_user

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
async def add_client_service(client_id: int, service: ClientServiceCreate, db = Depends(get_db)):
    if service.client_id != client_id:
        raise HTTPException(status_code=400, detail="Client ID mismatch")
    
    query = """
    INSERT INTO ancora_crm.client_services (client_id, service_id, monthly_price, setup_price, status, started_at, ended_at, notes)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING *
    """
    try:
        row = await db.fetchrow(query, client_id, service.service_id, service.monthly_price, service.setup_price, service.status, service.started_at, service.ended_at, service.notes)
        return dict(row)
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
    row = await db.fetchrow("DELETE FROM ancora_crm.client_services WHERE client_id = $1 AND service_id = $2 RETURNING id", client_id, service_id)
    if not row:
        raise HTTPException(status_code=404, detail="Client service not found")
    return {"message": "Client service removed"}
