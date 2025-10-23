from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.services.rag import SpecificationExtractor, ImageClassifier
import json
import logging
from pathlib import Path
import shutil
from typing import List
import uuid
from datetime import datetime

# ==================== LOGGING SETUP ====================
"""
LOGGING LEVELS:
- DEBUG: Detailed information for diagnosing problems
- INFO: General informational messages
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical error messages

How to use:
logger.debug("Detailed debug info")
logger.info("General info")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error!")
"""

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),  # Save to file with UTF-8
        logging.StreamHandler()  # Also print to console
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

# ==================== FASTAPI APP SETUP ====================

app = FastAPI(
    title="Paleon Fossil Classification API",
    description="AI-powered fossil classification using RAG and GPT-4 Vision",
    version="1.0.0"
)

# CORS middleware - allows Flutter app to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== GLOBAL RAG INITIALIZATION ====================
"""
IMPORTANT OPTIMIZATION:
We initialize RAG components ONCE when server starts.
This is MUCH faster than creating them on every request!

Why?
- Loading vector database takes time
- Initializing OpenAI embeddings takes time
- This way, first request is slow, all others are fast
"""

logger.info("=== Initializing RAG system on startup ===")

# Global variables (initialized once)
_extractor = None
_classification_prompt = None
_output_format = None
_classifier = None

def get_classifier() -> ImageClassifier:
    """
    Get or create the image classifier (singleton pattern).
    
    This function ensures we only create the classifier ONCE,
    not on every request (which would be very slow).
    """
    global _extractor, _classification_prompt, _output_format, _classifier
    
    if _classifier is None:
        logger.info("First request - initializing RAG components...")
        
        # Initialize extractor
        _extractor = SpecificationExtractor()
        logger.info("[OK] Extractor initialized")
        
        # Extract specifications (this takes a few seconds)
        logger.info("Extracting classification prompt from PDF...")
        _classification_prompt = _extractor.extract_classification_prompt()
        logger.info("[OK] Classification prompt extracted")
        
        logger.info("Extracting output format from PDF...")
        _output_format = _extractor.extract_output_format()
        logger.info("[OK] Output format extracted")
        
        # Create classifier
        _classifier = ImageClassifier(_classification_prompt, _output_format)
        logger.info("[OK] Classifier ready!")
    
    return _classifier

# ==================== FILE HANDLING ====================

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def save_upload_file(upload_file: UploadFile) -> Path:
    """
    Save uploaded file to disk temporarily.
    
    Args:
        upload_file: File uploaded by user
    
    Returns:
        Path to saved file
    
    Why save to disk?
    - UploadFile is in memory
    - We need file path to encode to base64
    - Temporary storage is fine (we delete after classification)
    """
    # Generate unique filename to avoid conflicts
    file_extension = Path(upload_file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    logger.info(f"Saved file: {file_path}")
    return file_path

def cleanup_files(file_paths: List[Path]):
    """
    Delete temporary files after classification.
    
    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.error(f"❌ Error deleting file {file_path}: {e}")

# ==================== API ENDPOINTS ====================

@app.get("/")
async def read_root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Paleon Fossil Classification API",
        "version": "1.0.0"
    }

@app.post("/fossil-image/")
async def classify_fossil_images(
    image_files: List[UploadFile] = File(..., description="Upload 1-5 images of the fossil")
):
    """
    Classify fossil images using RAG-enhanced AI.
    
    Args:
        image_files: List of image files (1-5 images of the same fossil)
    
    Returns:
        JSON with classification results
    
    Example Response:
    {
        "success": true,
        "classification": {
            "fossil_name": "Megalodon Tooth",
            "confidence": "high",
            ...
        },
        "metadata": {
            "num_images": 3,
            "processing_time_ms": 2345.67
        }
    }
    """
    
    request_id = str(uuid.uuid4())[:8]  # Short ID for logging
    start_time = datetime.now()
    
    logger.info(f"[{request_id}] NEW REQUEST - Received {len(image_files)} image(s)")
    
    # Validate number of images
    if len(image_files) == 0:
        logger.warning(f"[{request_id}] No images provided")
        raise HTTPException(status_code=400, detail="At least one image is required")
    
    if len(image_files) > 5:
        logger.warning(f"[{request_id}] Too many images: {len(image_files)}")
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed")
    
    saved_file_paths = []
    
    try:
        # ==================== STEP 1: SAVE UPLOADED FILES ====================
        logger.info(f"[{request_id}] Saving uploaded files...")
        
        for idx, upload_file in enumerate(image_files, 1):
            # Validate file type
            if not upload_file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {upload_file.filename} is not an image"
                )
            
            # Save file
            file_path = save_upload_file(upload_file)
            saved_file_paths.append(file_path)
            logger.info(f"  [{request_id}] Image {idx}/{len(image_files)}: {upload_file.filename} saved")
        
        # ==================== STEP 2: GET CLASSIFIER ====================
        logger.info(f"[{request_id}] Getting classifier...")
        classifier = get_classifier()
        logger.info(f"  [{request_id}] Classifier ready")
        
        # ==================== STEP 3: CLASSIFY IMAGES ====================
        logger.info(f"[{request_id}] Classifying {len(saved_file_paths)} image(s)...")
        
        # Convert Path objects to strings for the classifier
        image_path_strings = [str(path) for path in saved_file_paths]
        
        # Classify!
        result = classifier.classify_image(image_path_strings)
        
        logger.info(f"  [{request_id}] Classification complete!")
        
        # ==================== STEP 4: CALCULATE METRICS ====================
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # ==================== STEP 5: PREPARE RESPONSE ====================
        response = {
            "success": True,
            "request_id": request_id,
            "classification": result,
            "metadata": {
                "num_images_analyzed": len(image_files),
                "processing_time_ms": round(processing_time_ms, 2),
                "timestamp": end_time.isoformat()
            }
        }
        
        logger.info(f"[{request_id}] SUCCESS - Processed in {processing_time_ms:.2f}ms")
        logger.debug(f"[{request_id}] Response: {json.dumps(response, indent=2)}")
        
        return response
    
    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise
    
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"[{request_id}] ERROR: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )
    
    finally:
        # ==================== CLEANUP ====================
        # Always delete temporary files, even if error occurred
        logger.info(f"[{request_id}] Cleaning up temporary files...")
        cleanup_files(saved_file_paths)
