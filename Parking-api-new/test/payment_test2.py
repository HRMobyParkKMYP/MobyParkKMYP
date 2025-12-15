import pytest
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

# POST /payments
def test_create_payment_success(register_and_login):
    token = register_and_login("pay1", "pw", "Pay User", "100", "0612345678", 1990)

    tx = f"tx-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": token},
        json={"transaction": tx, "amount": 150}
    )

    print("\n[PAYMENT CREATE]", res.status_code, res.text)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "Success"
    assert body["payment"]["transaction"] == tx


def test_create_payment_missing_field(register_and_login):
    token = register_and_login("pay2", "pw", "Pay User", "101", "0612345679", 1990)

    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": token},
        json={"amount": 100}  # transaction ontbreekt
    )

    assert res.status_code == 422 or res.status_code == 400
    assert "missing" in res.text.lower() or "required" in res.text.lower()


def test_create_payment_invalid_token():
    res = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": "invalid_token"},
        json={"transaction": "tx-invalid", "amount": 50}
    )

    assert res.status_code == 401
    assert "Unauthorized" in res.text


# PUT /payments/{transaction}
def test_update_payment_success(register_and_login):
    token = register_and_login("pay3", "pw", "Updater", "102", "0611111111", 1990)

    tx = f"tx-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    create = requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": token},
        json={"transaction": tx, "amount": 75}
    )
    assert create.status_code == 201

    payment_hash = create.json()["payment"]["hash"]

    update = requests.put(
        f"{BASE_URL}/payments/{tx}",
        headers={"Authorization": token},
        json={
            "t_data": {"paid": True},
            "validation": payment_hash
        }
    )

    print("\n[PAYMENT UPDATE]", update.status_code, update.text)
    assert update.status_code == 200
    assert update.json()["status"] == "Success"


def test_update_payment_invalid_hash(register_and_login):
    token = register_and_login("pay4", "pw", "Updater", "103", "0622222222", 1990)

    tx = f"tx-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": token},
        json={"transaction": tx, "amount": 30}
    )

    update = requests.put(
        f"{BASE_URL}/payments/{tx}",
        headers={"Authorization": token},
        json={
            "t_data": {},
            "validation": "wrong_hash"
        }
    )

    assert update.status_code == 401
    assert "Validation failed" in update.text


# GET /payments
def test_get_own_payments(register_and_login):
    token = register_and_login("pay5", "pw", "Lister", "104", "0633333333", 1990)

    requests.post(
        f"{BASE_URL}/payments",
        headers={"Authorization": token},
        json={"transaction": "tx-list", "amount": 10}
    )

    res = requests.get(
        f"{BASE_URL}/payments",
        headers={"Authorization": token}
    )

    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_payments_unauthorized():
    res = requests.get(f"{BASE_URL}/payments")
    assert res.status_code == 401
    assert "Unauthorized" in res.text


# POST /payments/refund (admin only)
def test_refund_admin_only(register_and_login, register_admin):
    user_token = register_and_login("pay6", "pw", "Normal User", "105", "0644444444", 1990)
    admin_token = register_admin("admin1", "adminpw")

    # gewone gebruiker
    res_user = requests.post(
        f"{BASE_URL}/payments/refund",
        headers={"Authorization": user_token},
        json={"amount": 5}
    )
    assert res_user.status_code == 403

    # admin
    res_admin = requests.post(
        f"{BASE_URL}/payments/refund",
        headers={"Authorization": admin_token},
        json={"amount": 5}
    )
    assert res_admin.status_code == 201
    assert "Success" in res_admin.text
