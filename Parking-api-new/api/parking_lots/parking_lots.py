from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from utils.session_manager import get_session
from models.ParkingLot import ParkingLot
from . import parking_lots_utils as db

router = APIRouter()

class ParkingLotCreateRequest(BaseModel):
    name: str
    location: Optional[str] = None
    address: str
    capacity: int
    tariff: float
    day_tariff: Optional[float] = 0.0
    lat: Optional[float] = None
    lng: Optional[float] = None

class ParkingLotUpdateRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    capacity: Optional[int] = None
    tariff: Optional[float] = None
    day_tariff: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class SessionStartRequest(BaseModel):
    licenseplate: str

class SessionStopRequest(BaseModel):
    licenseplate: str

# GET all parking lots
@router.get("/parking-lots")
async def get_all_parking_lots():
    lots_data = db.get_all_parking_lots()
    lots = [ParkingLot.from_dict(lot).to_dict() for lot in lots_data]
    return {"parking_lots": lots}

# GET single parking lot
@router.get("/parking-lots/{lot_id}")
async def get_parking_lot(lot_id: int):
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    lot = ParkingLot.from_dict(lot_data)
    return lot.to_dict()

# POST create parking lot (ADMIN only)
@router.post("/parking-lots")
async def create_parking_lot(data: ParkingLotCreateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied: admin required")
    
    new_lot = ParkingLot(
        pid=None,
        name=data.name,
        location=data.location,
        address=data.address,
        capacity=data.capacity,
        reserved=0,
        tariff=data.tariff,
        day_tariff=data.day_tariff,
        created_at=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        lat=data.lat,
        lng=data.lng
    )
    
    lot_id = db.create_parking_lot(new_lot.to_dict())
    new_lot.id = lot_id
    
    return {"message": f"Parking lot saved under ID: {lot_id}", "lot_id": lot_id, "parking_lot": new_lot.to_dict()}

# PUT update parking lot (ADMIN only)
@router.put("/parking-lots/{lot_id}")
async def update_parking_lot(lot_id: int, data: ParkingLotUpdateRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied: admin required")
    
    existing_lot_data = db.get_parking_lot_by_id(lot_id)
    if not existing_lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    existing_lot = ParkingLot.from_dict(existing_lot_data)
    
    # Update only provided fields
    update_fields = data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        if value is not None:
            setattr(existing_lot, field, value)
    
    db.update_parking_lot(lot_id, existing_lot.to_dict())
    
    return {"message": "Parking lot modified", "parking_lot": existing_lot.to_dict()}

# DELETE parking lot (ADMIN only)
@router.delete("/parking-lots/{lot_id}")
async def delete_parking_lot(lot_id: int, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied: admin required")
    
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    db.delete_parking_lot(lot_id)
    
    return {"message": "Parking lot deleted"}

# POST start parking session
@router.post("/parking-lots/{lot_id}/sessions/start")
async def start_session(lot_id: int, data: SessionStartRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    licenseplate = data.licenseplate.strip()
    if not licenseplate:
        raise HTTPException(status_code=400, detail="Required field missing: licenseplate")
    
    # Check parking lot exists
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # Check if there's already an active session for this plate
    active_session = db.get_active_session_by_licenseplate(lot_id, licenseplate)
    if active_session:
        raise HTTPException(status_code=409, detail="Cannot start session: another session for this licenseplate is already active")
    
    # Create new session
    new_session = {
        "lot_id": lot_id,
        "licenseplate": licenseplate,
        "started": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "stopped": None,
        "user": session_user["username"]
    }
    
    session_id = db.create_parking_session(new_session)
    new_session["id"] = session_id
    
    return {"message": f"Session started for: {licenseplate}", "session": new_session}

# POST stop parking session
@router.post("/parking-lots/{lot_id}/sessions/stop")
async def stop_session(lot_id: int, data: SessionStopRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    licenseplate = data.licenseplate.strip()
    if not licenseplate:
        raise HTTPException(status_code=400, detail="Required field missing: licenseplate")
    
    # Check parking lot exists
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    # Find active session for this plate
    active_session = db.get_active_session_by_licenseplate(lot_id, licenseplate)
    if not active_session:
        raise HTTPException(status_code=404, detail="Cannot stop session: no active session for this licenseplate")
    
    # Stop the session
    db.update_parking_session(active_session["id"], {"stopped": datetime.now().strftime("%d-%m-%Y %H:%M:%S")})
    active_session["stopped"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    return {"message": f"Session stopped for: {licenseplate}", "session": active_session}

# GET all sessions for a parking lot
@router.get("/parking-lots/{lot_id}/sessions")
async def get_all_sessions(lot_id: int, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Check parking lot exists
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    sessions = db.get_sessions_by_lot_id(lot_id)
    
    # Admins see all sessions, users see only their own
    if session_user.get("role") != "ADMIN":
        sessions = [s for s in sessions if s.get("user_name") == session_user["username"]]
    
    return {"sessions": sessions}

# GET single session
@router.get("/parking-lots/{lot_id}/sessions/{session_id}")
async def get_session_details(lot_id: int, session_id: int, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Check parking lot exists
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    session_data = db.get_parking_session_by_id(session_id)
    if not session_data or session_data.get("parking_lot_id") != lot_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Permission check: ADMIN or owner
    if session_user.get("role") != "ADMIN" and session_user["username"] != session_data.get("user_name"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return session_data

# DELETE session (ADMIN only)
@router.delete("/parking-lots/{lot_id}/sessions/{session_id}")
async def delete_session(lot_id: int, session_id: int, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied: admin required")
    
    # Check parking lot exists
    lot_data = db.get_parking_lot_by_id(lot_id)
    if not lot_data:
        raise HTTPException(status_code=404, detail="Parking lot not found")
    
    session_data = db.get_parking_session_by_id(session_id)
    if not session_data or session_data.get("parking_lot_id") != lot_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete_parking_session(session_id)
    
    return {"message": "Session deleted"}