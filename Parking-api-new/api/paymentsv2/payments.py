from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from utils.session_manager import get_session
from utils.payment_utils import (
    create_payment as create_payment_util,
    get_payments_by_user,
    get_payments_by_username,
    get_payment_by_ref,
    update_payment_status,
    refund_payment
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
    paid_at: Optional[str] = None

# ---------- Endpoints ----------

@router.post("/payments", status_code=201)
async def create_payment(
    request: CreatePaymentRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    user = require_auth(authorization)
    payment = create_payment_util(user["id"], request.amount, request.currency, request.method, request.reservation_id)
    return {"status": "success", "payment": payment}

@router.get("/payments")
async def get_my_payments(authorization: Optional[str] = Header(None, alias="Authorization")):
    user = require_auth(authorization)
    return get_payments_by_user(user["id"])

@router.get("/payments/{username}")
async def get_user_payments(username: str):
    return get_payments_by_username(username)

@router.put("/payments/{external_ref}")
async def complete_payment(
    external_ref: str,
    request: UpdatePaymentRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    require_auth(authorization)
    if not get_payment_by_ref(external_ref):
        raise HTTPException(status_code=404, detail="Payment not found")
    update_payment_status(external_ref, request.status, request.paid_at)
    return {"status": "success"}

@router.post("/payments/refund")
async def refund_payment_endpoint(
    external_ref: str,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    require_auth(authorization)
    if not get_payment_by_ref(external_ref):
        raise HTTPException(status_code=404, detail="Payment not found")
    refund_payment(external_ref)
    return {"status": "success", "message": "Payment refunded"}
