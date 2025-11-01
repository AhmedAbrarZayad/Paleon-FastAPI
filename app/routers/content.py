"""
Content routes for guides, lessons, articles tracking
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from app.routers.routes_auth import get_current_user
from app.repositories import GuidesLessonsRepository, VisitedRepository, ReadRepository, GuidesLessonsExtraRepository, StorageRepository
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


# Request/Response Models
class CreateContentRequest(BaseModel):
    title: str
    description: str
    type: str  # "guide" or "deep_dive"
    image_url: Optional[str] = None
    duration: Optional[str] = None
    level: Optional[str] = None


class RecordVisitRequest(BaseModel):
    lesson_id: int


class RecordReadRequest(BaseModel):
    article_id: int

# ============= Guides & Lessons Endpoints =============

@router.post("/create")
async def create_guide_or_lesson(
    request: CreateContentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new guide or deep dive"""
    try:
        if request.type not in ["guide", "deep_dive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Type must be 'guide' or 'deep_dive'"
            )
        
        result = GuidesLessonsRepository.create_guide_or_lesson(
            title=request.title,
            description=request.description,
            content_type=request.type,
            author_id=current_user["user_id"],
            image_url=request.image_url,
            duration=request.duration,
            level=request.level
        )
        
        return {
            "success": True,
            "message": f"{request.type.capitalize()} created successfully",
            "data": result
        }
    
    except Exception as e:
        logger.error(f"Error creating content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create {request.type}"
        )


@router.put("/update/{content_id}")
async def update_guide_or_lesson(
    content_id: int,
    request: CreateContentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing guide or deep dive"""
    try:
        logger.info("=" * 50)
        logger.info("UPDATE GUIDE/LESSON REQUEST")
        logger.info(f"Content ID: {content_id}")
        logger.info(f"User ID: {current_user.get('user_id')}")
        logger.info(f"Title: {request.title}")
        logger.info(f"Type: {request.type}")
        logger.info(f"Level: {request.level}")
        logger.info(f"Duration: {request.duration}")
        logger.info("=" * 50)
        
        if request.type not in ["guide", "deep_dive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Type must be 'guide' or 'deep_dive'"
            )
        
        result = GuidesLessonsRepository.update_guide_or_lesson(
            content_id=content_id,
            title=request.title,
            description=request.description,
            content_type=request.type,
            image_url=request.image_url,
            duration=request.duration,
            level=request.level
        )
        
        if not result:
            logger.error(f"Content {content_id} not found or update failed")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found or update failed"
            )
        
        logger.info(f"Successfully updated content {content_id}")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "message": f"{request.type.capitalize()} updated successfully",
            "data": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"ERROR UPDATING CONTENT: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 50)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update {request.type}"
        )


@router.get("/all")
async def get_all_content():
    """Get all guides and lessons"""
    try:
        content = GuidesLessonsRepository.get_all_guides_and_lessons()
        return {
            "success": True,
            "data": content
        }
    
    except Exception as e:
        logger.error(f"Error fetching content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch content"
        )

@router.get("/guides")
async def get_guides():
    """Get all guides"""
    try:
        guides = GuidesLessonsRepository.get_by_type("guide")
        return {
            "success": True,
            "data": guides
        }
    
    except Exception as e:
        logger.error(f"Error fetching guides: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch guides"
        )


@router.get("/deep-dives")
async def get_deep_dives():
    """Get all deep dives"""
    try:
        deep_dives = GuidesLessonsRepository.get_by_type("deep_dive")
        return {
            "success": True,
            "data": deep_dives
        }
    
    except Exception as e:
        logger.error(f"Error fetching deep dives: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch deep dives"
        )


@router.delete("/delete/{content_id}")
async def delete_guide_or_lesson(
    content_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a guide or deep dive (Admin only)"""
    try:
        logger.info("=" * 50)
        logger.info("DELETE REQUEST RECEIVED")
        logger.info(f"Content ID: {content_id}")
        logger.info(f"User ID: {current_user.get('user_id')}")
        logger.info("=" * 50)
        
        from app.repositories import GuidesLessonsRepository
        
        # Delete the content
        logger.info(f"Attempting to delete content with ID: {content_id}")
        success = GuidesLessonsRepository.delete_guide_or_lesson(content_id)
        
        logger.info(f"Delete operation result: {success} (type: {type(success)})")
        
        if success:
            logger.info(f"Content {content_id} deleted successfully")
            logger.info("=" * 50)
            return {
                "success": True,
                "message": "Content deleted successfully"
            }
        else:
            logger.warning(f"Content {content_id} not found or already deleted")
            logger.info("=" * 50)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"DELETE ERROR: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 50)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete content: {str(e)}"
        )
    
