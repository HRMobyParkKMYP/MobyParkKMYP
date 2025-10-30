import pytest
import requests
import json

BASE_URL = "http://localhost:8000"

@pytest.fixture
def register_and_login():
    def _register_and_login(username, password, name):
        # Register user (ignore if already exists)
        requests.post(f"{BASE_URL}/register", json={
            "username": username,
            "password": password,
            "name": name
        })

        # Login to get session token
        res = requests.post(f"{BASE_URL}/login", json={
            "username": username,
            "password": password
        })
        assert res.status_code == 200, f"Login failed for {username}: {res.text}"
        return res.json().get("session_token")
    return _register_and_login


#[{"id": "1", "user_id": "1", "license_plate": "76-KQQ-7", "make": "Peugeot", "model": "308", "color": "Brown", "year": 2024, "created_at": "2024-08-13"},


#POST /vehicles tests
def test_create_vehicle_success(register_and_login):
    #1. Maak een voertuig aan dat nog niet bestaat bij de user
    token = register_and_login("jan", "geheim", "Jan Jansen")

    res = requests.post(f"{BASE_URL}/vehicles",
                        headers={"Authorization": token, "Content-Type": "application/json"},
                        json={"name": "Peugeot 308", "license_plate": "ABC-123"})

    print("\n[TEST 1 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 201
    assert "Success" in res.text


def test_create_duplicate_vehicle_same_user(register_and_login):
    #2. Maak een voertuig aan dat al bestaat bij dezelfde gebruiker
    token = register_and_login("jan", "geheim", "Jan Jansen")

    # Eerste keer aanmaken
    requests.post(f"{BASE_URL}/vehicles",
                  headers={"Authorization": token},
                  json={"name": "VW Golf", "license_plate": "XYZ-999"})

    # Tweede keer zelfde kenteken
    res = requests.post(f"{BASE_URL}/vehicles",
                        headers={"Authorization": token},
                        json={"name": "VW Golf", "license_plate": "XYZ-999"})

    print("\n[TEST 2 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 401
    assert "Vehicle already exists" in res.text


def test_create_vehicle_missing_field(register_and_login):
    #3. Maak een voertuig aan met ontbrekende verplichte velden
    token = register_and_login("piet", "geheim", "Piet Pieters")

    res = requests.post(f"{BASE_URL}/vehicles",
                        headers={"Authorization": token},
                        json={"name": "Ford Fiesta"})  # geen license_plate

    print("\n[TEST 3 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 401
    assert "Require field missing" in res.text


def test_create_vehicle_invalid_token():
    #4. Maak een voertuig aan zonder geldig sessie-token
    res = requests.post(f"{BASE_URL}/vehicles",
                        headers={"Authorization": "invalid_token"},
                        json={"name": "Tesla Model 3", "license_plate": "TES-333"})

    print("\n[TEST 4 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 401
    assert "Unauthorized" in res.text


def test_create_vehicle_different_user(register_and_login):
    #5. Zelfde voertuig als test 1, maar bij een andere gebruiker
    token1 = register_and_login("jan", "geheim", "Jan Jansen")
    requests.post(f"{BASE_URL}/vehicles",
                  headers={"Authorization": token1},
                  json={"name": "Opel Astra", "license_plate": "AAA-111"})

    token2 = register_and_login("klaas", "geheim", "Klaas Bakker")
    res = requests.post(f"{BASE_URL}/vehicles",
                        headers={"Authorization": token2},
                        json={"name": "Opel Astra", "license_plate": "AAA-111"})

    print("\n[TEST 5 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 201
    assert "Success" in res.text

#/POST /vehicles/ tests
def test_vehicle_entry_success(register_and_login):
    # 1. Succesvolle entry van bestaand voertuig
    token = register_and_login("jan", "geheim", "Jan Jansen")

    # Eerst een voertuig aanmaken
    v_res = requests.post(f"{BASE_URL}/vehicles",
                          headers={"Authorization": token},
                          json={"name": "Peugeot 308", "license_plate": "ENTRY-111"})
    assert v_res.status_code == 201, f"Failed to create vehicle: {v_res.text}"

    vehicles = requests.get(f"{BASE_URL}/vehicles",
                            headers={"Authorization": token}).json()
    vehicle_id = next(v["id"] for v in vehicles if v["license_plate"] == "ENTRY-111")

    # Entry aanmaken
    e_res = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/entry",
                          headers={"Authorization": token},
                          json={"parkinglot": "1"})

    print("\n[ENTRY TEST 1 RESPONSE]", e_res.status_code, e_res.text)
    assert e_res.status_code == 200
    assert "Accepted" in e_res.text

def test_vehicle_entry_invalid_token():
    # 2. Ongeldig token
    res = requests.post(f"{BASE_URL}/vehicles/1/entry",
                        headers={"Authorization": "invalid_token"},
                        json={"parkinglot": "1"})

    print("\n[ENTRY TEST 2 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 401
    assert "Unauthorized" in res.text

def test_vehicle_entry_nonexistent_vehicle(register_and_login):
    # 3. Entry van een voertuig dat niet bestaat bij gebruiker
    token = register_and_login("piet", "geheim", "Piet Pieters")

    res = requests.post(f"{BASE_URL}/vehicles/999/entry",
                        headers={"Authorization": token},
                        json={"parkinglot": "1"})

    print("\n[ENTRY TEST 3 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 401
    assert "Vehicle does not exist" in res.text

def test_vehicle_entry_missing_field(register_and_login):
    # 4. Entry met ontbrekend verplichte veld
    token = register_and_login("klaas", "geheim", "Klaas Bakker")

    # Eerst voertuig aanmaken
    v_res = requests.post(f"{BASE_URL}/vehicles",
                          headers={"Authorization": token},
                          json={"name": "Fiat 500", "license_plate": "MISS-777"})
    assert v_res.status_code == 201
    vehicle_id = v_res.json().get("id") or "1"

    # Entry zonder 'parkinglot'
    res = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/entry",
                        headers={"Authorization": token},
                        json={})

    print("\n[ENTRY TEST 4 RESPONSE]", res.status_code, res.text)
    assert res.status_code == 401
    assert "Require field missing" in res.text