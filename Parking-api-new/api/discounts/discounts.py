from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from utils.session_manager import get_session
from utils.database_utils import execute_query, get_db_connection
from models.Discount import Discount

router = APIRouter()


class CreateDiscountRequest(BaseModel):
    """Request model for creating a discount"""
    code: str
    description: str = ""
    percent: Optional[float] = None
    amount: Optional[float] = None
    applies_to: str = "both"  # "reservation", "payment", or "both"
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    parking_lot_id: Optional[int] = None  # Specific parking lot (optional)


class UpdateDiscountRequest(BaseModel):
    """Request model for updating a discount"""
    description: Optional[str] = None
    percent: Optional[float] = None
    amount: Optional[float] = None
    applies_to: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    parking_lot_id: Optional[int] = None


def require_admin(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied: admin required")
    
    return session_user


def require_admin_or_parking_lot_manager(authorization: Optional[str]) -> dict:
    """Require either ADMIN or PARKING_LOT_MANAGER role"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    # Get current role from database (in case it was updated)
    user_id = session_user.get("id")
    if user_id:
        db_results = execute_query(
            "SELECT role FROM users WHERE id = ?",
            (user_id,)
        )
        if db_results:
            db_role = db_results[0].get("role")
            # Update session cache with current role
            session_user['role'] = db_role
        else:
            raise HTTPException(status_code=401, detail="Unauthorized: user not found")
    
    role = session_user.get("role")
    if role not in ["ADMIN", "PARKING_LOT_MANAGER"]:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: admin or parking lot manager required"
        )
    
    return session_user


def user_manages_parking_lot(user: dict, parking_lot_id: int) -> bool:
    """
    Check if a PARKING_LOT_MANAGER user manages the specified parking lot.
    ADMIN users can manage all parking lots.
    """
    if user.get("role") == "ADMIN":
        return True
    
    if user.get("role") != "PARKING_LOT_MANAGER":
        return False
    
    # Check if user manages this parking lot
    # parking_lot_id would be stored in user profile/session
    # For now, we check the user_id against parking_lot_manager association table
    user_id = user.get("id")
    results = execute_query(
        "SELECT parking_lot_id FROM parking_lot_managers WHERE user_id = ? AND parking_lot_id = ?",
        (user_id, parking_lot_id)
    )
    return len(results) > 0


@router.post("/discounts", status_code=201)
async def create_discount(
    request: CreateDiscountRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Create a new discount code.
    - ADMIN: can create discounts for any parking lot or globally
    - PARKING_LOT_MANAGER: can only create discounts for their own parking lots
    
    Args:
        request: Discount details (code, description, percent or amount, parking_lot_id, etc.)
        authorization: Admin or parking lot manager session token
    
    Returns:
        Created discount object with ID
    """
    user = require_admin_or_parking_lot_manager(authorization)
    
    # If parking lot manager, validate they manage the requested parking lot
    if user.get("role") == "PARKING_LOT_MANAGER":
        if not request.parking_lot_id:
            raise HTTPException(
                status_code=400,
                detail="Parking lot manager must specify parking_lot_id"
            )
        if not user_manages_parking_lot(user, request.parking_lot_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: you don't manage parking lot {request.parking_lot_id}"
            )
    
    # Validate input
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Code is required")
    
    # Either percent or amount, but not both (and not neither)
    if (request.percent is None and request.amount is None) or \
       (request.percent is not None and request.amount is not None):
        raise HTTPException(
            status_code=400,
            detail="Must specify either percent or amount, but not both"
        )
    
    # Check if code already exists
    existing = execute_query(
        "SELECT * FROM discounts WHERE LOWER(code) = LOWER(?)",
        (request.code.strip(),)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Discount code '{request.code}' already exists"
        )
    
    # Set default date ranges if not provided
    starts_at = request.starts_at
    if not starts_at:
        starts_at = datetime.utcnow().isoformat()
    
    ends_at = request.ends_at
    if not ends_at:
        # Default to 30 days from now
        ends_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    # Insert into database
    query = """
        INSERT INTO discounts (code, description, percent, amount, applies_to, starts_at, ends_at, parking_lot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                request.code.strip(),
                request.description,
                request.percent,
                request.amount,
                request.applies_to,
                starts_at,
                ends_at,
                request.parking_lot_id
            ))
            discount_id = cursor.lastrowid
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Return created discount
    discount = Discount(
        did=discount_id,
        code=request.code.strip(),
        description=request.description,
        percent=request.percent,
        amount=request.amount,
        applies_to=request.applies_to,
        starts_at=starts_at,
        ends_at=ends_at,
        parking_lot_id=request.parking_lot_id
    )
    
    return {
        "status": "success",
        "message": "Discount created successfully",
        "discount": discount.to_dict()
    }


@router.get("/discounts")
async def list_discounts(
    authorization: Optional[str] = Header(None)
):
    """
    List discount codes.
    - ADMIN: can see all discounts
    - PARKING_LOT_MANAGER: can only see discounts for their parking lots
    """
    user = require_admin_or_parking_lot_manager(authorization)
    
    try:
        if user.get("role") == "ADMIN":
            # Admin can see all discounts
            query = "SELECT id, code, description, percent, amount, applies_to, starts_at, ends_at, parking_lot_id FROM discounts"
            discounts = execute_query(query)
        else:
            # Parking lot manager can only see their discounts
            user_id = user.get("id")
            query = """
                SELECT DISTINCT d.id, d.code, d.description, d.percent, d.amount, 
                       d.applies_to, d.starts_at, d.ends_at, d.parking_lot_id
                FROM discounts d
                WHERE d.parking_lot_id IN (
                    SELECT parking_lot_id FROM parking_lot_managers WHERE user_id = ?
                )
                OR d.parking_lot_id IS NULL
            """
            discounts = execute_query(query, (user_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {
        "status": "success",
        "count": len(discounts),
        "discounts": discounts
    }


@router.get("/discounts/{discount_id}")
async def get_discount(
    discount_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    Get a specific discount.
    - ADMIN: can get any discount
    - PARKING_LOT_MANAGER: can only get discounts for their parking lots
    """
    user = require_admin_or_parking_lot_manager(authorization)
    
    query = "SELECT * FROM discounts WHERE id = ?"
    results = execute_query(query, (discount_id,))
    
    if not results:
        raise HTTPException(status_code=404, detail="Discount not found")
    
    discount = results[0]
    
    # Check authorization for parking lot managers
    if user.get("role") == "PARKING_LOT_MANAGER":
        if discount.get("parking_lot_id") and not user_manages_parking_lot(user, discount.get("parking_lot_id")):
            raise HTTPException(status_code=403, detail="Access denied: discount belongs to different parking lot")
    
    return {
        "status": "success",
        "discount": discount
    }


@router.put("/discounts/{discount_id}")
async def update_discount(
    discount_id: int,
    request: UpdateDiscountRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Update a discount.
    - ADMIN: can update any discount
    - PARKING_LOT_MANAGER: can only update discounts for their parking lots
    """
    user = require_admin_or_parking_lot_manager(authorization)
    
    # Check if discount exists
    query = "SELECT id, code, description, percent, amount, applies_to, starts_at, ends_at, parking_lot_id FROM discounts WHERE id = ?"
    results = execute_query(query, (discount_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Discount not found")
    
    discount = results[0]
    
    # Check authorization for parking lot managers
    if user.get("role") == "PARKING_LOT_MANAGER":
        if discount.get("parking_lot_id") and not user_manages_parking_lot(user, discount.get("parking_lot_id")):
            raise HTTPException(status_code=403, detail="Access denied: discount belongs to different parking lot")
    
    # Build update query
    updates = []
    params = []
    
    if request.description is not None:
        updates.append("description = ?")
        params.append(request.description)
    
    if request.percent is not None:
        updates.append("percent = ?")
        params.append(request.percent)
    
    if request.amount is not None:
        updates.append("amount = ?")
        params.append(request.amount)
    
    if request.applies_to is not None:
        updates.append("applies_to = ?")
        params.append(request.applies_to)
    
    if request.starts_at is not None:
        updates.append("starts_at = ?")
        params.append(request.starts_at)
    
    if request.ends_at is not None:
        updates.append("ends_at = ?")
        params.append(request.ends_at)
    
    if request.parking_lot_id is not None:
        # Prevent parking lot managers from changing parking lot
        if user.get("role") == "PARKING_LOT_MANAGER":
            raise HTTPException(
                status_code=403,
                detail="Parking lot managers cannot change parking lot assignment"
            )
        updates.append("parking_lot_id = ?")
        params.append(request.parking_lot_id)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(discount_id)
    update_query = f"UPDATE discounts SET {', '.join(updates)} WHERE id = ?"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(update_query, tuple(params))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Return updated discount
    results = execute_query("SELECT * FROM discounts WHERE id = ?", (discount_id,))
    discount_data = results[0] if results else {}
    
    return {
        "status": "success",
        "message": "Discount updated successfully",
        "discount": discount_data
    }


@router.delete("/discounts/{discount_id}")
async def delete_discount(
    discount_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    Delete a discount.
    - ADMIN: can delete any discount
    - PARKING_LOT_MANAGER: can only delete discounts for their parking lots
    
    Args:
        discount_id: ID of the discount to delete
        authorization: Admin or parking lot manager session token
    
    Returns:
        Success message
    """
    user = require_admin_or_parking_lot_manager(authorization)
    
    # Check if discount exists
    query = "SELECT * FROM discounts WHERE id = ?"
    results = execute_query(query, (discount_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Discount not found")
    
    discount = results[0]
    
    # Check authorization for parking lot managers
    if user.get("role") == "PARKING_LOT_MANAGER":
        if discount.get("parking_lot_id") and not user_manages_parking_lot(user, discount.get("parking_lot_id")):
            raise HTTPException(status_code=403, detail="Access denied: discount belongs to different parking lot")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM discounts WHERE id = ?", (discount_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {
        "status": "success",
        "message": "Discount deleted successfully"
    }
