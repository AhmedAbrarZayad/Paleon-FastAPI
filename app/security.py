from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import settings
import secrets
import logging

logger = logging.getLogger(__name__)

# ==================== PASSWORD HASHING ====================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

# ==================== JWT TOKEN ====================

class TokenData(BaseModel):
    """JWT token payload"""
    user_id: str  # UUID from Supabase
    email: str
    tier: str
    exp: datetime

def create_access_token(
    user_id: str,  # UUID string
    email: str,
    tier: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "user_id": user_id,
        "email": email,
        "tier": tier,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_access_token(token: str) -> Optional[TokenData]:
    """Verify JWT access token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("user_id")  # UUID string
        email: str = payload.get("email")
        tier: str = payload.get("tier")
        
        if user_id is None or email is None:
            return None
        
        return TokenData(
            user_id=user_id,
            email=email,
            tier=tier,
            exp=payload.get("exp")
        )
    
    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        return None

# ==================== API KEY ====================

def hash_api_key(key: str) -> str:
    """Hash an API key"""
    return pwd_context.hash(key)

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key"""
    return pwd_context.verify(plain_key, hashed_key)

def generate_api_key() -> str:
    """Generate a random API key"""
    return f"sk_{secrets.token_urlsafe(32)}"