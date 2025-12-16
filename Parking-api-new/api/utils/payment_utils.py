from typing import Optional, List, Dict
from datetime import datetime
import uuid
from utils.database_utils import get_db_connection, execute_query

def generate_external_ref() -> str:
    return f"pay_{uuid.uuid4().hex}"

def create_payment(user_id: int, amount: float, currency: str, method: str, reservation_id: Optional[int] = None, p_session_id: Optional[str] = None) -> Dict:
    created_at = datetime.utcnow().isoformat()
    external_ref = generate_external_ref()
    status = "initiated"

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
            status,
            created_at,
            external_ref
        ))

    return {
        "reservation_id": reservation_id,
        "amount": amount,
        "currency": currency,
        "method": method,
        "status": status,
        "external_ref": external_ref,
        "p_session_id": p_session_id
    }

def get_payments_by_user(user_id: int) -> List[Dict]:
    return execute_query("SELECT * FROM payments WHERE user_id = ?", (user_id,))

def get_payments_by_username(username: str) -> List[Dict]:
    query = """
        SELECT p.*
        FROM payments p
        JOIN users u ON u.id = p.user_id
        WHERE u.username = ?
    """
    return execute_query(query, (username,))

def get_payment_by_ref(external_ref: str) -> Optional[Dict]:
    results = execute_query("SELECT * FROM payments WHERE external_ref = ?", (external_ref,))
    return results[0] if results else None

def update_payment_status(external_ref: str, status: str, paid_at: Optional[datetime] = None) -> bool:
    updates = ["status = ?"]
    params = [status]

    if paid_at:
        updates.append("paid_at = ?")
        params.append(paid_at.isoformat())

    params.append(external_ref)

    query = f"UPDATE payments SET {', '.join(updates)} WHERE external_ref = ?"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.rowcount > 0

def refund_payment(external_ref: str) -> bool:
    return update_payment_status(external_ref, "refunded")
