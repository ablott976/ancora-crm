from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.database import get_db

# Use a separate secret for the chatbot dashboard for better security
CHATBOT_SECRET_KEY = settings.secret_key + "-chatbot"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Placeholder URL, not used directly

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, CHATBOT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_chatbot_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, CHATBOT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        instance_id: int = payload.get("instance_id")
        if username is None or instance_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.fetchrow(
        "SELECT * FROM ancora_crm.chatbot_dashboard_users WHERE username = $1 AND instance_id = $2",
        username, instance_id
    )
    if user is None:
        raise credentials_exception
    return user
