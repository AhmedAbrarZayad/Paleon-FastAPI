"""
Content routes for guides, lessons, articles tracking
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.routers.routes_auth import get_current_user
from app.repositories import GuidesLessonsRepository, VisitedRepository, ReadRepository
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


# Request/Response Models
class CreateContentRequest(BaseModel):
    title: str
    description: str
    type: str  # "guide" or "deep_dive"


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
            author_id=current_user["user_id"]
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
