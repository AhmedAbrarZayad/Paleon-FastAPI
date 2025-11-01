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


class GuidesLessonsRepository:
    """Guides and Lessons repository for Supabase"""
    
    @staticmethod
    def create_guide_or_lesson(
        title: str, 
        description: str, 
        content_type: str, 
        author_id: str,
        image_url: str = None,
        duration: str = None,
        level: str = None
    ) -> Dict:
        """Create a new guide or lesson (Deep Dive)"""
        try:
            data = {
                "title": title,
                "description": description,
                "type": content_type,  # "guide" or "deep_dive"
                "authorid": author_id,
                "image_url": image_url,
                "duration": duration,
                "level": level,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = supabase.table("guides&lessons").insert(data).execute()
            
            if response.data:
                logger.info(f"Created {content_type}: {title}")
                return response.data[0]
            else:
                raise Exception(f"Failed to create {content_type}")
        
        except Exception as e:
            logger.error(f"Error creating guide/lesson: {e}")
            raise
    
    @staticmethod
    def update_guide_or_lesson(
        content_id: int,
        title: str, 
        description: str, 
        content_type: str,
        image_url: str = None,
        duration: str = None,
        level: str = None
    ) -> Dict:
        """Update an existing guide or lesson (Deep Dive)"""
        try:
            logger.info(f"[REPO] Updating guide/lesson with ID: {content_id}")
            
            data = {
                "title": title,
                "description": description,
                "type": content_type,
                "image_url": image_url,
                "duration": duration,
                "level": level
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            logger.info(f"[REPO] Update data: {data}")
            
            response = supabase.table("guides&lessons").update(data).eq("id", content_id).execute()
            
            logger.info(f"[REPO] Update response: {response}")
            logger.info(f"[REPO] Response data: {response.data}")
            
            if response.data and len(response.data) > 0:
                logger.info(f"[REPO] Successfully updated content {content_id}")
                return response.data[0]
            else:
                logger.warning(f"[REPO] No rows updated for ID {content_id} - item may not exist")
                return None
        
        except Exception as e:
            logger.error(f"[REPO] Error updating guide/lesson: {e}")
            import traceback
            logger.error(f"[REPO] Traceback:\n{traceback.format_exc()}")
            raise
    
    @staticmethod
    def get_all_guides_and_lessons() -> list:
        """Get all guides and lessons"""
        try:
            response = supabase.table("guides&lessons").select("*").order("created_at", desc=True).execute()
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Error fetching guides and lessons: {e}")
            return []
    
    @staticmethod
    def get_by_type(content_type: str) -> list:
        """Get guides or lessons by type"""
        try:
            response = supabase.table("guides&lessons").select("*").eq("type", content_type).order("created_at", desc=True).execute()
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Error fetching {content_type}s: {e}")
            return []
    
    @staticmethod
    def delete_guide_or_lesson(content_id: int) -> bool:
        """Delete a guide or lesson"""
        try:
            logger.info(f"[REPO] Deleting guide/lesson with ID: {content_id}")
            response = supabase.table("guides&lessons").delete().eq("id", content_id).execute()
            
            logger.info(f"[REPO] Delete response: {response}")
            logger.info(f"[REPO] Response data: {response.data}")
            logger.info(f"[REPO] Response data type: {type(response.data)}")
            logger.info(f"[REPO] Response data length: {len(response.data) if response.data else 0}")
            
            # Check if any rows were deleted
            if response.data and len(response.data) > 0:
                logger.info(f"[REPO] Successfully deleted {len(response.data)} row(s)")
                return True
            else:
                logger.warning(f"[REPO] No rows deleted for ID {content_id} - item may not exist")
                return False
        
        except Exception as e:
            logger.error(f"[REPO] Error deleting guide/lesson: {e}")
            import traceback
            logger.error(f"[REPO] Traceback:\n{traceback.format_exc()}")
            return False


class VisitedRepository:
    """Track visited guides/lessons"""
    
    @staticmethod
    def record_visit(user_id: str, lesson_id: int):
        """Record or increment visit to a lesson/guide"""
        try:
            # Check if visit exists
            existing = supabase.table("visited").select("*").eq("userid", user_id).eq("lessonid", lesson_id).execute()
            
            if existing.data:
                # Increment times
                current_times = existing.data[0].get("times", 0)
                supabase.table("visited").update({
                    "times": current_times + 1
                }).eq("userid", user_id).eq("lessonid", lesson_id).execute()
                logger.info(f"Incremented visit count for user {user_id}, lesson {lesson_id}")
            else:
                # Create new visit record
                supabase.table("visited").insert({
                    "userid": user_id,
                    "lessonid": lesson_id,
                    "times": 1
                }).execute()
                logger.info(f"Recorded first visit for user {user_id}, lesson {lesson_id}")
            
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Error recording visit: {e}")
            raise


class ReadRepository:
    """Track read articles"""
    
    @staticmethod
    def record_read(user_id: str, article_id: int):
        """Record or increment article read"""
        try:
            # Check if read exists
            existing = supabase.table("read").select("*").eq("userid", user_id).eq("articleid", article_id).execute()
            
            if existing.data:
                # Increment times
                current_times = existing.data[0].get("times", 0)
                supabase.table("read").update({
                    "times": current_times + 1
                }).eq("userid", user_id).eq("articleid", article_id).execute()
                logger.info(f"Incremented read count for user {user_id}, article {article_id}")
            else:
                # Create new read record
                supabase.table("read").insert({
                    "userid": user_id,
                    "articleid": article_id,
                    "times": 1
                }).execute()
                logger.info(f"Recorded first read for user {user_id}, article {article_id}")
            
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Error recording read: {e}")
            raise


class FossilRepository:
    """Manage fossil discoveries"""
    
    @staticmethod
    def create_or_update_fossil(name: str, species: str = None, location: str = None, age: float = None, images: str = None) -> Dict:
        """Create a new fossil entry or return existing"""
        try:
            # Check if fossil with same name exists
            existing = supabase.table("fossils").select("*").eq("name", name).execute()
            
            if existing.data:
                logger.info(f"Fossil '{name}' already exists")
                return existing.data[0]
            
            # Create new fossil
            fossil_data = {
                "name": name,
                "species": species,
                "location": location,
                "age": age,
                "images": images
            }
            
            response = supabase.table("fossils").insert(fossil_data).execute()
            
            if response.data:
                logger.info(f"Created new fossil: {name}")
                return response.data[0]
            else:
                raise Exception("Failed to create fossil")
        
        except Exception as e:
            logger.error(f"Error creating fossil: {e}")
            raise
    
    @staticmethod
    def get_all_fossils() -> list:
        """Get all fossils from the fossils table"""
        try:
            logger.info("Fetching all fossils from database")
            response = supabase.table("fossils").select("*").execute()
            fossils = response.data if response.data else []
            logger.info(f"Retrieved {len(fossils)} fossils from database")
            return fossils
        
        except Exception as e:
            logger.error(f"Error fetching all fossils: {e}")
            return []


class FoundRepository:
    """Track user fossil discoveries"""
    
    @staticmethod
    def record_found(user_id: str, fossil_name: str):
        """Record or increment fossil discovery"""
        try:
            # Check if user has found this fossil before
            existing = supabase.table("found").select("*").eq("userid", user_id).eq("name", fossil_name).execute()
            
            if existing.data:
                # Increment times
                current_times = existing.data[0].get("times", 0)
                supabase.table("found").update({
                    "times": current_times + 1
                }).eq("userid", user_id).eq("name", fossil_name).execute()
                logger.info(f"User {user_id} found '{fossil_name}' again (total: {current_times + 1})")
            else:
                # Create new found record
                supabase.table("found").insert({
                    "userid": user_id,
                    "name": fossil_name,
                    "times": 1
                }).execute()
                logger.info(f"User {user_id} found '{fossil_name}' for the first time")
            
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Error recording found fossil: {e}")
            raise
    
    @staticmethod
    def get_user_fossils(user_id: str) -> list:
        """Get all fossils found by a user"""
        try:
            response = supabase.table("found").select("*").eq("userid", user_id).execute()
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Error fetching user fossils: {e}")
            return []
        


class GuidesLessonsExtraRepository:
    """Repository for managing extra images for guides and deep dives"""
    
    @staticmethod
    def add_extra_image(guide_id: int, image_url: str):
        """Add an extra image for a guide or deep dive"""
        try:
            data = {
                "guides_lessons_id": guide_id,
                "imageurl": image_url
            }
            
            response = supabase.table("guides&lessonsExtra").insert(data).execute()
            
            if response.data:
                logger.info(f"Added extra image for guide/dive {guide_id}")
                return response.data[0]
            else:
                raise Exception("Failed to add extra image")
        
        except Exception as e:
            logger.error(f"Error adding extra image: {e}")
            raise
    
    @staticmethod
    def get_extra_images(guide_id: int) -> list:
        """Get all extra images for a guide or deep dive"""
        try:
            response = supabase.table("guides&lessonsExtra").select("*").eq("guides_lessons_id", guide_id).execute()
            return response.data if response.data else []
        
        except Exception as e:
            logger.error(f"Error fetching extra images: {e}")
            return []
    
    @staticmethod
    def delete_extra_image(guide_id: int, image_url: str) -> bool:
        """Delete an extra image"""
        try:
            supabase.table("guides&lessonsExtra").delete().eq("guides_lessons_id", guide_id).eq("imageurl", image_url).execute()
            logger.info(f"Deleted extra image for guide/dive {guide_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting extra image: {e}")
            return False


class StorageRepository:
    """Repository for managing file uploads to Supabase Storage"""
    
    @staticmethod
    def upload_image(bucket_name: str, file_path: str, file_data: bytes, content_type: str = "image/jpeg") -> str:
        """Upload an image to Supabase storage and return the public URL"""
        try:
            # Upload file to storage
            response = supabase.storage.from_(bucket_name).upload(
                file_path,
                file_data,
                {"content-type": content_type}
            )
            
            # Get public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            
            logger.info(f"Uploaded image to {bucket_name}/{file_path}")
            return public_url
        
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise
    
    @staticmethod
    def delete_image(bucket_name: str, file_path: str) -> bool:
        """Delete an image from Supabase storage"""
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
            logger.info(f"Deleted image from {bucket_name}/{file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return False