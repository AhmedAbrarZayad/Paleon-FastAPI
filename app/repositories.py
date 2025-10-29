from celery import uuid
from app.supabase_client import supabase
from app.security import hash_password, verify_password, generate_api_key, hash_api_key
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class UserRepository:
    """User repository for Supabase"""
    
    @staticmethod
    def create_user(email: str, username: str, password: str, tier: str = "free") -> Dict:
        """Create a new user in Supabase Auth and user_profile table"""
        try:
            # Step 1: Create user in Supabase Auth
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if not auth_response.user:
                raise Exception("Failed to create user in Supabase Auth")
            
            user_id = auth_response.user.id  # Get UUID from Supabase Auth
            
            # Step 2: Create user profile with the same UUID
            user_profile_data = {
                "user_id": user_id,  # Use the UUID from Supabase Auth
                "email": email,
                "name": username,
                "hashed_password": hash_password(password),
                "tier": tier,
                "created_at": datetime.utcnow().isoformat(),
                "last_reset_date": datetime.utcnow().isoformat(),
                "bio": None,
                "avatar": None,
                "type": None,
                "subscription_ends_at": None
            }
            
            response = supabase.table("user_profile").insert(user_profile_data).execute()
            
            if response.data:
                logger.info(f"User created: {email} with UUID: {user_id}")
                return response.data[0]
            else:
                raise Exception("Failed to create user profile")
        
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    @staticmethod
    def create_or_update_profile_from_oauth(user_id: str, email: str, name: str = None, avatar: str = None, tier: str = "free") -> Dict:
        """
        Create or update user profile from OAuth sign-in (Google, etc.)
        
        This is called when a user signs in via OAuth from the frontend.
        The frontend sends the access_token, backend verifies it and extracts user_id.
        """
        try:
            # Check if profile already exists
            existing_user = UserRepository.get_user_by_id(user_id)
            
            if existing_user:
                # User already exists, just return their profile
                logger.info(f"OAuth user already exists: {email}")
                return existing_user
            
            # Create new profile for OAuth user
            user_profile_data = {
                "user_id": user_id,  # UUID from Supabase Auth
                "email": email,
                "name": name or email.split("@")[0],  # Use email username if no name
                "hashed_password": None,  # OAuth users don't have passwords
                "tier": tier,
                "created_at": datetime.utcnow().isoformat(),
                "last_reset_date": datetime.utcnow().isoformat(),
                "bio": None,
                "avatar": avatar,  # Google profile picture
                "type": "oauth",  # Mark as OAuth user
                "subscription_ends_at": None
            }
            
            response = supabase.table("user_profile").insert(user_profile_data).execute()
            
            if response.data:
                logger.info(f"OAuth user profile created: {email} with UUID: {user_id}")
                return response.data[0]
            else:
                raise Exception("Failed to create OAuth user profile")
        
        except Exception as e:
            logger.error(f"Error creating/updating OAuth profile: {e}")
            raise
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            response = supabase.table("user_profile").select("*").eq("email", email).execute()
            
            if response.data:
                return response.data[0]
            return None
        
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        """Get user by UUID"""
        try:
            response = supabase.table("user_profile").select("*").eq("user_id", user_id).execute()
            
            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    
    @staticmethod
    def verify_user_password(email: str, password: str) -> Optional[Dict]:
        """Verify user password and return user if valid"""
        try:
            user = UserRepository.get_user_by_email(email)
            
            if not user:
                return None
            
            if not verify_password(password, user["hashed_password"]):
                return None
            
            return user
        
        except Exception as e:
            logger.error(f"Error verifying user password: {e}")
            return None
    
    @staticmethod
    def check_username_exists(username: str) -> bool:
        """Check if username exists"""
        try:
            response = supabase.table("user_profile").select("user_id").eq("name", username).execute()
            return len(response.data) > 0
        
        except Exception as e:
            logger.error(f"Error checking username: {e}")
            return False
    
    @staticmethod
    def check_email_exists(email: str) -> bool:
        """Check if email exists"""
        try:
            response = supabase.table("user_profile").select("user_id").eq("email", email).execute()
            return len(response.data) > 0
        
        except Exception as e:
            logger.error(f"Error checking email: {e}")
            return False


