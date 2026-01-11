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


class UpdateDiscountRequest(BaseModel):
    """Request model for updating a discount"""
    description: Optional[str] = None
    percent: Optional[float] = None
    amount: Optional[float] = None
    applies_to: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None


def require_admin(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized: missing token")
    
    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid session")
    
    if session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied: admin required")
    
    return session_user


@router.post("/discounts", status_code=201)
async def create_discount(
    request: CreateDiscountRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Create a new discount code (admin only).
    
    Args:
        request: Discount details (code, description, percent or amount, etc.)
        authorization: Admin session token
    
    Returns:
        Created discount object with ID
    """
    require_admin(authorization)
    
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
        INSERT INTO discounts (code, description, percent, amount, applies_to, starts_at, ends_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
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
                ends_at
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
        ends_at=ends_at
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
    require_admin(authorization)
    
    try:
        query = "SELECT id, code, description, percent, amount, applies_to, starts_at, ends_at FROM discounts"
        discounts = execute_query(query)
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
    require_admin(authorization)
    
    query = "SELECT * FROM discounts WHERE id = ?"
    results = execute_query(query, (discount_id,))
    
    if not results:
        raise HTTPException(status_code=404, detail="Discount not found")
    
    return {
        "status": "success",
        "discount": results[0]
    }


@router.put("/discounts/{discount_id}")
async def update_discount(
    discount_id: int,
    request: UpdateDiscountRequest,
    authorization: Optional[str] = Header(None)
):
    require_admin(authorization)
    
    # Check if discount exists
    query = "SELECT id, code, description, percent, amount, applies_to, starts_at, ends_at FROM discounts WHERE id = ?"
    results = execute_query(query, (discount_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Discount not found")
    
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
    Delete a discount (admin only).
    
    Args:
        discount_id: ID of the discount to delete
        authorization: Admin session token
    
    Returns:
        Success message
    """
    require_admin(authorization)
    
    # Check if discount exists
    query = "SELECT * FROM discounts WHERE id = ?"
    results = execute_query(query, (discount_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Discount not found")
    
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
