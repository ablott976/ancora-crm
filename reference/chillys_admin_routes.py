"""
Admin API router — mounted at /api/admin/
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from services import admin_api, broadcasts, menus, cierres
from services.auth import (
    ALGORITHM,
    CurrentUser,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    invalidate_tokens,
    require_admin,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ===========================================================================
# Models
# ===========================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class MesaCreate(BaseModel):
    nombre: str
    sillas: int = 4
    zona: str = "interior"


class MesaUpdate(BaseModel):
    nombre: Optional[str] = None
    sillas: Optional[int] = None
    zona: Optional[str] = None
    activa: Optional[bool] = None


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class BroadcastCreate(BaseModel):
    tipo: str = "custom"
    titulo: str
    mensaje: str
    imagen_url: Optional[str] = None
    programado_para: Optional[str] = None
    audiencia: str = "todos"
    audiencia_tags: Optional[list[str]] = None


class BroadcastUpdate(BaseModel):
    titulo: Optional[str] = None
    mensaje: Optional[str] = None
    tipo: Optional[str] = None
    imagen_url: Optional[str] = None
    programado_para: Optional[str] = None
    audiencia: Optional[str] = None
    audiencia_tags: Optional[list[str]] = None


class ContactoCreate(BaseModel):
    telefono: str
    nombre: str = "Cliente"
    activo: bool = True
    tags: Optional[list[str]] = None
    notas: Optional[str] = None


class ContactoUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    estado: Optional[str] = None
    tags: Optional[list[str]] = None
    notas: Optional[str] = None


class ContactoTagsUpdate(BaseModel):
    tags: list[str]


class ReservationCreate(BaseModel):
    fecha: str
    hora: str
    personas: int
    telefono: str
    nombre: str
    observaciones: str = ""
    mesa_id: Optional[int] = None


class ReservationUpdate(BaseModel):
    fecha: Optional[str] = None
    hora: Optional[str] = None
    personas: Optional[int] = None
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    observaciones: Optional[str] = None
    id_mesa: Optional[int] = None


# ===========================================================================
# Auth — with brute-force protection
# ===========================================================================
import time as _time
_login_attempts: dict[str, list[float]] = {}
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW_SECS = 300  # 5 min


def _check_rate_limit(ip: str):
    now = _time.time()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW_SECS]
    _login_attempts[ip] = attempts
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 5 minutos.")


@router.post("/auth/login")
async def login(req: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = await admin_api.get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        _login_attempts.setdefault(client_ip, []).append(_time.time())
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await admin_api.update_last_login(user["id"])

    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "token_version": user["token_version"],
    }
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
        "must_change_password": user["must_change_pw"],
    }


@router.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, user: CurrentUser = Depends(get_current_user)):
    db_user = await admin_api.get_user_by_id(user.id)
    if not verify_password(req.old_password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Wrong current password")
    await admin_api.update_password(user.id, hash_password(req.new_password))
    return {"ok": True}


@router.post("/auth/refresh")
async def refresh_token(req: RefreshRequest):
    from jose import JWTError, jwt as jose_jwt
    from config import get_settings
    _settings = get_settings()
    try:
        payload = jose_jwt.decode(req.refresh_token, _settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await admin_api.get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "token_version": user["token_version"],
    }
    return {"access_token": create_access_token(token_data)}


@router.get("/auth/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return user


@router.post("/auth/logout")
async def logout(user: CurrentUser = Depends(get_current_user)):
    await invalidate_tokens(user.id)
    return {"ok": True}


# ===========================================================================
# Dashboard
# ===========================================================================
@router.get("/dashboard")
async def dashboard(user: CurrentUser = Depends(get_current_user)):
    return await admin_api.get_dashboard_stats()


# ===========================================================================
# Shift View (table map per shift)
# ===========================================================================
@router.get("/shift-view")
async def shift_view(
    fecha: date = Query(default=None),
    turno: str = Query(default="cenas"),
    user: CurrentUser = Depends(get_current_user),
):
    if not fecha:
        fecha = date.today()
    return await admin_api.get_shift_view(fecha, turno)


# ===========================================================================
# Reservations
# ===========================================================================
@router.get("/reservations")
async def list_reservations(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    return await admin_api.list_reservations(fecha_desde, fecha_hasta, estado, limit, offset)


# ===========================================================================
# Tables (Mesas)
# ===========================================================================
@router.get("/mesas")
async def list_mesas(user: CurrentUser = Depends(get_current_user)):
    return await admin_api.list_mesas()


@router.post("/mesas")
async def create_mesa(req: MesaCreate, user: CurrentUser = Depends(require_admin)):
    return await admin_api.create_mesa(req.nombre, req.sillas, req.zona)


@router.put("/mesas/{mesa_id}")
async def update_mesa(mesa_id: int, req: MesaUpdate, user: CurrentUser = Depends(require_admin)):
    return await admin_api.update_mesa(mesa_id, **req.model_dump(exclude_unset=True))


@router.delete("/mesas/{mesa_id}")
async def delete_mesa(mesa_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await admin_api.delete_mesa(mesa_id)
    if not ok:
        raise HTTPException(status_code=404)
    return {"ok": True}


# ===========================================================================
# Config
# ===========================================================================
@router.get("/config")
async def get_config(user: CurrentUser = Depends(get_current_user)):
    return await admin_api.get_config()


@router.put("/config")
async def update_config(body: dict, user: CurrentUser = Depends(require_admin)):
    return await admin_api.update_config(**body)


# ===========================================================================
# Users
# ===========================================================================
@router.get("/users")
async def list_users(user: CurrentUser = Depends(require_admin)):
    return await admin_api.list_users()


@router.post("/users")
async def create_user(req: UserCreate, user: CurrentUser = Depends(require_admin)):
    existing = await admin_api.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    pw_hash = hash_password(req.password)
    return await admin_api.create_user(req.username, pw_hash, req.role)


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, user: CurrentUser = Depends(require_admin)):
    kwargs: dict = {}
    if req.role is not None:
        kwargs["role"] = req.role
    if req.password is not None and req.password != "":
        kwargs["password_hash"] = hash_password(req.password)
    if not kwargs:
        raise HTTPException(status_code=400, detail="No changes provided")
    result = await admin_api.update_user(user_id, **kwargs)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, user: CurrentUser = Depends(require_admin)):
    target = await admin_api.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminarte a ti mismo")
    if target["role"] == "superadmin":
        raise HTTPException(status_code=403, detail="Cannot delete superadmin")
    ok = await admin_api.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


# ===========================================================================
# Prompts
# ===========================================================================
@router.get("/prompts")
async def list_prompts(user: CurrentUser = Depends(get_current_user)):
    return await admin_api.list_prompts()


@router.put("/prompts/{key}")
async def update_prompt(key: str, body: dict, user: CurrentUser = Depends(get_current_user)):
    content = body.get("content", "")
    return await admin_api.update_prompt(key, content, user.username)


# ===========================================================================
# Broadcasts (mensajes masivos)
# ===========================================================================
@router.get("/broadcasts")
async def list_broadcasts(
    estado: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    return await broadcasts.list_broadcasts(estado, limit, offset)


@router.get("/broadcasts/{broadcast_id}")
async def get_broadcast(broadcast_id: int, user: CurrentUser = Depends(get_current_user)):
    b = await broadcasts.get_broadcast(broadcast_id)
    if not b:
        raise HTTPException(status_code=404)
    return b


@router.post("/broadcasts")
async def create_broadcast(req: BroadcastCreate, user: CurrentUser = Depends(get_current_user)):
    return await broadcasts.create_broadcast(
        tipo=req.tipo,
        titulo=req.titulo,
        mensaje=req.mensaje,
        imagen_url=req.imagen_url,
        programado_para=req.programado_para,
        audiencia=req.audiencia,
        audiencia_tags=req.audiencia_tags,
        creado_por=user.username,
    )


@router.put("/broadcasts/{broadcast_id}")
async def update_broadcast(
    broadcast_id: int, req: BroadcastUpdate, user: CurrentUser = Depends(get_current_user),
):
    result = await broadcasts.update_broadcast(broadcast_id, **req.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Not found or already sent")
    return result


@router.post("/broadcasts/{broadcast_id}/send")
async def send_broadcast(broadcast_id: int, user: CurrentUser = Depends(get_current_user)):
    """Send a broadcast immediately."""
    result = await broadcasts.send_broadcast(broadcast_id)
    if not result.get("exito"):
        raise HTTPException(status_code=400, detail=result.get("mensaje"))
    return result


@router.delete("/broadcasts/{broadcast_id}")
async def delete_broadcast(broadcast_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await broadcasts.delete_broadcast(broadcast_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found or not in draft state")
    return {"ok": True}


# ===========================================================================
# Contactos
# ===========================================================================
@router.get("/contactos/stats")
async def contactos_stats(user: CurrentUser = Depends(get_current_user)):
    return await admin_api.get_contactos_stats()


@router.get("/contactos")
async def list_contactos(
    search: Optional[str] = None,
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
    activo: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return await admin_api.list_contactos(search, tags_list, activo, limit, offset)


@router.post("/contactos", status_code=status.HTTP_201_CREATED)
async def create_contacto(req: ContactoCreate, user: CurrentUser = Depends(get_current_user)):
    try:
        return await admin_api.create_contacto(
            telefono=req.telefono,
            nombre=req.nombre,
            activo=req.activo,
            tags=req.tags,
            notas=req.notas,
        )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Teléfono ya registrado")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/contactos/{contacto_id}")
async def update_contacto(
    contacto_id: int, req: ContactoUpdate, user: CurrentUser = Depends(get_current_user),
):
    result = await admin_api.update_contacto(contacto_id, **req.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return result


@router.delete("/contactos/{contacto_id}")
async def delete_contacto(contacto_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await admin_api.delete_contacto(contacto_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return {"ok": True}


@router.put("/contactos/{contacto_id}/tags")
async def update_contacto_tags(
    contacto_id: int, req: ContactoTagsUpdate, user: CurrentUser = Depends(get_current_user),
):
    result = await admin_api.update_contacto_tags(contacto_id, req.tags)
    if not result:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return result


# ===========================================================================
# Admin Reservation mutations (GET /reservations already exists above)
# ===========================================================================
@router.post("/reservations", status_code=status.HTTP_201_CREATED)
async def create_reservation(
    req: ReservationCreate, user: CurrentUser = Depends(get_current_user),
):
    try:
        return await admin_api.admin_create_reserva(
            fecha=req.fecha,
            hora=req.hora,
            personas=req.personas,
            telefono=req.telefono,
            nombre=req.nombre,
            observaciones=req.observaciones,
            mesa_id=req.mesa_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.put("/reservations/{reserva_id}")
async def update_reservation(
    reserva_id: int, req: ReservationUpdate, user: CurrentUser = Depends(get_current_user),
):
    result = await admin_api.admin_update_reserva(
        reserva_id, **req.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.post("/reservations/{reserva_id}/confirm")
async def confirm_reservation(reserva_id: int, user: CurrentUser = Depends(get_current_user)):
    result = await admin_api.admin_set_reserva_estado(reserva_id, "Confirmada")
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.post("/reservations/{reserva_id}/cancel")
async def cancel_reservation(reserva_id: int, user: CurrentUser = Depends(get_current_user)):
    result = await admin_api.admin_set_reserva_estado(reserva_id, "Cancelada")
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


@router.post("/reservations/{reserva_id}/noshow")
async def noshow_reservation(reserva_id: int, user: CurrentUser = Depends(get_current_user)):
    result = await admin_api.admin_set_reserva_estado(reserva_id, "No-show")
    if not result:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return result


# ===========================================================================
# Models for Menus & Cierres
# ===========================================================================
class OwnerPhoneCreate(BaseModel):
    telefono: str
    nombre: str
    activo: bool = True

class PlantillaCreate(BaseModel):
    tipo: str
    nombre: str
    precio: Optional[float] = None
    incluye: Optional[str] = None
    postres_default: Optional[list[str]] = []
    dias_semana: Optional[list[int]] = []
    activo: bool = True

class PlantillaUpdate(BaseModel):
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    precio: Optional[float] = None
    incluye: Optional[str] = None
    postres_default: Optional[list[str]] = None
    dias_semana: Optional[list[int]] = None
    activo: Optional[bool] = None

class MenuDiarioCreate(BaseModel):
    fecha: date
    plantilla_id: int
    primeros: list[str] = []
    segundos: list[str] = []
    postres: Optional[list[str]] = None
    extras: Optional[str] = None
    imagen_url: Optional[str] = None
    estado: str = "borrador"
    origen: str = "manual"
    rotatorio_id: Optional[int] = None

class MenuDiarioUpdate(BaseModel):
    fecha: Optional[date] = None
    plantilla_id: Optional[int] = None
    primeros: Optional[list[str]] = None
    segundos: Optional[list[str]] = None
    postres: Optional[list[str]] = None
    extras: Optional[str] = None
    imagen_url: Optional[str] = None
    estado: Optional[str] = None
    origen: Optional[str] = None
    rotatorio_id: Optional[int] = None

class RotatorioCreate(BaseModel):
    nombre: str
    plantilla_id: int
    ciclo: list[dict]
    activo: bool = True

class RotatorioUpdate(BaseModel):
    nombre: Optional[str] = None
    plantilla_id: Optional[int] = None
    ciclo: Optional[list[dict]] = None
    posicion_actual: Optional[int] = None
    activo: Optional[bool] = None

class CierreCreate(BaseModel):
    tipo: str
    recurrencia: str = "puntual"
    fecha: Optional[date] = None
    dia_semana: Optional[int] = None
    descripcion: Optional[str] = None
    activo: bool = True
    turno: str = "completo"

class CierreUpdate(BaseModel):
    tipo: Optional[str] = None
    recurrencia: Optional[str] = None
    fecha: Optional[date] = None
    dia_semana: Optional[int] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None
    turno: Optional[str] = None

# ===========================================================================
# Owner Phones
# ===========================================================================
@router.get("/owner-phones")
async def list_owner_phones(user: CurrentUser = Depends(require_admin)):
    return await menus.list_owner_phones()

@router.post("/owner-phones")
async def create_owner_phone(req: OwnerPhoneCreate, user: CurrentUser = Depends(require_admin)):
    return await menus.create_owner_phone(req.telefono, req.nombre, req.activo)

@router.delete("/owner-phones/{phone_id}")
async def delete_owner_phone(phone_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await menus.delete_owner_phone(phone_id)
    if not ok:
        raise HTTPException(status_code=404)
    return {"ok": True}

# ===========================================================================
# Menús
# ===========================================================================
@router.get("/menu-plantillas")
async def list_menu_plantillas(user: CurrentUser = Depends(get_current_user)):
    return await menus.list_plantillas()

@router.post("/menu-plantillas")
async def create_menu_plantilla(req: PlantillaCreate, user: CurrentUser = Depends(require_admin)):
    return await menus.create_plantilla(**req.model_dump())

@router.put("/menu-plantillas/{plantilla_id}")
async def update_menu_plantilla(plantilla_id: int, req: PlantillaUpdate, user: CurrentUser = Depends(require_admin)):
    res = await menus.update_plantilla(plantilla_id, **req.model_dump(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404)
    return res

@router.delete("/menu-plantillas/{plantilla_id}")
async def delete_menu_plantilla(plantilla_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await menus.delete_plantilla(plantilla_id)
    if not ok:
        raise HTTPException(status_code=404)
    return {"ok": True}


@router.get("/menu-diario")
async def list_menu_diario(
    fecha_desde: Optional[date] = None, 
    fecha_hasta: Optional[date] = None, 
    user: CurrentUser = Depends(get_current_user)
):
    return await menus.list_menu_diario(fecha_desde, fecha_hasta)

@router.post("/menu-diario")
async def create_menu_diario(req: MenuDiarioCreate, user: CurrentUser = Depends(get_current_user)):
    return await menus.create_menu_diario(**req.model_dump())

@router.put("/menu-diario/{menu_id}")
async def update_menu_diario(menu_id: int, req: MenuDiarioUpdate, user: CurrentUser = Depends(get_current_user)):
    res = await menus.update_menu_diario(menu_id, **req.model_dump(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404)
    return res

@router.delete("/menu-diario/{menu_id}")
async def delete_menu_diario(menu_id: int, user: CurrentUser = Depends(get_current_user)):
    ok = await menus.delete_menu_diario(menu_id)
    if not ok:
        raise HTTPException(status_code=404)
    return {"ok": True}

@router.get("/menu-diario/preview/{menu_id}")
async def preview_menu_diario(menu_id: int, user: CurrentUser = Depends(get_current_user)):
    return await menus.preview_menu(menu_id)


@router.get("/menu-rotatorio")
async def list_menu_rotatorio(user: CurrentUser = Depends(get_current_user)):
    return await menus.list_rotatorios()

@router.post("/menu-rotatorio")
async def create_menu_rotatorio(req: RotatorioCreate, user: CurrentUser = Depends(require_admin)):
    return await menus.create_rotatorio(**req.model_dump())

@router.put("/menu-rotatorio/{rotatorio_id}")
async def update_menu_rotatorio(rotatorio_id: int, req: RotatorioUpdate, user: CurrentUser = Depends(require_admin)):
    res = await menus.update_rotatorio(rotatorio_id, **req.model_dump(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404)
    return res

@router.delete("/menu-rotatorio/{rotatorio_id}")
async def delete_menu_rotatorio(rotatorio_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await menus.delete_rotatorio(rotatorio_id)
    if not ok:
        raise HTTPException(status_code=404)
    return {"ok": True}

@router.post("/menu-rotatorio/{rotatorio_id}/toggle")
async def toggle_menu_rotatorio(rotatorio_id: int, user: CurrentUser = Depends(require_admin)):
    res = await menus.toggle_rotatorio(rotatorio_id)
    if not res:
        raise HTTPException(status_code=404)
    return res

# ===========================================================================
# Cierres
# ===========================================================================
@router.get("/cierres")
async def list_cierres(mes: Optional[int] = None, año: Optional[int] = None, user: CurrentUser = Depends(get_current_user)):
    if mes and año:
        return await cierres.get_cierres_for_month(año, mes)
    return await cierres.list_cierres()

@router.post("/cierres")
async def create_cierre(req: CierreCreate, user: CurrentUser = Depends(require_admin)):
    return await cierres.create_cierre(**req.model_dump())

@router.put("/cierres/{cierre_id}")
async def update_cierre(cierre_id: int, req: CierreUpdate, user: CurrentUser = Depends(require_admin)):
    res = await cierres.update_cierre(cierre_id, **req.model_dump(exclude_unset=True))
    if not res:
        raise HTTPException(status_code=404)
    return res

@router.delete("/cierres/{cierre_id}")
async def delete_cierre(cierre_id: int, user: CurrentUser = Depends(require_admin)):
    ok = await cierres.delete_cierre(cierre_id)
    if not ok:
        raise HTTPException(status_code=404)
    return {"ok": True}
