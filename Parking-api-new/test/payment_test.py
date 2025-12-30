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
    token_admin = get_admin_token()
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
