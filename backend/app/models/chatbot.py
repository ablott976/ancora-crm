from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class BusinessInfo(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    services_offered: Optional[str] = None
    additional_info: Optional[str] = None

class ChatUserCreate(BaseModel):
    username: str
    password: str

class ChatUser(BaseModel):
    id: int
    username: str
    role: str

class Prompt(BaseModel):
    id: int
    filename: str
    content: str
    updated_at: datetime

class ScheduleDay(BaseModel):
    dia_semana: int = Field(..., ge=0, le=6)
    hora_apertura: Optional[str] = None
    hora_cierre: Optional[str] = None
    abierto: bool

class ScheduleUpdate(BaseModel):
    schedule: List[ScheduleDay]

class HolidayCreate(BaseModel):
    fecha: date
    nombre: str

class Holiday(BaseModel):
    id: int
    fecha: date
    nombre: str

class Contact(BaseModel):
    id: int
    instance_id: int
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    first_seen: datetime
    last_seen: datetime

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class ConversationMessage(BaseModel):
    role: str
    message: str
    created_at: datetime

class ConversationDay(BaseModel):
    date: date
    messages: List[ConversationMessage]

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Rich Prompt Config Models ---
class CustomResponse(BaseModel):
    trigger: str
    response: str

class PromptConfigUpdate(BaseModel):
    identity_name: Optional[str] = None
    identity_company: Optional[str] = None
    identity_tagline: Optional[str] = None
    identity_tone: Optional[str] = None
    business_context: Optional[str] = None
    first_contact_behavior: Optional[str] = None
    pricing_response: Optional[str] = None
    off_topic_response: Optional[str] = None
    custom_responses: Optional[List[CustomResponse]] = None
    restrictions_max_chars: Optional[int] = None
    restrictions_no_markdown: Optional[bool] = None
    restrictions_max_emojis: Optional[int] = None
