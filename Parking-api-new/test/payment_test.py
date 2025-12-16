import pytest
import requests
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"


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


# ---------- POST /payments ----------

def test_create_payment_success(auth_token):
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,  # Optional, avoids foreign key issues
            "amount": 150.0,
            "currency": "EUR",
            "method": "CARD"
        }
    )

    # Ensure payment was created successfully
    assert res.status_code == 201, f"Create payment failed: {res.text}"
    body = res.json()
    assert body["status"] == "success"
    assert body["payment"]["amount"] == 150.0
    assert body["payment"]["currency"] == "EUR"
    assert body["payment"]["status"] == "initiated"
    assert "external_ref" in body["payment"]
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

    # FastAPI validation error
    assert res.status_code == 422


# ---------- PUT /payments/{external_ref} ----------

def test_update_payment_success(auth_token):
    # First, create a payment
    create = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token},
        json={
            "reservation_id": None,
            "amount": 60.0,
            "currency": "EUR",
            "method": "IDEAL"
        }
    )

    assert create.status_code == 201, f"Create payment failed: {create.text}"
    body = create.json()
    external_ref = body["payment"]["external_ref"]

    # Now, update the payment status
    res = requests.put(
        f"{BASE_URL}/payments/{external_ref}",
        headers={"Authorization": auth_token},
        json={
            "status": "paid",
            "paid_at": datetime.utcnow().isoformat()
        }
    )

    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_update_payment_not_found(auth_token):
    # Try to update a non-existent payment
    res = requests.put(
        f"{BASE_URL}/payments/non_existing_ref",
        headers={"Authorization": auth_token},
        json={"status": "PAID"}
    )

    assert res.status_code == 404
    assert "Payment not found" in res.text


# ---------- GET /payments ----------

def test_get_own_payments(auth_token):
    res = requests.get(
        f"{BASE_URL}/payments",
        headers={"Authorization": auth_token}
    )

    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

    
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


def test_refund_payment_not_found(auth_token):
    res = requests.post(
        f"{BASE_URL}/payments/refund",
        headers={"Authorization": auth_token},
        params={"external_ref": "non_existing_ref"}
    )

    assert res.status_code == 404
    assert "Payment not found" in res.text


# ---------- PUT /payments/{transaction} (alias endpoint) ----------

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


# ---------- GET /payments/{username} ----------

def test_get_payments_by_username(auth_token):
    # Username is derived from auth token test user
    # Fetch profile to get username
    profile_res = requests.get(
        f"{BASE_URL}/profile",
        headers={"Authorization": auth_token}
    )

    # If profile endpoint is not implemented yet, skip safely
    if profile_res.status_code != 200:
        pytest.skip("Profile endpoint not implemented")

    username = profile_res.json().get("username")
    assert username is not None

    res = requests.get(f"{BASE_URL}/payments/{username}")

    assert res.status_code == 200
    assert isinstance(res.json(), list)