# ============= Visit Tracking Endpoints =============

@router.post("/visit")
async def record_visit(
    request: RecordVisitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Record a visit to a guide/lesson"""
    try:
        VisitedRepository.record_visit(
            user_id=current_user["user_id"],
            lesson_id=request.lesson_id
        )
        
        return {
            "success": True,
            "message": "Visit recorded successfully"
        }
    
    except Exception as e:
        logger.error(f"Error recording visit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record visit"
        )


# ============= Read Tracking Endpoints =============

@router.post("/read")
async def record_read(
    request: RecordReadRequest,
    current_user: dict = Depends(get_current_user)
):
    """Record reading an article"""
    try:
        ReadRepository.record_read(
            user_id=current_user["user_id"],
            article_id=request.article_id
        )
        
        return {
            "success": True,
            "message": "Read recorded successfully"
        }
    
    except Exception as e:
        logger.error(f"Error recording read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record read"
        )


# ============= Image Upload Endpoints =============

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload an image to the lessons bucket"""
    try:
        logger.info("=" * 50)
        logger.info("IMAGE UPLOAD REQUEST RECEIVED")
        logger.info(f"Filename: {file.filename}")
        logger.info(f"Content-Type: {file.content_type}")
        logger.info(f"User ID: {current_user.get('user_id')}")
        logger.info("=" * 50)
        
        # Validate file type - handle None or empty content_type
        content_type = file.content_type
        logger.info(f"Content-Type value: '{content_type}' (type: {type(content_type)})")
        
        # Check both content_type and file extension
        file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
        logger.info(f"File extension: {file_extension}")
        
        valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        
        # Accept if content_type starts with 'image/' OR if extension is valid
        if content_type and not content_type.startswith('image/'):
            if file_extension not in valid_extensions:
                logger.error(f"Invalid file - content_type: {content_type}, extension: {file_extension}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File must be an image (got content_type: {content_type}, extension: {file_extension})"
                )
        elif not content_type or content_type == '':
            # If no content_type, rely on extension
            logger.warning(f"No content_type provided, checking extension: {file_extension}")
            if file_extension not in valid_extensions:
                logger.error(f"Invalid extension: {file_extension}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File must be an image (extension: {file_extension} not in {valid_extensions})"
                )
            # Set a default content_type based on extension
            content_type = f'image/{file_extension}' if file_extension != 'jpg' else 'image/jpeg'
            logger.info(f"Set default content_type to: {content_type}")
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"guides/{unique_filename}"
        logger.info(f"Generated path: {file_path}")
        
        # Read file data
        file_data = await file.read()
        file_size = len(file_data)
        logger.info(f"File size: {file_size} bytes ({file_size/1024:.2f} KB)")
        
        # Upload to storage
        logger.info(f"Attempting upload to bucket 'lessons' with path '{file_path}'")
        public_url = StorageRepository.upload_image(
            bucket_name="lessons",
            file_path=file_path,
            file_data=file_data,
            content_type=content_type
        )
        
        logger.info(f"Upload successful! URL: {public_url}")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "message": "Image uploaded successfully",
            "data": {
                "url": public_url,
                "filename": unique_filename
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"UPLOAD ERROR: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 50)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


# ============= Extra Images Endpoints =============

@router.post("/extra-image")
async def add_extra_image(
    guide_id: int = Form(...),
    image_url: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Add an extra image to a guide or deep dive"""
    try:
        result = GuidesLessonsExtraRepository.add_extra_image(
            guide_id=guide_id,
            image_url=image_url
        )
        
        return {
            "success": True,
            "message": "Extra image added successfully",
            "data": result
        }
    
    except Exception as e:
        logger.error(f"Error adding extra image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add extra image"
        )


@router.get("/extra-images/{guide_id}")
async def get_extra_images(guide_id: int):
    """Get all extra images for a guide or deep dive"""
    try:
        images = GuidesLessonsExtraRepository.get_extra_images(guide_id)
        return {
            "success": True,
            "data": images
        }
    
    except Exception as e:
        logger.error(f"Error fetching extra images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch extra images"
        )


@router.delete("/extra-image")
async def delete_extra_image(
    guide_id: int,
    image_url: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an extra image from a guide or deep dive"""
    try:
        success = GuidesLessonsExtraRepository.delete_extra_image(
            guide_id=guide_id,
            image_url=image_url
        )
        
        return {
            "success": success,
            "message": "Extra image deleted successfully" if success else "Failed to delete extra image"
        }
    
    except Exception as e:
        logger.error(f"Error deleting extra image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete extra image"
        )
