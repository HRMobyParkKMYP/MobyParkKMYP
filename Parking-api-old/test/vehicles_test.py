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

def add_mock_vehicle_for_user(user_id, license_plate="MOCK-123", make="Renault"):
    # Laad de voertuigen
    with open("data/vehicles.json", "r") as f:
        vehicles = json.load(f)

    # Voeg het voertuig toe
    vehicles.append({
        "id": str(len(vehicles)+1),
        "user_id": user_id,
        "license_plate": license_plate,
        "make": make,
        "model": "Clio",
        "color": "Red",
        "year": 2025,
        "created_at": "2025-01-01"
    })

    # Sla terug op
    with open("data/vehicles.json", "w") as f:
        json.dump(vehicles, f)
    
    return license_plate

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
    vehicle = add_mock_vehicle_for_user(token, license_plate="MOCK-123", make="Renault")

    vehicle_id = vehicle["id"]

    res = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/entry",
                        headers={"Authorization": token, "Content-Type": "application/json"},
                        json={"parkinglot": "1"})
    print("Test 1 Response:", res.status_code, res.text)
    assert res.status_code == 200
    assert "Accepted" in res.text

def test_vehicle_entry_invalid_token():
    # 2. Ongeldig token
    vehicle_id = "ABC-123"
    res = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/entry",
                        headers={"Authorization": "invalid_token", "Content-Type": "application/json"},
                        json={"parkinglot": "1"})
    print("Test 2 Response:", res.status_code, res.text)
    assert res.status_code == 401
    assert "Unauthorized" in res.text

def test_vehicle_entry_nonexistent_vehicle(register_and_login):
    # 3. Entry van een voertuig dat niet bestaat bij gebruiker
    token = register_and_login("piet", "geheim", "Piet Pieters")
    vehicle_id = "NONEXISTENT-999"
    res = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/entry",
                        headers={"Authorization": token, "Content-Type": "application/json"},
                        json={"parkinglot": "1"})
    print("Test 3 Response:", res.status_code, res.text)
    assert res.status_code == 401
    assert "Vehicle does not exist" in res.text

def test_vehicle_entry_missing_field(register_and_login):
    # 4. Entry met ontbrekend verplichte veld
    token = register_and_login("klaas", "geheim", "Klaas Bakker")
    vehicle_id = "ABC-123"
    res = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/entry",
                        headers={"Authorization": token, "Content-Type": "application/json"},
                        json={})  # geen parkinglot
    print("Test 4 Response:", res.status_code, res.text)
    assert res.status_code == 401
    assert "Require field missing" in res.text