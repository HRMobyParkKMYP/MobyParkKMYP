"""
End-to-end tests for discount code functionality with payments
"""
import pytest
import requests
import uuid
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = "http://localhost:8000"


@pytest.fixture
def discount_db():
    """Get the appropriate database path (main db, not test db, since server likely uses main)"""
    db_path = Path(__file__).parent.parent / "api" / "data" / "parking.sqlite3"
    return str(db_path)


@pytest.fixture
def auth_token(register_and_login):
    """Create a test user and return their auth token"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"discuser_{unique_id}"
    password = "secret123"
    name = "Discount User"
    email = f"discuser_{unique_id}@test.local"
    # Use hash-based phone number generation like in reservations_test.py
    phone = f"+31{hash(unique_id) % 900000000 + 100000000}"
    
    token = register_and_login(username, password, name, email, phone, 1990)
    return token


def insert_discount(db_path, code, percent=None, amount=None, description="Test Discount", 
                   starts_at=None, ends_at=None):
    """Helper to insert a discount into the database"""
    import time
    
    # Wait a bit to avoid locking issues
    time.sleep(0.1)
    
    conn = sqlite3.connect(db_path, timeout=5.0)  # Add timeout for lock
    cursor = conn.cursor()
    
    # Default times
    if starts_at is None:
        starts_at = (datetime.now() - timedelta(days=1)).isoformat()
    if ends_at is None:
        ends_at = (datetime.now() + timedelta(days=30)).isoformat()
    
    # Make code unique by adding a random suffix
    unique_code = f"{code}_{uuid.uuid4().hex[:4]}"
    
    # Use 'reservation' for applies_to since that's a valid value in DB schema
    try:
        cursor.execute("""
            INSERT INTO discounts (code, description, percent, amount, applies_to, starts_at, ends_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (unique_code, description, percent, amount, "reservation", starts_at, ends_at))
        
        conn.commit()
        
        # Return the unique code that was actually inserted
        return unique_code
    finally:
        conn.close()


def test_create_payment_with_valid_percent_discount(auth_token, discount_db):
    """Create payment with valid percentage discount code"""
    # Insert discount: 10% off
    code = insert_discount(discount_db, "SAVE10", percent=10.0)
    
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": code
        }
    )

    assert res.status_code == 201, f"Failed: {res.text}"
    body = res.json()
    assert body["status"] == "success"
    
    # Verify discount was applied
    assert "discount" in body
    assert body["discount"]["code"] == code
    assert body["discount"]["original_amount"] == 100.0
    
    # 10% of 100 = 10, so final should be 90
    assert body["discount"]["discount_amount"] == 10.0
    assert body["discount"]["final_amount"] == 90.0
    
    # Payment amount should reflect the discount
    assert body["payment"]["amount"] == 90.0


def test_create_payment_with_valid_flat_discount(auth_token, discount_db):
    """Create payment with valid flat amount discount code"""
    # Insert discount: €15 off
    code = insert_discount(discount_db, "SAVE15EUR", amount=15.0)
    
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": code
        }
    )

    assert res.status_code == 201
    body = res.json()
    
    # Verify discount was applied
    assert "discount" in body
    assert body["discount"]["code"] == code
    assert body["discount"]["original_amount"] == 100.0
    assert body["discount"]["discount_amount"] == 15.0
    assert body["discount"]["final_amount"] == 85.0
    assert body["payment"]["amount"] == 85.0


def test_discount_cannot_exceed_payment_amount(auth_token, discount_db):
    """Verify discount never exceeds payment amount"""
    # Insert discount: 80% off (so 80 off of 100)
    code = insert_discount(discount_db, "HUGE80", percent=80.0)
    
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": code
        }
    )

    assert res.status_code == 201
    body = res.json()
    
    # Final amount should never be negative
    assert body["discount"]["final_amount"] >= 0
    assert body["discount"]["discount_amount"] <= body["discount"]["original_amount"]


def test_create_payment_with_expired_discount(auth_token, discount_db):
    """Create payment with expired discount code - should fail"""
    # Insert discount that expired yesterday
    expired_time = (datetime.now() - timedelta(days=1)).isoformat()
    code = insert_discount(
        discount_db, "EXPIRED_CODE", percent=10.0, 
        ends_at=expired_time
    )
    
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": code
        }
    )

    # Should return 400 with error about expired discount
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
    assert "expired" in res.text.lower()


def test_create_payment_with_future_discount(auth_token, discount_db):
    """Create payment with discount that hasn't started yet - should fail"""
    # Insert discount that starts tomorrow
    future_time = (datetime.now() + timedelta(days=1)).isoformat()
    code = insert_discount(
        discount_db, "FUTURE_CODE", percent=10.0, 
        starts_at=future_time
    )
    
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": code
        }
    )

    # Should return 400 with error about invalid discount
    assert res.status_code == 400
    assert "expired" in res.text.lower() or "not valid" in res.text.lower()


def test_discount_code_case_insensitive(auth_token, discount_db):
    """Verify discount codes are case-insensitive"""
    # Insert discount with lowercase code
    code = insert_discount(discount_db, "casetest", percent=20.0)
    
    # Try with uppercase
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": code.upper()  # Use uppercase
        }
    )

    # Should work (case-insensitive lookup)
    assert res.status_code == 201
    body = res.json()
    # Code should match what was inserted (which may be in different case than requested)
    assert body["discount"]["code"].lower() == code.lower()
    assert body["discount"]["discount_amount"] == 20.0


def test_payment_without_discount(auth_token):
    """Verify payment works normally without discount code"""
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 75.0,
            "currency": "EUR",
            "method": "IDEAL"
        }
    )

    assert res.status_code == 201
    body = res.json()
    
    # No discount should be applied
    assert "discount" not in body or body.get("discount") is None
    assert body["payment"]["amount"] == 75.0
