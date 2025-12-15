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