class APIKeyRepository:
    """API Key repository for Supabase"""
    
    @staticmethod
    def create_api_key(user_id: str, name: str) -> Dict:
        """Create a new API key"""
        try:
            plain_key = generate_api_key()
            hashed_key = hash_api_key(plain_key)
            
            api_key_data = {
                "user_id": user_id,
                "key": hashed_key,
                "name": name,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "last_used_at": None
            }
            
            response = supabase.table("api_keys").insert(api_key_data).execute()
            
            if response.data:
                # Return the plain key only once!
                result = response.data[0].copy()
                result["key"] = plain_key  # Only return plain key on creation
                logger.info(f"API key created for user {user_id}: {name}")
                return result
            else:
                raise Exception("Failed to create API key")
        
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            raise
    
    @staticmethod
    def get_api_keys(user_id: str) -> list:
        """Get all API keys for a user (without showing the key itself)"""
        try:
            response = supabase.table("api_keys").select(
                "id, user_id, name, is_active, created_at, last_used_at"
            ).eq("user_id", user_id).eq("is_active", True).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Error getting API keys: {e}")
            return []
    
    @staticmethod
    def verify_api_key(plain_key: str) -> Optional[Dict]:
        """Verify API key and return user info"""
        try:
            # Get all hashed keys
            response = supabase.table("api_keys").select(
                "id, user_id, key, is_active"
            ).eq("is_active", True).execute()
            
            if not response.data:
                return None
            
            # Find matching key
            from app.security import verify_api_key
            for api_key_record in response.data:
                if verify_api_key(plain_key, api_key_record["key"]):
                    # Update last used
                    supabase.table("api_keys").update({
                        "last_used_at": datetime.utcnow().isoformat()
                    }).eq("id", api_key_record["id"]).execute()
                    
                    # Get user info
                    user = UserRepository.get_user_by_id(api_key_record["user_id"])
                    return user
            
            return None
        
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None


class ClassificationJobRepository:
    """Classification job repository for Supabase"""
    
    @staticmethod
    def create_job(user_id: str, job_id: str, image_count: int) -> Dict:
        """Create a new classification job"""
        try:
            job_data = {
                "user_id": user_id,
                "job_id": job_id,
                "status": "pending",
                "image_count": image_count,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = supabase.table("classification_jobs").insert(job_data).execute()
            
            if response.data:
                logger.info(f"Job created: {job_id} for user {user_id}")
                return response.data[0]
            else:
                raise Exception("Failed to create job")
        
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise
    
    @staticmethod
    def update_job_result(job_id: str, status: str, result: Dict = None, error: str = None, processing_time_ms: int = None):
        """Update job with result"""
        try:
            update_data = {
                "status": status,
                "completed_at": datetime.utcnow().isoformat() if status == "complete" else None
            }
            
            if result:
                update_data["result"] = result
            
            if error:
                update_data["error_message"] = error
            
            if processing_time_ms:
                update_data["processing_time_ms"] = processing_time_ms
            
            response = supabase.table("classification_jobs").update(
                update_data
            ).eq("job_id", job_id).execute()
            
            logger.info(f"Job updated: {job_id} → {status}")
            return response.data[0] if response.data else None
        
        except Exception as e:
            logger.error(f"Error updating job: {e}")
            raise
    
    @staticmethod
    def get_job(job_id: str) -> Optional[Dict]:
        """Get job by ID"""
        try:
            response = supabase.table("classification_jobs").select("*").eq("job_id", job_id).execute()
            
            if response.data:
                return response.data[0]
            return None
        
        except Exception as e:
            logger.error(f"Error getting job: {e}")
            return None
    
    @staticmethod
    def get_user_jobs(user_id: str, limit: int = 10) -> list:
        """Get user's recent jobs"""
        try:
            response = supabase.table("classification_jobs").select("*").eq(
                "user_id", user_id
            ).order("created_at", desc=True).limit(limit).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Error getting user jobs: {e}")
            return []