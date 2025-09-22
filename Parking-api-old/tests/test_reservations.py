# tests/test_reservations.py
import requests


def setup_user_and_lot(api_server):
    # normal user alice
    requests.post(f"{api_server}/register", json={"username": "alice", "password": "pw", "name": "Alice"})
    login = requests.post(f"{api_server}/login", json={"username": "alice", "password": "pw"})
    user_token = login.json()["session_token"]

    # admin + lot
    requests.post(f"{api_server}/register", json={"username": "admin2", "password": "pw", "name": "Admin"})
    alogin = requests.post(f"{api_server}/login", json={"username": "admin2", "password": "pw"})
    admin_token = alogin.json()["session_token"]

    requests.post(
        f"{api_server}/parking-lots",
        headers={"Authorization": admin_token},
        json={"name": "Lot 1", "location": "TestLoc", "tariff": 1, "daytariff": 10, "reserved": 0},
    )

    return user_token


def test_create_and_delete_reservation(api_server):
    token = setup_user_and_lot(api_server)

    res = requests.post(
        f"{api_server}/reservations",
        headers={"Authorization": token},
        json={
            "licenseplate": "ABC-123",
            "startdate": "2025-09-22 12:00:00",
            "enddate": "2025-09-22 18:00:00",
            "parkinglot": "1",
        },
    )
    assert res.status_code == 201
    rid = res.json()["reservation"]["id"]

    get_res = requests.get(f"{api_server}/reservations/{rid}", headers={"Authorization": token})
    assert get_res.status_code == 200

    del_res = requests.delete(f"{api_server}/reservations/{rid}", headers={"Authorization": token})
    assert del_res.status_code == 200