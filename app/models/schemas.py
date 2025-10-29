from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# ==================== USER SCHEMAS ====================

class UserCreate(BaseModel):
    """Schema for creating a user"""
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Schema for user response"""
    user_id: str  # UUID from Supabase
    email: str
    name: str  # Username field in database
    tier: str
    created_at: str
    subscription_ends_at: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    type: Optional[str] = None
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ==================== API KEY SCHEMAS ====================

class APIKeyCreate(BaseModel):
    """Schema for creating an API key"""
    name: str

class APIKeyResponse(BaseModel):
    """Schema for API key response (with key only on creation)"""
    id: int  # Auto-increment int4
    user_id: str  # UUID
    name: str
    key: Optional[str] = None  # Only on creation
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class APIKeyPublicResponse(BaseModel):
    """Schema for API key response (without key)"""
    id: int  # Auto-increment int4
    name: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str]

# ==================== RATE LIMIT INFO ====================

class RateLimitInfo(BaseModel):
    """Rate limit information"""
    limit: int
    current: int
    remaining: int
    reset_at: str

# ==================== CLASSIFICATION JOB SCHEMAS ====================

class ClassificationJobResponse(BaseModel):
    """Classification job response"""
    job_id: str
    status: str
    image_count: int
    result: Optional[dict]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]
    processing_time_ms: Optional[int]
    
    class Config:
        from_attributes = True

class ClassificationAsyncResponse(BaseModel):
    """Async classification response"""
    success: bool
    job_id: str
    status: str
    message: str
    request_id: str
    rate_limit: RateLimitInfo