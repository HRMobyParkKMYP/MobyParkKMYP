from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from api.utils.database_utils import get_db_connection, execute_query
import uuid

def generate_external_ref() -> str:
    return f"pay_{uuid.uuid4().hex}"

def create_payment_db(user_id: int, reservation_id: Optional[int], amount: float, currency: str, method: str, p_session_id: Optional[str] = None, discount_id: Optional[int] = None) -> Dict[str, Any]:
    """DB logic for creating a payment"""
    created_at = datetime.now(timezone.utc).isoformat()
    external_ref = generate_external_ref()

    query = """
        INSERT INTO payments
        (user_id, reservation_id, p_session_id, amount, currency, method, status, created_at, external_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (
            user_id,
            reservation_id,
            p_session_id,
            amount,
            currency,
            method,
            "initiated",
            created_at,
            external_ref
        ))

    return {
        "reservation_id": reservation_id,
        "amount": amount,
        "currency": currency,
        "method": method,
        "status": "initiated",
        "external_ref": external_ref,
        "p_session_id": p_session_id
    }

def get_my_payments_db(user_id: int) -> List[Dict[str, Any]]:
    """DB logic for retrieving user's payments"""
    query = "SELECT * FROM payments WHERE user_id = ?"
    return execute_query(query, (user_id,))

def refund_payment_db(external_ref: str) -> bool:
    """DB logic for refunding a payment"""
    query = "UPDATE payments SET status = ? WHERE external_ref = ?"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, ("refunded", external_ref))
        return cursor.rowcount > 0

def get_payment_by_external_ref(external_ref: str) -> Optional[Dict[str, Any]]:
    """DB logic for fetching a payment by external_ref"""
    query = "SELECT * FROM payments WHERE external_ref = ?"
    results = execute_query(query, (external_ref,))
    return results[0] if results else None

def get_user_payments_db(username: str) -> List[Dict[str, Any]]:
    """DB logic for fetching payments by username"""
    query = """
        SELECT p.*
        FROM payments p
        JOIN users u ON u.id = p.user_id
        WHERE u.username = ?
    """
    return execute_query(query, (username,))
