from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.config import settings
from app.models.domain import Token, LoginRequest
from datetime import datetime, timedelta
import jwt

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None or username != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    access_token = create_access_token(data={"sub": "admin"})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login-json", response_model=Token)
async def login_json(req: LoginRequest):
    if req.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    access_token = create_access_token(data={"sub": "admin"})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
