from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database import get_db
from app.models.domain import ServiceCatalog, ServiceCatalogCreate, ServiceCatalogUpdate
from app.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("", response_model=List[ServiceCatalog])
async def get_services(db = Depends(get_db)):
    rows = await db.fetch("SELECT * FROM ancora_crm.service_catalog ORDER BY id ASC")
    return [dict(row) for row in rows]

@router.post("", response_model=ServiceCatalog)
async def create_service(service: ServiceCatalogCreate, db = Depends(get_db)):
    query = """
    INSERT INTO ancora_crm.service_catalog (name, description, default_monthly_price, default_setup_price, category, is_active)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING *
    """
    try:
        row = await db.fetchrow(query, service.name, service.description, service.default_monthly_price, service.default_setup_price, service.category, service.is_active)
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{service_id}", response_model=ServiceCatalog)
async def update_service(service_id: int, service: ServiceCatalogUpdate, db = Depends(get_db)):
    update_data = service.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    values = []
    for i, (key, value) in enumerate(update_data.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(value)
    
    values.append(service_id)
    query = f"""
    UPDATE ancora_crm.service_catalog
    SET {', '.join(set_clauses)}
    WHERE id = ${len(values)}
    RETURNING *
    """
    row = await db.fetchrow(query, *values)
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")
    return dict(row)

@router.delete("/{service_id}")
async def delete_service(service_id: int, db = Depends(get_db)):
    # Delete or soft delete? Let's just set is_active = false
    row = await db.fetchrow("UPDATE ancora_crm.service_catalog SET is_active = false WHERE id = $1 RETURNING id", service_id)
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deactivated"}
