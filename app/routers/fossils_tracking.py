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
        logger.info("=" * 50)
        logger.info("RECORD FOSSIL FOUND REQUEST")
        logger.info(f"User ID: {current_user.get('user_id')}")
        logger.info(f"Fossil Name: {request.fossil_name}")
        logger.info("=" * 50)
        
        # First ensure fossil exists
        logger.info(f"Creating/updating fossil: {request.fossil_name}")
        FossilRepository.create_or_update_fossil(name=request.fossil_name)
        
        # Then record the discovery
        logger.info(f"Recording discovery for user {current_user['user_id']}")
        FoundRepository.record_found(
            user_id=current_user["user_id"],
            fossil_name=request.fossil_name
        )
        
        logger.info("Fossil discovery recorded successfully")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "message": "Fossil discovery recorded successfully"
        }
    
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"ERROR RECORDING FOUND FOSSIL: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 50)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record fossil discovery"
        )


@router.get("/my-fossils")
async def get_user_fossils(current_user: dict = Depends(get_current_user)):
    """Get all fossils found by the current user (from 'found' table)"""
    try:
        logger.info("=" * 50)
        logger.info("GET USER FOSSILS REQUEST")
        logger.info(f"User ID: {current_user.get('user_id')}")
        logger.info("=" * 50)
        
        fossils = FoundRepository.get_user_fossils(current_user["user_id"])
        
        logger.info(f"Fossils retrieved: {len(fossils) if fossils else 0} items")
        if fossils:
            logger.info(f"First fossil sample: {fossils[0] if len(fossils) > 0 else 'N/A'}")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "data": fossils
        }
    
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"ERROR FETCHING USER FOSSILS: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 50)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user fossils"
        )


@router.get("/all")
async def get_all_fossils(current_user: dict = Depends(get_current_user)):
    """Get all fossils from the fossils table"""
    try:
        logger.info("=" * 50)
        logger.info("GET ALL FOSSILS REQUEST")
        logger.info(f"User ID: {current_user.get('user_id')}")
        logger.info("=" * 50)
        
        fossils = FossilRepository.get_all_fossils()
        
        logger.info(f"Total fossils retrieved: {len(fossils) if fossils else 0} items")
        if fossils:
            logger.info(f"First fossil: {fossils[0] if len(fossils) > 0 else 'N/A'}")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "data": fossils
        }
    
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"ERROR FETCHING ALL FOSSILS: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 50)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch fossils"
        )
