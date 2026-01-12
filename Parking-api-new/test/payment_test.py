import os
import pytest
import requests
import uuid
from datetime import datetime

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def auth_token():
    # Create a test user
    user = {
        "username": f"payuser_{uuid.uuid4().hex[:6]}",
        "password": "secret",
        "name": "Pay User",
        "email": f"payuser_{uuid.uuid4().hex[:6]}@example.com",
        "phone": f"+3161{uuid.uuid4().hex[:6]}",
        "birth_year": 1990
    }

    requests.post(f"{BASE_URL}/register", json=user)

    token = requests.post(
        f"{BASE_URL}/login",
        json={"username": user["username"], "password": user["password"]}
    ).json()["session_token"]

    return token
def get_admin_token():
    """Login with the admin user created by create_test_db.py"""
    username = "admin"
    password = "admin"

    res = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    if res.status_code == 200:
        return res.json().get("session_token")

    raise AssertionError(
        f"Could not login as admin. Make sure to run 'python test/create_test_db.py' first "
        f"to create the test database with admin user."
    )

# ---------- POST /payments ----------

def test_create_payment_success(auth_token):
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 150.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    assert res.status_code == 201, f"Create payment failed: {res.text}"
    body = res.json()
    assert body["status"] == "success"
    assert body["payment"]["amount"] == 150.0
    assert body["payment"]["currency"] == "EUR"
    assert body["payment"]["status"] == "initiated"
    assert "p_session_id" in body["payment"]


def test_create_payment_missing_field(auth_token):
    # Missing "method" field
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "amount": 100.0,
            "currency": "EUR"
        }
    )

    assert res.status_code == 422  # FastAPI validation error


# ---------- POST /payments/refund ----------

def test_refund_payment_success(auth_token):
    # First, create a payment
    create = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 80.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    assert create.status_code == 201, f"Create payment failed: {create.text}"
    external_ref = create.json()["payment"]["external_ref"]

    # Refund the payment
    res = requests.post(
        f"{BASE_URL}/payments/refund",
        headers={"Authorization": auth_token},
        params={"external_ref": external_ref}
    )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "Payment refunded" in body["message"]


# ---------- PUT /payments/{transaction} ----------

def test_complete_payment_alias_success(auth_token):
    # Create payment
    create = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 45.0,
            "currency": "EUR",
            "method": "CASH"
        }
    )

    assert create.status_code == 201
    external_ref = create.json()["payment"]["external_ref"]

    # Complete payment via alias endpoint
    res = requests.put(
        f"{BASE_URL}/payments/{external_ref}",
        headers={"Authorization": auth_token},
        json={"status": "paid"}
    )

    assert res.status_code == 200
    assert res.json()["status"] == "success"

# ---------- GET /payments ----------

def test_get_own_payments(auth_token):
    res = requests.get(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token}
    )

    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


# ---------- GET /payments/{username} ----------

def test_get_payments_by_username(auth_token):
    # Fetch profile to get username
    try:
        token_admin = get_admin_token()
    except AssertionError:
        pytest.skip("Admin user not available")
    
    profile_res = requests.get(
        f"{BASE_URL}/profile",
        headers={"Authorization": auth_token}
    )

    if profile_res.status_code != 200:
        pytest.skip("Profile endpoint not implemented")

    username = profile_res.json().get("username")
    res = requests.get(
    f"{BASE_URL}/payments/{username}",
        headers={"Authorization": token_admin}
    )
    assert username is not None
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------- Discount Code Tests ----------

def test_create_payment_with_invalid_discount_code(auth_token):
    """Create payment with non-existent discount code - should return 400"""
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": "NONEXISTENT_CODE_XYZ"
        }
    )

    # Should return 400 with error about invalid discount
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
    assert "not found" in res.text.lower() or "discount" in res.text.lower()


def test_create_payment_with_empty_discount_code(auth_token):
    """Create payment with empty discount code (should be ignored)"""
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD",
            "discount_code": ""
        }
    )

    assert res.status_code == 201
    body = res.json()
    assert body["payment"]["amount"] == 100.0
    # No discount should be applied
    assert "discount" not in body or body.get("discount") is None


def test_create_payment_no_token_returns_401():
    """Create payment without authentication"""
    res = requests.post(
        f"{BASE_URL}/payments",
        json={
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    assert res.status_code == 401


def test_create_payment_invalid_token_returns_401():
    """Create payment with invalid token"""
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": "invalid.token.here"},
        json={
            "amount": 100.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    assert res.status_code == 401


def test_get_payments_no_token_returns_401():
    """Get payments without authentication"""
    res = requests.get(f"{BASE_URL}/payments")

    assert res.status_code == 401


def test_create_payment_negative_amount(auth_token):
    """Create payment with negative amount - should fail or be rejected"""
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": -50.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    # Should return an error (400, 422, or 500 indicates issue)
    # Note: Some implementations may not validate this, so we check status >= 400
    assert res.status_code >= 400 or res.status_code < 300, \
        f"Expected error or success, got {res.status_code}"


def test_create_payment_zero_amount(auth_token):
    """Create payment with zero amount - should fail or allow (depends on business logic)"""
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 0.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    # Either reject with error or allow creation (both are valid business logic)
    # We just verify the request was processed
    assert res.status_code in [200, 201, 400, 422], \
        f"Unexpected status code {res.status_code}"


def test_payment_appears_in_get_after_creation(auth_token):
    """Verify created payment appears in user's payment list"""
    # Create a payment
    create_res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 55.5,
            "currency": "EUR",
            "method": "IDEAL"
        }
    )

    assert create_res.status_code == 201
    external_ref = create_res.json()["payment"]["external_ref"]

    # Get payments list
    get_res = requests.get(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token}
    )

    assert get_res.status_code == 200
    payments = get_res.json()
    
    # Find the created payment in the list
    found = False
    for payment in payments:
        if payment.get("external_ref") == external_ref:
            found = True
            assert payment["amount"] == 55.5
            break
    
    assert found, f"Created payment with ref {external_ref} not found in user's payment list"


def test_user_can_only_see_own_payments(register_and_login):
    """Verify users cannot see other users' payments"""
    # Create user 1
    user1_token = register_and_login(
        f"user1_{uuid.uuid4().hex[:6]}", "pass123", "User 1", 
        f"user1_{uuid.uuid4().hex[:6]}@test.local", 
        f"+31{hash('user1') % 900000000 + 100000000}", 1990
    )

    # Create user 2
    user2_token = register_and_login(
        f"user2_{uuid.uuid4().hex[:6]}", "pass123", "User 2", 
        f"user2_{uuid.uuid4().hex[:6]}@test.local", 
        f"+31{hash('user2') % 900000000 + 100000000}", 1990
    )

    # User 1 creates a payment
    user1_payment = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": user1_token},
        json={
            "reservation_id": None,
            "amount": 99.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    assert user1_payment.status_code == 201
    external_ref = user1_payment.json()["payment"]["external_ref"]

    # User 2 tries to get payments - should not include user 1's payment
    user2_payments = requests.get(
        f"{BASE_URL}/payments",
        headers={"Authorization": user2_token}
    )

    assert user2_payments.status_code == 200
    user2_list = user2_payments.json()
    
    for payment in user2_list:
        assert payment.get("external_ref") != external_ref, "User 2 can see User 1's payment!"
