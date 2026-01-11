from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from utils.session_manager import get_session
from utils.payment_utils import (
    generate_external_ref,
    create_payment_db,
    get_my_payments_db,
    refund_payment_db,
    get_payment_by_external_ref,
    get_user_payments_db
)
from discounts.discount_utils import apply_discount_to_payment, get_discount_by_code

router = APIRouter()

# ---------- Helpers ----------

def require_auth(token: Optional[str]):
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")
    user = get_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return user

# ---------- Models ----------

class CreatePaymentRequest(BaseModel):
    reservation_id: Optional[int] = None
    amount: float
    currency: str
    method: str
    discount_code: Optional[str] = None

class UpdatePaymentRequest(BaseModel):
    status: str
    paid_at: Optional[datetime] = None

# ---------- Endpoints ----------

@router.post("/payments", status_code=201)
async def create_payment(
    request: CreatePaymentRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    user = require_auth(authorization)

    # Validate and apply discount if provided
    final_amount = request.amount
    discount_id = None
    discount_code_used = None
    
    if request.discount_code:
        success, final_amount, error_msg = apply_discount_to_payment(
            request.discount_code,
            request.amount
        )
        if not success:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Get discount ID for storage
        discount = get_discount_by_code(request.discount_code)
        if discount:
            discount_id = discount.get("id")
            discount_code_used = request.discount_code

    # Use NULL for p_session_id if you don't have a real session
    p_session_id = None

    payment = create_payment_db(
        user_id=user["id"],
        reservation_id=request.reservation_id,
        amount=final_amount,  # Use discounted amount
        currency=request.currency,
        method=request.method,
        p_session_id=p_session_id,
        discount_id=discount_id
    )

    response = {"status": "success", "payment": payment}
    
    # Include discount information in response
    if discount_code_used:
        response["discount"] = {
            "code": discount_code_used,
            "original_amount": request.amount,
            "final_amount": final_amount,
            "discount_amount": request.amount - final_amount
        }
    
    return response

@router.get("/payments")
async def get_my_payments(authorization: Optional[str] = Header(None, alias="Authorization")):
    user = require_auth(authorization)
    payments = get_my_payments_db(user["id"])
    return payments

# ---------- Additional Endpoints (for apiroutes compatibility) ----------

@router.post("/payments/refund")
async def refund_payment(
    external_ref: str,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    require_auth(authorization)

    payment = get_payment_by_external_ref(external_ref)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    success = refund_payment_db(external_ref)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to refund payment")

    return {"status": "success", "message": "Payment refunded"}

@router.put("/payments/{transaction}")
async def complete_payment(
    transaction: str,
    request: UpdatePaymentRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    # Keep this alias endpoint as-is (it previously called update_payment)
    # Logic can later use utils if needed
    return {"status": "success", "message": "Transaction completed"}

@router.get("/payments/{username}")
async def get_user_payments(username: str):
    payments = get_user_payments_db(username)
    return payments
