"""
Fossil discovery tracking routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.routers.routes_auth import get_current_user
from app.repositories import FossilRepository, FoundRepository
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fossils", tags=["Fossils"])


# Request/Response Models
class CreateFossilRequest(BaseModel):
    name: str
    species: Optional[str] = None
    location: Optional[str] = None
    age: Optional[float] = None
    images: Optional[str] = None


class RecordFoundRequest(BaseModel):
    fossil_name: str


# ============= Fossil Management Endpoints =============

@router.post("/create")
async def create_fossil(
    request: CreateFossilRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create or get existing fossil entry"""
    try:
        fossil = FossilRepository.create_or_update_fossil(
            name=request.name,
            species=request.species,
            location=request.location,
            age=request.age,
            images=request.images
        )
        
        return {
            "success": True,
            "message": "Fossil processed successfully",
            "data": fossil
        }
    
    except Exception as e:
        logger.error(f"Error creating fossil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process fossil"
        )


# ============= User Discovery Tracking Endpoints =============

@router.post("/found")
async def record_fossil_found(
    request: RecordFoundRequest,
    current_user: dict = Depends(get_current_user)
):
    """Record that user found a fossil"""
    try:
        # First ensure fossil exists
        FossilRepository.create_or_update_fossil(name=request.fossil_name)
        
        # Then record the discovery
        FoundRepository.record_found(
            user_id=current_user["user_id"],
            fossil_name=request.fossil_name
        )
        
        return {
            "success": True,
            "message": "Fossil discovery recorded successfully"
        }
    
    except Exception as e:
        logger.error(f"Error recording found fossil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record fossil discovery"
        )


@router.get("/my-fossils")
async def get_user_fossils(current_user: dict = Depends(get_current_user)):
    """Get all fossils found by the current user"""
    try:
        fossils = FoundRepository.get_user_fossils(current_user["user_id"])
        
        return {
            "success": True,
            "data": fossils
        }
    
    except Exception as e:
        logger.error(f"Error fetching user fossils: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user fossils"
        )
