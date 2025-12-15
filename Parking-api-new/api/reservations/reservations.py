from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from utils.session_manager import get_session
from . import reservations_utils as db

router = APIRouter()

class ReservationCreateRequest(BaseModel):
    licenseplate: str
    startdate: str
    enddate: str
    parkinglot: int
    user: Optional[str] = None

class ReservationUpdateRequest(BaseModel):
    licenseplate: str
    startdate: str
    enddate: str
    parkinglot: int
    user: Optional[str] = None

# POST /reservations - Create reservation
@router.post("/reservations")
async def create_reservation(data: ReservationCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Check if parking lot exists
    parking_lot = db.get_parking_lot_by_id(data.parkinglot)
    if not parking_lot:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # Handle user field based on role
    if session_user.get("role") == "ADMIN":
        if not data.user:
            raise HTTPException(status_code=400, detail="Required field missing: user")
        username = data.user
    else:
        username = session_user.get("username")
    
    # Create reservation
    new_reservation = {
        "licenseplate": data.licenseplate,
        "startdate": data.startdate,
        "enddate": data.enddate,
        "parkinglot": data.parkinglot,
        "user": username
    }
    
    reservation_id = db.create_reservation(new_reservation)
    new_reservation["id"] = reservation_id
    
    # Update parking lot reserved count
    db.increment_reserved_count(data.parkinglot)
    
    return {"status": "Success", "reservation": new_reservation}

# GET /reservations/{rid} - Get single reservation
@router.get("/reservations/{rid}")
async def get_reservation(rid: int, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    reservation = db.get_reservation_by_id(rid)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Permission check: ADMIN or owner
    if session_user.get("role") != "ADMIN" and session_user.get("username") != reservation.get("user"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return reservation

# PUT /reservations/{rid} - Update reservation
@router.put("/reservations/{rid}")
async def update_reservation(rid: int, data: ReservationUpdateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Check if reservation exists
    existing_reservation = db.get_reservation_by_id(rid)
    if not existing_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Check if parking lot exists
    parking_lot = db.get_parking_lot_by_id(data.parkinglot)
    if not parking_lot:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # Handle user field based on role
    if session_user.get("role") == "ADMIN":
        if not data.user:
            raise HTTPException(status_code=400, detail="Required field missing: user")
        username = data.user
    else:
        username = session_user.get("username")
    
    # Update reservation
    updated_reservation = {
        "id": rid,
        "licenseplate": data.licenseplate,
        "startdate": data.startdate,
        "enddate": data.enddate,
        "parkinglot": data.parkinglot,
        "user": username
    }
    
    db.update_reservation(rid, updated_reservation)
    
    return {"status": "Updated", "reservation": updated_reservation}

# DELETE /reservations/{rid} - Delete reservation
@router.delete("/reservations/{rid}")
async def delete_reservation(rid: int, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Check if reservation exists
    reservation = db.get_reservation_by_id(rid)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Permission check: ADMIN or owner
    if session_user.get("role") != "ADMIN" and session_user.get("username") != reservation.get("user"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    parking_lot_id = reservation.get("parkinglot")
    
    # Delete reservation
    db.delete_reservation(rid)
    
    # Update parking lot reserved count
    if parking_lot_id:
        db.decrement_reserved_count(parking_lot_id)
    
    return {"status": "Deleted"}
