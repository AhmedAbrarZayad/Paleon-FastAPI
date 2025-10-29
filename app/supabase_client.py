from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY
)

logger.info(f"Supabase client initialized: {settings.SUPABASE_URL}")

def get_supabase() -> Client:
    """Get Supabase client"""
    return supabase