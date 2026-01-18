from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from utils.session_manager import get_session
from . import reservations_utils as db

router = APIRouter()

class ReservationCreateRequest(BaseModel):
    parking_lot_id: int
    vehicle_id: int
    start_time: str
    end_time: str
    status: Optional[str] = "pending"
    cost: Optional[float] = None

class ReservationUpdateRequest(BaseModel):
    parking_lot_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    cost: Optional[float] = None

# POST /reservations - Create reservation
@router.post("/reservations")
async def create_reservation(data: ReservationCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Check if parking lot exists
    parking_lot = db.get_parking_lot_by_id(data.parking_lot_id)
    if not parking_lot:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # Get user_id from session
    user_id = session_user.get("id")
    if not user_id:
        # Debug: print what's in session
        import json
        raise HTTPException(status_code=400, detail=f"User ID missing from session. Session data: {json.dumps(session_user)}")
    
    # CAPACITY CHECK: Ensure there's available capacity for this reservation
    capacity = parking_lot.get("capacity", 0)
    
    # Count overlapping reservations during the requested time period
    overlapping_reservations = db.get_overlapping_reservations(
        data.parking_lot_id, 
        data.start_time, 
        data.end_time
    )

    # Check if there's capacity available
    if overlapping_reservations >= capacity:
        raise HTTPException(
            status_code=409, 
            detail=f"Parking lot is fully booked for the requested time. {overlapping_reservations}/{capacity} reservations already exist for this time period."
        )
    
    # Create reservation
    new_reservation = {
        "user_id": user_id,
        "parking_lot_id": data.parking_lot_id,
        "vehicle_id": data.vehicle_id,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "status": data.status or "pending",
        "cost": data.cost
    }
    
    reservation_id = db.create_reservation(new_reservation)
    new_reservation["id"] = reservation_id
    
    # Update parking lot reserved count
    db.increment_reserved_count(data.parking_lot_id)
    
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
    user_id = session_user.get("id")
    if session_user.get("role") != "ADMIN" and user_id != reservation.get("user_id"):
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
    
    # Permission check: ADMIN or owner
    user_id = session_user.get("id")
    if session_user.get("role") != "ADMIN" and user_id != existing_reservation.get("user_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if parking lot exists (if being updated)
    if data.parking_lot_id:
        parking_lot = db.get_parking_lot_by_id(data.parking_lot_id)
        if not parking_lot:
            raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # CAPACITY CHECK: If time or parking lot is being changed, verify capacity
    if data.start_time or data.end_time or data.parking_lot_id:
        # Determine the lot_id, start_time, and end_time to check
        lot_id = data.parking_lot_id if data.parking_lot_id else existing_reservation.get("parking_lot_id")
        start_time = data.start_time if data.start_time else existing_reservation.get("start_time")
        end_time = data.end_time if data.end_time else existing_reservation.get("end_time")
        
        # Get parking lot capacity
        lot_to_check = db.get_parking_lot_by_id(lot_id)
        if lot_to_check:
            capacity = lot_to_check.get("capacity", 0)
            
            # Count overlapping reservations (excluding this one)
            overlapping_reservations = db.get_overlapping_reservations(
                lot_id, 
                start_time, 
                end_time,
                exclude_reservation_id=rid
            )
            
            # Check if there's capacity available
            # Note: We only check reservations, not current sessions, since this could be for a future date
            if overlapping_reservations >= capacity:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Cannot update: parking lot is fully booked for the requested time. {overlapping_reservations}/{capacity} reservations already exist for this time period."
                )
    
    # Build updated fields
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    
    db.update_reservation(rid, update_data)
    
    # Get updated reservation
    updated_reservation = db.get_reservation_by_id(rid)
    
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
    user_id = session_user.get("id")
    if session_user.get("role") != "ADMIN" and user_id != reservation.get("user_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    parking_lot_id = reservation.get("parking_lot_id")
    
    # Delete reservation
    db.delete_reservation(rid)
    
    # Update parking lot reserved count
    if parking_lot_id:
        db.decrement_reserved_count(parking_lot_id)
    
    return {"status": "Deleted"}
