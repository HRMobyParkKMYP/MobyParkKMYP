# tests/test_payments.py
import requests


def login_payer(api_server):
    requests.post(f"{api_server}/register", json={"username": "payer", "password": "pw", "name": "Payy"})
    login = requests.post(f"{api_server}/login", json={"username": "payer", "password": "pw"})
    return login.json()["session_token"]


def test_make_payment(api_server):
    token = login_payer(api_server)

    res = requests.post(
        f"{api_server}/payments",
        headers={"Authorization": token},
        json={"transaction": "tx1", "amount": 50},
    )
    assert res.status_code == 201

    payments = requests.get(f"{api_server}/payments", headers={"Authorization": token})
    assert any(p["transaction"] == "tx1" for p in payments.json())