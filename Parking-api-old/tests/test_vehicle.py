# tests/test_vehicles.py
import requests


def login_driver(api_server):
    requests.post(f"{api_server}/register", json={"username": "driver", "password": "pw", "name": "Driver"})
    login = requests.post(f"{api_server}/login", json={"username": "driver", "password": "pw"})
    return login.json()["session_token"]


def test_vehicle_crud(api_server):
    token = login_driver(api_server)

    # Create
    res = requests.post(
        f"{api_server}/vehicles",
        headers={"Authorization": token},
        json={"name": "My Car", "license_plate": "DRI-123"},
    )
    assert res.status_code == 201

    # List
    res2 = requests.get(f"{api_server}/vehicles", headers={"Authorization": token})
    data = res2.json()
    assert "DRI123" in data

    # Delete
    res3 = requests.delete(f"{api_server}/vehicles/DRI123", headers={"Authorization": token})
    assert res3.status_code == 200