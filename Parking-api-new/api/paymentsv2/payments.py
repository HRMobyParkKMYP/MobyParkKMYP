from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from utils.database_utils import execute_query, get_db_connection
from utils.session_manager import get_session
import uuid

router = APIRouter()

# ---------- Helpers ----------

def require_auth(token: Optional[str]):
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")
    user = get_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return user

def generate_external_ref() -> str:
    return f"pay_{uuid.uuid4().hex}"

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

    created_at = datetime.utcnow().isoformat()
    external_ref = generate_external_ref()

    # Use NULL for p_session_id if you don't have a real session
    p_session_id = None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO payments
                (user_id, reservation_id, p_session_id, amount, currency, method, status, created_at, external_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    request.reservation_id,
                    p_session_id,
                    request.amount,
                    request.currency,
                    request.method,
                    "initiated",  # <-- FIXED status
                    created_at,
                    external_ref
                )
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "payment": {
            "reservation_id": request.reservation_id,
            "amount": request.amount,
            "currency": request.currency,
            "method": request.method,
            "status": "initiated",
            "external_ref": external_ref,
            "p_session_id": p_session_id
        }
    }

@router.put("/payments/{external_ref}")
async def update_payment(
    external_ref: str,
    request: UpdatePaymentRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    require_auth(authorization)

    payment = execute_query(
        "SELECT * FROM payments WHERE external_ref = ?",
        (external_ref,)
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    paid_at = request.paid_at.isoformat() if request.paid_at else datetime.utcnow().isoformat()

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE payments
                SET status = ?, paid_at = ?
                WHERE external_ref = ?
                """,
                (
                    request.status,
                    paid_at,
                    external_ref
                )
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "success"}

@router.get("/payments")
async def get_my_payments(authorization: Optional[str] = Header(None, alias="Authorization")):
    user = require_auth(authorization)
    return execute_query(
        "SELECT * FROM payments WHERE user_id = ?",
        (user["id"],)
    )

# ---------- Additional Endpoints (for apiroutes compatibility) ----------

@router.post("/payments/refund")
async def refund_payment(
    external_ref: str,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    require_auth(authorization)

    payment = execute_query(
        "SELECT * FROM payments WHERE external_ref = ?",
        (external_ref,)
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE payments
                SET status = ?
                WHERE external_ref = ?
                """,
                ("refunded", external_ref)
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "success", "message": "Payment refunded"}


# Alias endpoint — same logic as update_payment
@router.put("/payments/{transaction}")
async def complete_payment(
    transaction: str,
    request: UpdatePaymentRequest,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    # Reuse existing logic exactly
    return await update_payment(transaction, request, authorization)


@router.get("/payments/{username}")
async def get_user_payments(username: str):
    payments = execute_query(
        """
        SELECT p.*
        FROM payments p
        JOIN users u ON u.id = p.user_id
        WHERE u.username = ?
        """,
        (username,)
    )

    return payments

