import pytest
import requests
import json
from storage_utils import load_json, save_data

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

#PUT /vehicles/{id} tests
def test_vehicle_update_success(register_and_login):
    # 1. Succesvolle update van bestaand voertuig
    token = register_and_login("piet", "geheim", "Piet Puk")

    create = requests.post(f"{BASE_URL}/vehicles",
                           headers={"Authorization": token},
                           json={"name": "Toyota Yaris", "license_plate": "PUT-123"})
    assert create.status_code == 201

    vehicles = requests.get(f"{BASE_URL}/vehicles",
                            headers={"Authorization": token}).json()
    vehicle_id = next(v["id"] for v in vehicles if v["license_plate"] == "PUT-123")

    update = requests.put(f"{BASE_URL}/vehicles/{vehicle_id}",
                          headers={"Authorization": token},
                          json={"name": "Toyota Yaris Updated"})
    assert update.status_code == 200
    data = update.json()
    assert data["status"] == "Success"
    assert data["vehicle"]["name"] == "Toyota Yaris Updated"


def test_vehicle_update_not_found(register_and_login):
    # 2. Probeer niet bestaand voertuig te updaten
    token = register_and_login("kees", "geheim", "Kees Koster")

    # Probeer niet bestaand voertuig te updaten
    update = requests.put(f"{BASE_URL}/vehicles/999",
                          headers={"Authorization": token},
                          json={"name": "DoesNotExist"})
    assert update.status_code == 404
    assert "Vehicle not found" in update.text


def test_vehicle_update_missing_field(register_and_login):
    # 3. Update met ontbrekend verplicht veld
    token = register_and_login("klaas", "geheim", "Klaas Klaassen")

    create = requests.post(f"{BASE_URL}/vehicles",
                           headers={"Authorization": token},
                           json={"name": "Mazda 3", "license_plate": "MISSING-123"})
    assert create.status_code == 201

    vehicles = requests.get(f"{BASE_URL}/vehicles",
                            headers={"Authorization": token}).json()
    vehicle_id = next(v["id"] for v in vehicles if v["license_plate"] == "MISSING-123")

    update = requests.put(f"{BASE_URL}/vehicles/{vehicle_id}",
                          headers={"Authorization": token},
                          json={})
    assert update.status_code == 400
    assert "Require field missing" in update.text

#DELETE /vehicles/{id} tests
def test_vehicle_delete_success(register_and_login):
    # 1. Succesvolle verwijdering van bestaand voertuig
    token = register_and_login("klaas", "geheim", "Klaas Klinkhamer")

    create = requests.post(f"{BASE_URL}/vehicles",
                           headers={"Authorization": token},
                           json={"name": "Opel Astra", "license_plate": "DEL-123"})
    assert create.status_code == 201

    vehicles = requests.get(f"{BASE_URL}/vehicles",
                            headers={"Authorization": token}).json()
    vehicle_id = next(v["id"] for v in vehicles if v["license_plate"] == "DEL-123")

    delete = requests.delete(f"{BASE_URL}/vehicles/{vehicle_id}",
                             headers={"Authorization": token})
    assert delete.status_code == 200
    data = delete.json()
    assert data["status"] == "Deleted"

    vehicles_after = requests.get(f"{BASE_URL}/vehicles",
                                  headers={"Authorization": token}).json()
    assert all(v["id"] != vehicle_id for v in vehicles_after)

def test_vehicle_delete_not_found(register_and_login):
    # 2. Probeer niet bestaand voertuig te verwijderen
    token = register_and_login("hans", "geheim", "Hans Worst")

    delete = requests.delete(f"{BASE_URL}/vehicles/999",
                             headers={"Authorization": token})
    assert delete.status_code in (403, 404)

def test_vehicle_delete_other_user_forbidden(register_and_login):
    # 3. Probeer voertuig van andere gebruiker te verwijderen
    # User 1 maakt voertuig aan
    token1 = register_and_login("sarah", "geheim", "Sarah Smits")
    create = requests.post(f"{BASE_URL}/vehicles",
                           headers={"Authorization": token1},
                           json={"name": "Fiat Panda", "license_plate": "DEL-999"})
    assert create.status_code == 201

    vehicles1 = requests.get(f"{BASE_URL}/vehicles",
                             headers={"Authorization": token1}).json()
    vehicle_id = next(v["id"] for v in vehicles1 if v["license_plate"] == "DEL-999")

    # User 2 probeert te verwijderen
    token2 = register_and_login("mark", "geheim", "Mark Visser")
    delete = requests.delete(f"{BASE_URL}/vehicles/{vehicle_id}",
                             headers={"Authorization": token2})
    assert delete.status_code in (403, 404)

#GET /vehicles tests
def test_get_vehicles_success(register_and_login):
    # 1. Succesvolle opvraging van voertuigenlijst
    token = register_and_login("emma", "geheim", "Emma de Vries")

    # Voeg voertuigen toe
    requests.post(f"{BASE_URL}/vehicles",
                  headers={"Authorization": token},
                  json={"name": "Honda Civic", "license_plate": "GET-123"})
    requests.post(f"{BASE_URL}/vehicles",
                  headers={"Authorization": token},
                  json={"name": "Audi A3", "license_plate": "GET-456"})

    res = requests.get(f"{BASE_URL}/vehicles",
                       headers={"Authorization": token})

    assert res.status_code == 200
    vehicles = res.json()
    assert any(v["license_plate"] == "GET-123" for v in vehicles)
    assert any(v["license_plate"] == "GET-456" for v in vehicles)

def test_get_vehicle_reservations_empty(register_and_login):
    # 2. Opvraging reserveringen voor voertuig zonder reserveringen
    token = register_and_login("resuser", "pw", "Res Gebruiker")

    create = requests.post(f"{BASE_URL}/vehicles",
                           headers={"Authorization": token},
                           json={"name": "Peugeot 208", "license_plate": "RES-001"})
    assert create.status_code == 201

    vehicles = requests.get(f"{BASE_URL}/vehicles",
                            headers={"Authorization": token}).json()
    vid = vehicles[0]["id"]

    res = requests.get(f"{BASE_URL}/vehicles/{vid}/reservations",
                       headers={"Authorization": token})
    assert res.status_code == 200
    assert res.json() == []

def test_get_vehicle_history_empty(register_and_login):
    # 3. Opvraging geschiedenis voor voertuig zonder geschiedenis
    token = register_and_login("histuser", "pw", "History User")

    create = requests.post(f"{BASE_URL}/vehicles",
                           headers={"Authorization": token},
                           json={"name": "VW Golf", "license_plate": "HIST-001"})
    assert create.status_code == 201

    vehicles = requests.get(f"{BASE_URL}/vehicles",
                            headers={"Authorization": token}).json()
    vid = vehicles[0]["id"]

    res = requests.get(f"{BASE_URL}/vehicles/{vid}/history",
                       headers={"Authorization": token})
    assert res.status_code == 200
    assert res.json() == []
