from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from app.services.rag import SpecificationExtractor, ImageClassifier
from app.celery_task import classify_images_task
from app.celery_config import celery_app
from app.routers.routes_auth import router as auth_router, get_current_user
from app.routers.content import router as content_router
from app.routers.fossils_tracking import router as fossils_router
from app.rate_limit import TierRateLimiter
from app.repositories import ClassificationJobRepository
from app.config import settings
import json
import logging
from typing import List
import uuid
from datetime import datetime
import base64
import io
from PIL import Image
import redis

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ==================== REDIS CONNECTION ====================

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

# Test Redis connection
try:
    redis_client.ping()
    logger.info("[OK] Connected to Redis")
except Exception as e:
    logger.warning(f"Warning: Could not connect to Redis: {e}")

# Initialize rate limiter
rate_limiter = TierRateLimiter(redis_client)

# ==================== FASTAPI APP SETUP ====================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered fossil classification using RAG and GPT-4 Vision",
    version=settings.VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(fossils_router)

logger.info("=== Initializing RAG system on startup ===")

# Global variables (for fast endpoint)
_extractor = None
_classification_prompt = None
_output_format = None
_classifier = None

def get_classifier() -> ImageClassifier:
    """Get or create the image classifier (singleton pattern)."""
    global _extractor, _classification_prompt, _output_format, _classifier
    
    if _classifier is None:
        logger.info("First request - initializing RAG components...")
        
        _extractor = SpecificationExtractor()
        logger.info("[OK] Extractor initialized")
        
        logger.info("Extracting classification prompt from PDF...")
        _classification_prompt = _extractor.extract_classification_prompt()
        logger.info("[OK] Classification prompt extracted")
        
        logger.info("Extracting output format from PDF...")
        _output_format = _extractor.extract_output_format()
        logger.info("[OK] Output format extracted")
        
        _classifier = ImageClassifier(_classification_prompt, _output_format)
        logger.info("[OK] Classifier ready!")
    
    return _classifier

# ==================== SECURITY ====================

security = HTTPBearer()

# ==================== API ENDPOINTS ====================

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.post("/classify-async/")
async def classify_fossil_images_async(
    image_files: List[UploadFile] = File(
        ...,
        description="Upload 1-5 images of the fossil"
    ),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Classify fossil images ASYNCHRONOUSLY using Celery.
    
    **REQUIRES AUTHENTICATION** - Pass JWT token in Authorization header
    
    Args:
        image_files: List of image files (1-5 images)
        credentials: Bearer token from /auth/login
    
    Returns:
        Instant response with job_id
    
    Example Response:
    {
        "success": true,
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "processing",
        "message": "Classification started. Check /result/{job_id} to get results",
        "rate_limit": {
            "limit": 10,
            "current": 1,
            "remaining": 9,
            "reset_at": "2025-10-25T12:30:00"
        }
    }
    """
    
    request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{request_id}] ASYNC REQUEST - Received {len(image_files)} image(s)")
    
    try:
        # ===== AUTHENTICATE USER =====
        current_user = await get_current_user(credentials)
        logger.info(f"[{request_id}] User authenticated: {current_user['email']}")
        
        # ===== CHECK RATE LIMIT =====
        is_allowed, limit_info = rate_limiter.check_rate_limit(
            current_user["user_id"],  # UUID from Supabase
            current_user["tier"]
        )
        
        if not is_allowed:
            logger.warning(f"[{request_id}] Rate limit exceeded for {current_user['email']}")
            raise HTTPException(
                status_code=429,  # Too Many Requests
                detail=f"Rate limit exceeded. Limit: {limit_info['limit']} requests/day",
                headers={
                    "X-RateLimit-Limit": str(limit_info['limit']),
                    "X-RateLimit-Current": str(limit_info['current']),
                    "X-RateLimit-Remaining": str(limit_info['remaining']),
                    "X-RateLimit-Reset": limit_info.get('reset_at', '')
                }
            )
        
        # Validate number of images
        if len(image_files) == 0:
            logger.warning(f"[{request_id}] No images provided")
            raise HTTPException(status_code=400, detail="At least one image is required")
        
        if len(image_files) > 5:
            logger.warning(f"[{request_id}] Too many images: {len(image_files)}")
            raise HTTPException(status_code=400, detail="Maximum 5 images allowed")
        
        # ===== CONVERT IMAGES TO BASE64 =====
        logger.info(f"[{request_id}] Converting images to base64...")
        images_base64 = []
        
        for idx, upload_file in enumerate(image_files, 1):
            # Validate file type
            if not upload_file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {upload_file.filename} is not an image"
                )
            
            # Read file into memory
            image_bytes = await upload_file.read()
            
            # Validate image
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image {upload_file.filename}: {str(e)}"
                )
            
            # Encode to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            images_base64.append(image_base64)
            logger.info(f"[{request_id}] Image {idx}/{len(image_files)}: {upload_file.filename} converted")
        
        # ===== CREATE JOB IN DATABASE =====
        job_id = str(uuid.uuid4())
        try:
            ClassificationJobRepository.create_job(
                user_id=current_user["user_id"],  # UUID from Supabase
                job_id=job_id,
                image_count=len(image_files)
            )
            logger.info(f"[{request_id}] Job created in database: {job_id}")
        except Exception as e:
            logger.error(f"[{request_id}] Error creating job in database: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create classification job"
            )
        
        # ===== SEND TO CELERY =====
        logger.info(f"[{request_id}] Sending task to Celery worker...")
        task = classify_images_task.delay(
            images_base64=images_base64,
            request_id=request_id,
            job_id=job_id,
            user_id=current_user["user_id"]  # UUID from Supabase
        )
        
        logger.info(f"[{request_id}] Task queued with ID: {task.id}")
        
        # Return response
        return {
            "success": True,
            "job_id": job_id,
            "status": "processing",
            "message": f"Classification started. Check /result/{job_id} for status",
            "request_id": request_id,
            "rate_limit": limit_info
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[{request_id}] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )

@app.get("/result/{job_id}")
async def get_classification_result(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get classification result by job ID.
    
    **REQUIRES AUTHENTICATION**
    
    Args:
        job_id: Job ID returned from /classify-async/
        credentials: Bearer token
    
    Returns:
        - If pending: {"status": "pending"}
        - If processing: {"status": "processing"}
        - If complete: {"status": "complete", "result": {...}}
        - If failed: {"status": "failed", "error": "..."}
    """
    
    logger.info(f"Result check for job: {job_id}")
    
    try:
        # Authenticate user
        current_user = await get_current_user(credentials)
        
        # Get job from database
        job = ClassificationJobRepository.get_job(job_id)
        
        if not job:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )
        
        # Verify ownership
        if job["user_id"] != current_user["user_id"]:  # UUID from Supabase
            logger.warning(f"Unauthorized access to job {job_id} by user {current_user['user_id']}")
            raise HTTPException(
                status_code=403,
                detail="Unauthorized"
            )
        
        # Return result
        return {
            "status": job["status"],
            "job_id": job_id,
            "result": job.get("result"),
            "error": job.get("error_message"),
            "processing_time_ms": job.get("processing_time_ms"),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving result: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve result"
        )

@app.get("/jobs")
async def get_user_jobs(
    limit: int = 10,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get user's recent classification jobs.
    
    **REQUIRES AUTHENTICATION**
    """
    
    try:
        current_user = await get_current_user(credentials)
        
        jobs = ClassificationJobRepository.get_user_jobs(
            user_id=current_user["user_id"],  # UUID from Supabase
            limit=limit
        )
        
        return {
            "success": True,
            "jobs": jobs
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve jobs"
        )