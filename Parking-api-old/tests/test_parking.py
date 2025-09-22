# tests/test_parking.py
import requests


def make_admin(api_server):
    requests.post(
        f"{api_server}/register", json={"username": "admin", "password": "root", "name": "Boss"}
    )
    res = requests.post(f"{api_server}/login", json={"username": "admin", "password": "root"})
    return res.json()["session_token"]


def test_create_parking_lot_admin_only(api_server):
    admin_token = make_admin(api_server)

    # Create as admin
    res = requests.post(
        f"{api_server}/parking-lots",
        headers={"Authorization": admin_token},
        json={"name": "Lot A", "location": "Downtown", "tariff": 2.5, "daytariff": 20, "reserved": 0},
    )
    assert res.status_code == 201

    # Create as non-admin
    requests.post(
        f"{api_server}/register",
        json={"username": "bob", "password": "foo", "name": "Bob"},
    )
    login = requests.post(f"{api_server}/login", json={"username": "bob", "password": "foo"})
    token = login.json()["session_token"]

    res2 = requests.post(
        f"{api_server}/parking-lots",
        headers={"Authorization": token},
        json={"name": "Lot B", "location": "Uptown"},
    )
    assert res2.status_code == 403