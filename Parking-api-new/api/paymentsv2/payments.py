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

    # Use NULL for p_session_id if you don't have a real session
    p_session_id = None

    payment = create_payment_db(
        user_id=user["id"],
        reservation_id=request.reservation_id,
        amount=request.amount,
        currency=request.currency,
        method=request.method,
        p_session_id=p_session_id
    )

    return {"status": "success", "payment": payment}

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
