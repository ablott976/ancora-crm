from fastapi import APIRouter, Depends
from app.database import get_db
from app.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/stats")
async def get_dashboard_stats(db = Depends(get_db)):
    # Total Active Clients
    active_clients = await db.fetchval("SELECT COUNT(*) FROM ancora_crm.clients WHERE status = 'active'")
    
    # MRR (Sum of active monthly services)
    mrr = await db.fetchval("""
        SELECT SUM(monthly_price) 
        FROM ancora_crm.client_services 
        WHERE status = 'active'
    """)
    mrr = mrr or 0.0

    # Pending Invoices Count
    pending_invoices = await db.fetchval("SELECT COUNT(*) FROM ancora_crm.invoices WHERE status = 'pending'")
    
    # Total Revenue YTD (Paid invoices this year)
    ytd_revenue = await db.fetchval("""
        SELECT SUM(total_amount) 
        FROM ancora_crm.invoices 
        WHERE status = 'paid' AND extract(year from payment_date) = extract(year from current_date)
    """)
    ytd_revenue = ytd_revenue or 0.0

    return {
        "active_clients": active_clients,
        "mrr": mrr,
        "pending_invoices": pending_invoices,
        "ytd_revenue": ytd_revenue
    }
