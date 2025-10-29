"""
Celery tasks for background processing.

Tasks run asynchronously in separate worker processes.
"""

from app.celery_config import celery_app
import logging
from app.services.rag import ImageClassifier, SpecificationExtractor
import json
import base64
import io
from pathlib import Path
from PIL import Image
from app.repositories import ClassificationJobRepository
from time import time

logger = logging.getLogger(__name__)

# Initialize RAG components once at module load
logger.info("Initializing RAG components for Celery worker...")
_extractor = None
_classifier = None

def get_classifier():
    """Get or create classifier (singleton for Celery worker)."""
    global _extractor, _classifier
    
    if _classifier is None:
        logger.info("Initializing classifier in Celery worker...")
        _extractor = SpecificationExtractor()
        classification_prompt = _extractor.extract_classification_prompt()
        output_format = _extractor.extract_output_format()
        _classifier = ImageClassifier(classification_prompt, output_format)
        logger.info("Classifier ready in worker!")
    
    return _classifier

# UPDATE THE FUNCTION:
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def classify_images_task(
    self,
    images_base64: list,
    request_id: str,
    job_id: str,
    user_id: str  # UUID from Supabase
) -> dict:
    """
    Background task to classify images.
    
    Args:
        images_base64: List of base64-encoded images
        request_id: Request ID for logging
        job_id: Classification job ID from database
        user_id: User ID who submitted the request
    
    Returns:
        Classification result
    """
    
    start_time = time()
    
    try:
        logger.info(f"[{request_id}] CELERY TASK STARTED - {len(images_base64)} images")
        
        # Update job status to processing
        ClassificationJobRepository.update_job_result(job_id, "processing")
        
        # Get classifier
        classifier = get_classifier()
        
        # Decode base64 images to temporary files
        image_paths = []
        temp_dir = Path("temp_images")
        temp_dir.mkdir(exist_ok=True)
        
        for idx, image_base64 in enumerate(images_base64, 1):
            try:
                # Decode from base64
                image_bytes = base64.b64decode(image_base64)
                
                # Validate image
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
                
                # Save temporarily
                temp_path = temp_dir / f"{request_id}_{idx}.jpg"
                with open(temp_path, "wb") as f:
                    f.write(image_bytes)
                
                image_paths.append(str(temp_path))
                logger.info(f"[{request_id}] Decoded image {idx}/{len(images_base64)}")
                
            except Exception as e:
                logger.error(f"[{request_id}] Error processing image {idx}: {e}")
                raise
        
        logger.info(f"[{request_id}] Sending to GPT-4 Vision for classification...")
        
        # Classify images
        result = classifier.classify_image(image_paths)
        
        # Cleanup temp images
        for path in image_paths:
            try:
                Path(path).unlink()
                logger.info(f"[{request_id}] Cleaned up {path}")
            except:
                pass
        
        # Calculate processing time
        processing_time_ms = int((time() - start_time) * 1000)
        
        # Update job with result
        ClassificationJobRepository.update_job_result(
            job_id,
            "complete",
            result=result,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"[{request_id}] Classification complete! ({processing_time_ms}ms)")
        
        return {
            "success": True,
            "job_id": job_id,
            "classification": result,
            "request_id": request_id,
            "processing_time_ms": processing_time_ms
        }
    
    except Exception as exc:
        logger.error(f"[{request_id}] Task failed: {str(exc)}", exc_info=True)
        
        # Update job with error
        processing_time_ms = int((time() - start_time) * 1000)
        ClassificationJobRepository.update_job_result(
            job_id,
            "failed",
            error=str(exc),
            processing_time_ms=processing_time_ms
        )
        
        # Retry
        raise self.retry(exc=exc)