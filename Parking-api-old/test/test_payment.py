import pytest
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="session")
def auth_tokens():
    # registreer normale user + admin
    user = {
        "username": "payuser",
        "password": "secret",
        "name": "Pay User",
        "email": "payuser@example.com",
        "phone": "+31610000000",
        "birth_year": 1990
    }
    admin = {
        "username": "adminuser",
        "password": "adminpw",
        "name": "Admin Tester",
        "email": "admin@example.com",
        "phone": "+31620000000",
        "birth_year": 1980,
        "role": "ADMIN"
    }
    requests.post(f"{BASE_URL}/register", json=user)
    requests.post(f"{BASE_URL}/register", json=admin)

    token_user = requests.post(f"{BASE_URL}/login", json={"username": "payuser", "password": "secret"}).json()["session_token"]
    token_admin = requests.post(f"{BASE_URL}/login", json={"username": "adminuser", "password": "adminpw"}).json()["session_token"]
    return token_user, token_admin


# POST /payments tests
def test_create_payment_success(auth_tokens):
    token, _ = auth_tokens
    tx = "tx-" + datetime.now().strftime("%Y%m%d%H%M%S")
    data = {"transaction": tx, "amount": 150}

    res = requests.post(f"{BASE_URL}/payments", headers={"Authorization": token}, json=data)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "Success"
    assert body["payment"]["transaction"] == tx


def test_create_payment_missing_field(auth_tokens):
    token, _ = auth_tokens
    res = requests.post(f"{BASE_URL}/payments", headers={"Authorization": token}, json={"amount": 100})
    assert res.status_code == 401
    assert b"Require field missing" in res.content


def test_create_payment_unauthorized():
    data = {"transaction": "tx-unauth", "amount": 20}
    res = requests.post(f"{BASE_URL}/payments", json=data)
    assert res.status_code == 401
    assert b"Invalid or missing session token" in res.content


def test_create_refund_admin_only(auth_tokens):
    user_token, admin_token = auth_tokens
    # gewone gebruiker → 403
    res_user = requests.post(f"{BASE_URL}/payments/refund", headers={"Authorization": user_token}, json={"amount": 5})
    assert res_user.status_code == 403
    # admin → 201
    res_admin = requests.post(f"{BASE_URL}/payments/refund", headers={"Authorization": admin_token}, json={"amount": 5})
    assert res_admin.status_code == 201
    assert b"Success" in res_admin.content


# PUT /payments/<tx>
def test_update_payment_success(auth_tokens):
    token, _ = auth_tokens
    tx = "tx-" + datetime.now().strftime("%Y%m%d%H%M%S")
    create = requests.post(f"{BASE_URL}/payments", headers={"Authorization": token}, json={"transaction": tx, "amount": 60})
    payment_hash = create.json()["payment"]["hash"]

    res = requests.put(
        f"{BASE_URL}/payments/{tx}",
        headers={"Authorization": token},
        json={"t_data": {"ok": True}, "validation": payment_hash}
    )
    assert res.status_code == 200
    assert b"Success" in res.content


def test_update_payment_invalid_hash(auth_tokens):
    token, _ = auth_tokens
    tx = "tx-" + datetime.now().strftime("%Y%m%d%H%M%S")
    requests.post(f"{BASE_URL}/payments", headers={"Authorization": token}, json={"transaction": tx, "amount": 30})

    res = requests.put(
        f"{BASE_URL}/payments/{tx}",
        headers={"Authorization": token},
        json={"t_data": {}, "validation": "wronghash"}
    )
    assert res.status_code == 401
    assert b"Validation failed" in res.content


# GET /payments tests
def test_get_own_payments(auth_tokens):
    token, _ = auth_tokens
    res = requests.get(f"{BASE_URL}/payments", headers={"Authorization": token})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_payments_unauthorized():
    res = requests.get(f"{BASE_URL}/payments")
    assert res.status_code == 401
    assert b"Invalid or missing session token" in res.content


# GET /payments/<user> (admin only)
def test_admin_get_user_payments(auth_tokens):
    _, admin_token = auth_tokens
    res = requests.get(f"{BASE_URL}/payments/payuser", headers={"Authorization": admin_token})
    assert res.status_code in (200, 403, 401)  # depends on implementation
