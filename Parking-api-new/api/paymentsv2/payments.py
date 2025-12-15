from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from utils.database_utils import execute_query, get_db_connection
from utils.session_manager import get_session
import uuid
import hashlib

router = APIRouter()


# ---------- Helpers ----------

def require_auth(token: Optional[str]):
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")
    user = get_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return user


def generate_transaction_hash(username: str = "") -> str:
    """Unieke transaction ID voor betaling of refund"""
    return f"tx-{uuid.uuid4()}"


def generate_validation_hash(username: str = "") -> str:
    """Unieke validation hash voor betaling"""
    data = f"{username}-{datetime.now().timestamp()}-{uuid.uuid4()}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


# ---------- Models ----------

class CreatePaymentRequest(BaseModel):
    transaction: str
    amount: float


class UpdatePaymentRequest(BaseModel):
    t_data: Dict[str, Any]
    validation: str


class RefundRequest(BaseModel):
    amount: float
    transaction: Optional[str] = None
    coupled_to: Optional[str] = None


# ---------- Endpoints ----------

@router.post("/payments", status_code=201)
async def create_payment(
    request: CreatePaymentRequest,
    authorization: Optional[str] = Header(None)
):
    user = require_auth(authorization)

    payment_hash = generate_validation_hash(user["username"])
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query = """
        INSERT INTO payments
        (transaction, amount, initiator, created_at, completed, hash)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, (
                request.transaction,
                request.amount,
                user["username"],
                created_at,
                None,
                payment_hash
            ))
        except Exception:
            raise HTTPException(status_code=409, detail="Payment already exists")

    return {
        "status": "Success",
        "payment": {
            "transaction": request.transaction,
            "amount": request.amount,
            "initiator": user["username"],
            "created_at": created_at,
            "completed": False,
            "hash": payment_hash
        }
    }


@router.put("/payments/{transaction}")
async def update_payment(
    transaction: str,
    request: UpdatePaymentRequest,
    authorization: Optional[str] = Header(None)
):
    require_auth(authorization)

    payments = execute_query(
        "SELECT * FROM payments WHERE transaction = ?",
        (transaction,)
    )
    if not payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = payments[0]
    if payment["hash"] != request.validation:
        raise HTTPException(status_code=401, detail="Validation failed")

    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE payments
            SET completed = ?, t_data = ?
            WHERE transaction = ?
            """,
            (completed_at, str(request.t_data), transaction)
        )

    return {"status": "Success"}


@router.get("/payments")
async def get_my_payments(authorization: Optional[str] = Header(None)):
    user = require_auth(authorization)
    return execute_query(
        "SELECT * FROM payments WHERE initiator = ? OR processed_by = ?",
        (user["username"], user["username"])
    )


@router.post("/payments/refund", status_code=201)
async def create_refund(
    request: RefundRequest,
    authorization: Optional[str] = Header(None)
):
    user = require_auth(authorization)
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied")

    tx = request.transaction or generate_transaction_hash(user["username"])
    payment_hash = generate_validation_hash(user["username"])
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO payments
            (transaction, amount, processed_by, coupled_to, created_at, completed, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx,
                -abs(request.amount),
                user["username"],
                request.coupled_to,
                created_at,
                None,
                payment_hash
            )
        )

    return {
        "status": "Success",
        "payment": {
            "transaction": tx,
            "amount": -abs(request.amount),
            "processed_by": user["username"],
            "hash": payment_hash
        }
    }