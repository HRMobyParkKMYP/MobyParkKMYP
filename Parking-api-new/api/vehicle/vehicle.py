from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from utils import vehicle_utils
from utils.session_manager import get_session

router = APIRouter()

# Request/Response models
class CreateVehicleRequest(BaseModel):
    license_plate: str
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    year: Optional[int] = None

class UpdateVehicleRequest(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    year: Optional[int] = None

class VehicleEntryRequest(BaseModel):
    parkinglot: str


@router.post("/vehicles", status_code=201)
async def create_vehicle(request: CreateVehicleRequest, authorization: Optional[str] = Header(None)):
    """Create a new vehicle for the authenticated user"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    # Checkt op vereiste velden
    if not request.license_plate:
        raise HTTPException(status_code=400, detail="Missing required field: license_plate")
    
    # Check of voertuig met hetzelfde kenteken al bestaat voor deze gebruiker
    existing_vehicle = vehicle_utils.get_vehicle_by_license_plate(request.license_plate, user_id)
    if existing_vehicle:
        raise HTTPException(
            status_code=409, 
            detail={"error": "Vehicle already exists", "data": existing_vehicle}
        )
    
    # Maak het voertuig aan
    try:
        vehicle_id = vehicle_utils.create_vehicle(
            user_id=user_id,
            license_plate=request.license_plate,
            make=request.make,
            model=request.model,
            color=request.color,
            year=request.year
        )
        
        return {
            "status": "Success",
            "vehicle": {
                "id": vehicle_id,
                "license_plate": request.license_plate,
                "make": request.make,
                "model": request.model,
                "color": request.color,
                "year": request.year
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/vehicles/{vehicle_id}/entry")
async def vehicle_entry(vehicle_id: str, request: VehicleEntryRequest, authorization: Optional[str] = Header(None)):
    """Register vehicle entry to a parking lot"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    # Checkt op vereiste velden
    if not request.parkinglot:
        raise HTTPException(status_code=400, detail={"error": "Require field missing", "field": "parkinglot"})
    
    # Check of voertuig bestaat en bij user hoort
    vehicle = vehicle_utils.get_vehicle_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail={"error": "Vehicle does not exist", "data": vehicle_id})
    
    # TODO: Implementeerer logic voor voertuigentry in parkeerplaats
    return {"status": "Accepted", "vehicle": vehicle}


@router.put("/vehicles/{vehicle_id}")
async def update_vehicle(vehicle_id: str, request: UpdateVehicleRequest, authorization: Optional[str] = Header(None)):
    """Update vehicle information"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    # Checkt of er minimaal één veld is om te updaten
    if not any([request.make, request.model, request.color, request.year]):
        raise HTTPException(status_code=400, detail={"error": "Require field missing", "field": "At least one field required"})
    
    # Check of voertuig bestaat en bij user hoort
    vehicle = vehicle_utils.get_vehicle_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail={"error": "Vehicle not found"})
    
    # Update voertuig
    try:
        success = vehicle_utils.update_vehicle(
            vehicle_id, user_id, 
            make=request.make,
            model=request.model,
            color=request.color,
            year=request.year
        )
        if not success:
            raise HTTPException(status_code=404, detail={"error": "Vehicle not found"})
        
        # Get updated vehicle
        updated_vehicle = vehicle_utils.get_vehicle_by_id(vehicle_id, user_id)
        return {"status": "Success", "vehicle": updated_vehicle}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str, authorization: Optional[str] = Header(None)):
    """Delete a vehicle"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    # Check of voertuig bestaat en bij user hoort
    vehicle = vehicle_utils.get_vehicle_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(status_code=403, detail="Vehicle not found!")
    
    # Delete vehicle
    try:
        success = vehicle_utils.delete_vehicle(vehicle_id, user_id)
        if not success:
            raise HTTPException(status_code=403, detail="Vehicle not found!")
        
        return {"status": "Deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/vehicles")
async def get_vehicles(authorization: Optional[str] = Header(None)):
    """Get all vehicles for the authenticated user"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    try:
        vehicles = vehicle_utils.get_vehicles_by_user_id(user_id)
        return vehicles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/vehicles/{vehicle_id}/reservations")
async def get_vehicle_reservations(vehicle_id: str, authorization: Optional[str] = Header(None)):
    """Get all reservations for a specific vehicle"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    # Check of voertuig bestaat en bij user hoort
    vehicle = vehicle_utils.get_vehicle_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Not found!")
    
    try:
        reservations = vehicle_utils.get_vehicle_reservations(vehicle_id, user_id)
        return reservations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/vehicles/{vehicle_id}/history")
async def get_vehicle_history(vehicle_id: str, authorization: Optional[str] = Header(None)):
    """Get history for a specific vehicle"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    # Check of voertuig bestaat en bij user hoort
    vehicle = vehicle_utils.get_vehicle_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Not found!")
    
    try:
        history = vehicle_utils.get_vehicle_history(vehicle_id, user_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
