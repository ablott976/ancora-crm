from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import date, datetime

class ClientBase(BaseModel):
    name: str
    slug: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    business_type: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = 'active'
    dashboard_url: Optional[str] = None
    onboarding_date: Optional[date] = None
    offboarding_date: Optional[date] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    slug: Optional[str] = None

class Client(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ServiceCatalogBase(BaseModel):
    name: str
    description: Optional[str] = None
    default_monthly_price: Optional[float] = None
    default_setup_price: Optional[float] = None
    category: Optional[str] = None
    is_active: Optional[bool] = True

class ServiceCatalogCreate(ServiceCatalogBase):
    pass

class ServiceCatalogUpdate(ServiceCatalogBase):
    name: Optional[str] = None

class ServiceCatalog(ServiceCatalogBase):
    id: int
    created_at: Optional[datetime] = None

class ClientServiceBase(BaseModel):
    client_id: int
    service_id: int
    monthly_price: Optional[float] = None
    setup_price: Optional[float] = None
    status: Optional[str] = 'active'
    started_at: Optional[date] = None
    ended_at: Optional[date] = None
    notes: Optional[str] = None

class ClientServiceCreate(ClientServiceBase):
    pass

class ClientServiceCreateRequest(BaseModel):
    service_id: int
    monthly_price: Optional[float] = None
    setup_price: Optional[float] = None

class ClientServiceUpdate(BaseModel):
    monthly_price: Optional[float] = None
    setup_price: Optional[float] = None
    status: Optional[str] = None
    started_at: Optional[date] = None
    ended_at: Optional[date] = None
    notes: Optional[str] = None

class ClientService(ClientServiceBase):
    id: int
    created_at: Optional[datetime] = None

class InvoiceBase(BaseModel):
    client_id: int
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = 'EUR'
    status: Optional[str] = 'pending'
    concept: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    ai_extracted_data: Optional[Dict[str, Any]] = None
    ai_confidence: Optional[float] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    concept: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None

class Invoice(InvoiceBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ActivateChatbotRequest(BaseModel):
    phone_number_id: str
    display_phone_number: str
    whatsapp_access_token: str
    business_name: str
    business_type: str = ""
    address: str = ""
    city: str = ""
    system_prompt: str = ""
    service_id: int

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
