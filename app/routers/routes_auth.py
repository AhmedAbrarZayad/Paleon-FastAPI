from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from app.models.schemas import APIKeyResponse, UserCreate, UserLogin, TokenResponse, UserResponse
from app.repositories import UserRepository, APIKeyRepository
from app.security import create_access_token, verify_access_token, TokenData
from app.config import settings
from app.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

security = HTTPBearer()

# ==================== REGISTER ====================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user (FREE tier by default)"""
    
    logger.info(f"Register request for email: {user_data.email}")
    
    # Check if email already exists
    if UserRepository.check_email_exists(user_data.email):
        logger.warning(f"Email already registered: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username exists
    if UserRepository.check_username_exists(user_data.username):
        logger.warning(f"Username already taken: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    try:
        # Create user
        user = UserRepository.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            tier="free"
        )
        
        # Create token
        access_token = create_access_token(
            user_id=user["user_id"],
            email=user["email"],
            tier=user["tier"]
        )
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse(**user)
        )
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

# ==================== LOGIN ====================

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user"""
    
    logger.info(f"Login request for email: {credentials.email}")
    
    try:
        # Verify credentials
        user = UserRepository.verify_user_password(
            email=credentials.email,
            password=credentials.password
        )
        
        if not user:
            logger.warning(f"Invalid credentials for: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Create token
        access_token = create_access_token(
            user_id=user["user_id"],
            email=user["email"],
            tier=user["tier"]
        )
        
        logger.info(f"User logged in: {credentials.email}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse(**user)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

# ==================== OAUTH SIGN-IN (GOOGLE, ETC.) ====================

@router.post("/oauth/signin", response_model=TokenResponse)
async def oauth_signin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Handle OAuth sign-in from Flutter frontend.
    
    Frontend flow:
    1. User clicks "Sign in with Google" in Flutter
    2. Supabase handles OAuth, returns access_token to Flutter
    3. Flutter sends access_token to this endpoint
    4. Backend verifies token, creates/updates profile, returns our JWT
    
    Headers:
        Authorization: Bearer <supabase_access_token>
    """
    
    supabase_token = credentials.credentials
    
    logger.info("OAuth sign-in request received")
    
    try:
        # Verify Supabase token and get user info
        user_response = supabase.auth.get_user(supabase_token)
        
        if not user_response or not user_response.user:
            logger.warning("Invalid Supabase token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Supabase token"
            )
        
        supabase_user = user_response.user
        user_id = supabase_user.id
        email = supabase_user.email
        
        # Get user metadata (name, avatar from Google)
        user_metadata = supabase_user.user_metadata or {}
        name = user_metadata.get("full_name") or user_metadata.get("name") or email.split("@")[0]
        avatar = user_metadata.get("avatar_url") or user_metadata.get("picture")
        
        logger.info(f"OAuth user verified: {email} (UUID: {user_id})")
        
        # Create or update profile in our database
        user_profile = UserRepository.create_or_update_profile_from_oauth(
            user_id=user_id,
            email=email,
            name=name,
            avatar=avatar,
            tier="free"
        )
        
        # Create our own JWT token
        access_token = create_access_token(
            user_id=user_profile["user_id"],
            email=user_profile["email"],
            tier=user_profile["tier"]
        )
        
        logger.info(f"OAuth sign-in successful: {email}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse(**user_profile)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth sign-in error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth sign-in failed"
        )

# ==================== GET CURRENT USER ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user from token"""
    
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify token
    token_data: TokenData = verify_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user from database
    user = UserRepository.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(**current_user)

# ==================== API KEYS ====================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new API key for user"""
    
    try:
        api_key = APIKeyRepository.create_api_key(
            user_id=current_user["user_id"],
            name=key_data.get("name", "API Key")
        )
        
        return APIKeyResponse(**api_key)
    
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

@router.get("/api-keys")
async def get_api_keys(current_user: dict = Depends(get_current_user)):
    """Get all API keys for current user"""
    
    try:
        api_keys = APIKeyRepository.get_api_keys(current_user["user_id"])
        
        return {
            "success": True,
            "api_keys": api_keys
        }
    
    except Exception as e:
        logger.error(f"Error getting API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys"
        )