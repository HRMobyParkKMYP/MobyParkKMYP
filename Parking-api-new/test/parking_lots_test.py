import pytest
import requests
import uuid
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.utils import database_utils, auth_utils

BASE_URL = "http://localhost:8000"

# Helper functions
def register_user(username, password, name, email, phone, birth_year):
    """Register a new user"""
    data = {
        "username": username,
        "password": password,
        "name": name,
        "email": email,
        "phone": phone,
        "birth_year": birth_year
    }
    return requests.post(f"{BASE_URL}/register", json=data)

def login_user(username, password):
    """Login user and return session token"""
    res = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    if res.status_code == 200:
        return res.json().get("session_token")
    return None

def get_admin_token():
    """Create admin directly in DB using create_admin_user(). Return session token."""
    unique_id = uuid.uuid4().hex[:6]
    username = f"admin_{unique_id}"
    email = f"admin_{unique_id}@test.com"
    phone = f"+3160{unique_id}"

    hashed_pw, salt = auth_utils.hash_password_bcrypt("admin_pw")

    # Create admin directly in DB
    database_utils.create_admin_user(
        username=username,
        password_hash=hashed_pw,
        name="Admin User",
        email=email,
        phone=phone,
        birth_year=1980,
        role="ADMIN",
        hash_v="bcrypt",
        salt=salt
    )

    # Login normally to get session token
    return login_user(username, "admin_pw")

def get_user_token():
    """Get regular user token - creates unique user each time"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"user_{unique_id}"
    email = f"user_{unique_id}@test.com"
    phone = f"+3161{unique_id}"
    
    register_user(username, "user_pw", "Regular User", email, phone, 1990)
    return login_user(username, "user_pw")

# POST /parking-lots tests
def test_create_parking_lot_success():
    # 1. Succesvolle aanmaak parkeerplaats
    admin_token = get_admin_token()
    assert admin_token is not None, "Admin token creation failed"
    
    lot_data = {
        "name": "Downtown Garage",
        "location": "Downtown",
        "address": "456 Oak Ave",
        "capacity": 100,
        "tariff": 3.5,
        "day_tariff": 20.0,
        "lat": 52.5200,
        "lng": 13.4050
    }
    res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    assert res.status_code in (200, 201), f"Status: {res.status_code}, Response: {res.text}"
    data = res.json()
    assert "lot_id" in data
    assert data["parking_lot"]["name"] == "Downtown Garage"

def test_create_parking_lot_missing_token():
    # 2. Aanmaak parkeerplaats zonder token
    lot_data = {
        "name": "Test Lot",
        "address": "123 Main St",
        "capacity": 50,
        "tariff": 5.0
    }
    res = requests.post(f"{BASE_URL}/parking-lots", json=lot_data)
    assert res.status_code == 401
    assert b"missing token" in res.content or b"Unauthorized" in res.content

def test_create_parking_lot_invalid_token():
    # 3. Aanmaak parkeerplaats met ongeldig token
    lot_data = {
        "name": "Test Lot",
        "address": "123 Main St",
        "capacity": 50,
        "tariff": 5.0
    }
    res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": "invalid_token"})
    assert res.status_code == 401

def test_create_parking_lot_non_admin():
    # 4. Aanmaak parkeerplaats door non-admin user
    user_token = get_user_token()
    
    lot_data = {
        "name": "Test Lot",
        "address": "123 Main St",
        "capacity": 50,
        "tariff": 5.0
    }
    res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": user_token})
    assert res.status_code == 403
    assert b"admin" in res.content or b"Access denied" in res.content

def test_create_parking_lot_missing_required_fields():
    # 5. Aanmaak parkeerplaats met ontbrekende velden
    admin_token = get_admin_token()
    
    lot_data = {
        "name": "Incomplete Lot"
        # Missing required fields: address, capacity, tariff
    }
    res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    assert res.status_code in (422, 400)

# GET /parking-lots tests
def test_get_all_parking_lots_success():
    # 1. Ophalen alle parkeerplaatsen
    res = requests.get(f"{BASE_URL}/parking-lots")
    assert res.status_code == 200, f"Status: {res.status_code}, Response: {res.text}"
    data = res.json()
    assert "parking_lots" in data
    assert isinstance(data["parking_lots"], list)

def test_get_all_parking_lots_contains_required_fields():
    # 2. Alle parkeerplaatsen hebben vereiste velden
    res = requests.get(f"{BASE_URL}/parking-lots")
    assert res.status_code == 200, f"Status: {res.status_code}, Response: {res.text}"
    data = res.json()
    if data["parking_lots"]:  # Als er parkeerplaatsen zijn
        lot = data["parking_lots"][0]
        assert "name" in lot
        assert "capacity" in lot

# GET /parking-lots/{lot_id} tests
def test_get_single_parking_lot_success():
    # 1. Ophalen enkele parkeerplaats
    admin_token = get_admin_token()
    
    # Eerst een parkeerplaats aanmaken
    lot_data = {
        "name": "Test Lot Single",
        "address": "123 Main St",
        "capacity": 50,
        "tariff": 5.0
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        res = requests.get(f"{BASE_URL}/parking-lots/{lot_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Test Lot Single"

def test_get_parking_lot_not_found():
    # 2. Ophalen parkeerplaats die niet bestaat
    res = requests.get(f"{BASE_URL}/parking-lots/99999")
    assert res.status_code == 404
    assert b"not found" in res.content or b"Not found" in res.content

# PUT /parking-lots/{lot_id} tests
def test_update_parking_lot_success():
    # 1. Succesvolle update parkeerplaats
    admin_token = get_admin_token()
    
    # Eerst een parkeerplaats aanmaken
    lot_data = {
        "name": "Original Name",
        "address": "123 Main St",
        "capacity": 50,
        "tariff": 5.0
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        update_data = {"name": "Updated Name", "capacity": 75}
        res = requests.put(f"{BASE_URL}/parking-lots/{lot_id}", 
            json=update_data, 
            headers={"Authorization": admin_token})
        
        assert res.status_code == 200
        assert res.json()["parking_lot"]["name"] == "Updated Name"
        assert res.json()["parking_lot"]["capacity"] == 75

def test_update_parking_lot_not_found():
    # 2. Update parkeerplaats die niet bestaat
    admin_token = get_admin_token()
    assert admin_token is not None
    
    update_data = {"name": "Updated Name"}
    res = requests.put(f"{BASE_URL}/parking-lots/99999", 
        json=update_data, 
        headers={"Authorization": admin_token})
    assert res.status_code == 404, f"Status: {res.status_code}, Response: {res.text}"

def test_update_parking_lot_non_admin():
    # 3. Update parkeerplaats door non-admin user
    user_token = get_user_token()
    
    update_data = {"capacity": 75}
    res = requests.put(f"{BASE_URL}/parking-lots/1", 
        json=update_data, 
        headers={"Authorization": user_token})
    assert res.status_code == 403

def test_update_parking_lot_missing_token():
    # 4. Update parkeerplaats zonder token
    update_data = {"capacity": 75}
    res = requests.put(f"{BASE_URL}/parking-lots/1", json=update_data)
    assert res.status_code == 401

# DELETE /parking-lots/{lot_id} tests
def test_delete_parking_lot_success():
    # 1. Succesvolle delete parkeerplaats
    admin_token = get_admin_token()
    
    # Eerst een parkeerplaats aanmaken
    lot_data = {
        "name": "Lot to Delete",
        "address": "123 Main St",
        "capacity": 50,
        "tariff": 5.0
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        res = requests.delete(f"{BASE_URL}/parking-lots/{lot_id}", 
            headers={"Authorization": admin_token})
        
        assert res.status_code == 200
        assert b"deleted" in res.content.lower()

def test_delete_parking_lot_not_found():
    # 2. Delete parkeerplaats die niet bestaat
    admin_token = get_admin_token()
    assert admin_token is not None
    
    res = requests.delete(f"{BASE_URL}/parking-lots/99999", 
        headers={"Authorization": admin_token})
    assert res.status_code == 404, f"Status: {res.status_code}, Response: {res.text}"

def test_delete_parking_lot_non_admin():
    # 3. Delete parkeerplaats door non-admin user
    user_token = get_user_token()
    
    res = requests.delete(f"{BASE_URL}/parking-lots/1", 
        headers={"Authorization": user_token})
    assert res.status_code == 403

def test_delete_parking_lot_missing_token():
    # 4. Delete parkeerplaats zonder token
    res = requests.delete(f"{BASE_URL}/parking-lots/1")
    assert res.status_code == 401

# POST /parking-lots/{lot_id}/sessions/start tests
def test_start_session_success():
    # 1. Succesvolle start parkeersezie
    admin_token = get_admin_token()
    user_token = get_user_token()
    
    # Eerst een parkeerplaats aanmaken
    lot_data = {
        "name": "Session Test Lot",
        "address": "789 Pine St",
        "capacity": 30,
        "tariff": 2.5
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        session_data = {"licenseplate": "ABC123"}
        res = requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/start", 
            json=session_data, 
            headers={"Authorization": user_token})
        
        assert res.status_code == 200
        assert b"session" in res.content.lower()
        assert b"ABC123" in res.content

def test_start_session_missing_token():
    # 2. Start sessie zonder token
    session_data = {"licenseplate": "ABC123"}
    res = requests.post(f"{BASE_URL}/parking-lots/1/sessions/start", 
        json=session_data)
    assert res.status_code == 401

def test_start_session_invalid_token():
    # 3. Start sessie met ongeldig token
    session_data = {"licenseplate": "ABC123"}
    res = requests.post(f"{BASE_URL}/parking-lots/1/sessions/start", 
        json=session_data, 
        headers={"Authorization": "invalid_token"})
    assert res.status_code == 401

def test_start_session_missing_licenseplate():
    # 4. Start sessie zonder licenseplate
    user_token = get_user_token()
    
    res = requests.post(f"{BASE_URL}/parking-lots/1/sessions/start", 
        json={}, 
        headers={"Authorization": user_token})
    # FastAPI returns 422 for validation errors
    assert res.status_code in (400, 422)

def test_start_session_parking_lot_not_found():
    # 5. Start sessie voor parkeerplaats die niet bestaat
    user_token = get_user_token()
    
    session_data = {"licenseplate": "ABC123"}
    res = requests.post(f"{BASE_URL}/parking-lots/99999/sessions/start", 
        json=session_data, 
        headers={"Authorization": user_token})
    assert res.status_code == 404

def test_start_duplicate_session():
    # 6. Start dubbele sessie voor zelfde kenteken
    admin_token = get_admin_token()
    user_token = get_user_token()
    
    # Eerst een parkeerplaats aanmaken
    lot_data = {
        "name": "Duplicate Session Test",
        "address": "999 Elm St",
        "capacity": 20,
        "tariff": 3.0
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        session_data = {"licenseplate": "XYZ789"}
        requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/start", 
            json=session_data, 
            headers={"Authorization": user_token})
        
        # Probeer dezelfde sessie opnieuw te starten
        res = requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/start", 
            json=session_data, 
            headers={"Authorization": user_token})
        assert res.status_code == 409

# POST /parking-lots/{lot_id}/sessions/stop tests
def test_stop_session_success():
    # 1. Succesvolle stop parkeersezie
    admin_token = get_admin_token()
    user_token = get_user_token()
    
    lot_data = {
        "name": "Stop Session Test",
        "address": "555 Maple St",
        "capacity": 25,
        "tariff": 4.0
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        # Start sessie
        session_data = {"licenseplate": "STOP123"}
        requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/start", 
            json=session_data, 
            headers={"Authorization": user_token})
        
        # Stop sessie
        res = requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/stop", 
            json=session_data, 
            headers={"Authorization": user_token})
        
        assert res.status_code == 200
        assert b"stopped" in res.content.lower()

def test_stop_session_no_active_session():
    # 2. Stop sessie wanneer geen actieve sessie bestaat
    user_token = get_user_token()
    
    session_data = {"licenseplate": "NOACTIVE"}
    res = requests.post(f"{BASE_URL}/parking-lots/1/sessions/stop", 
        json=session_data, 
        headers={"Authorization": user_token})
    assert res.status_code in (404, 500), f"Status: {res.status_code}, Response: {res.text}"

def test_stop_session_missing_token():
    # 3. Stop sessie zonder token
    session_data = {"licenseplate": "ABC123"}
    res = requests.post(f"{BASE_URL}/parking-lots/1/sessions/stop", 
        json=session_data)
    assert res.status_code == 401

# GET /parking-lots/{lot_id}/sessions tests
def test_get_all_sessions_success():
    # 1. Ophalen alle sessies voor parkeerplaats
    admin_token = get_admin_token()
    user_token = get_user_token()
    
    lot_data = {
        "name": "Get Sessions Test",
        "address": "111 Cedar St",
        "capacity": 40,
        "tariff": 2.0
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        res = requests.get(f"{BASE_URL}/parking-lots/{lot_id}/sessions", 
            headers={"Authorization": user_token})
        
        assert res.status_code == 200
        assert b"sessions" in res.content

def test_get_all_sessions_missing_token():
    # 2. Ophalen sessies zonder token
    res = requests.get(f"{BASE_URL}/parking-lots/1/sessions")
    assert res.status_code == 401

def test_get_all_sessions_lot_not_found():
    # 3. Ophalen sessies voor parkeerplaats die niet bestaat
    user_token = get_user_token()
    
    res = requests.get(f"{BASE_URL}/parking-lots/99999/sessions", 
        headers={"Authorization": user_token})
    assert res.status_code == 404

# GET /parking-lots/{lot_id}/sessions/{session_id} tests
def test_get_session_details_success():
    # 1. Ophalen details enkele sessie
    admin_token = get_admin_token()
    user_token = get_user_token()
    
    lot_data = {
        "name": "Session Details Test",
        "address": "222 Birch St",
        "capacity": 35,
        "tariff": 3.5
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        # Start sessie
        session_data = {"licenseplate": "DETAIL1"}
        start_res = requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/start", 
            json=session_data, 
            headers={"Authorization": user_token})
        
        if start_res.status_code == 200:
            session_id = start_res.json()["session"]["id"]
            
            res = requests.get(f"{BASE_URL}/parking-lots/{lot_id}/sessions/{session_id}", 
                headers={"Authorization": user_token})
            
            assert res.status_code == 200
            assert b"DETAIL1" in res.content

def test_get_session_details_not_found():
    # 2. Ophalen sessie details die niet bestaat
    user_token = get_user_token()
    
    res = requests.get(f"{BASE_URL}/parking-lots/1/sessions/99999", 
        headers={"Authorization": user_token})
    assert res.status_code in (404, 500), f"Status: {res.status_code}, Response: {res.text}"

def test_get_session_details_missing_token():
    # 3. Ophalen sessie details zonder token
    res = requests.get(f"{BASE_URL}/parking-lots/1/sessions/1")
    assert res.status_code == 401

# DELETE /parking-lots/{lot_id}/sessions/{session_id} tests
def test_delete_session_success():
    # 1. Succesvolle delete sessie
    admin_token = get_admin_token()
    user_token = get_user_token()
    
    lot_data = {
        "name": "Delete Session Test",
        "address": "333 Spruce St",
        "capacity": 45,
        "tariff": 2.5
    }
    create_res = requests.post(f"{BASE_URL}/parking-lots", 
        json=lot_data, 
        headers={"Authorization": admin_token})
    
    if create_res.status_code in (200, 201):
        lot_id = create_res.json().get("lot_id")
        
        # Start sessie
        session_data = {"licenseplate": "DEL123"}
        start_res = requests.post(f"{BASE_URL}/parking-lots/{lot_id}/sessions/start", 
            json=session_data, 
            headers={"Authorization": user_token})
        
        if start_res.status_code == 200:
            session_id = start_res.json()["session"]["id"]
            
            res = requests.delete(f"{BASE_URL}/parking-lots/{lot_id}/sessions/{session_id}", 
                headers={"Authorization": admin_token})
            
            assert res.status_code == 200
            assert b"deleted" in res.content.lower()

def test_delete_session_non_admin():
    # 2. Delete sessie door non-admin user
    user_token = get_user_token()
    
    res = requests.delete(f"{BASE_URL}/parking-lots/1/sessions/1", 
        headers={"Authorization": user_token})
    assert res.status_code == 403

def test_delete_session_missing_token():
    # 3. Delete sessie zonder token
    res = requests.delete(f"{BASE_URL}/parking-lots/1/sessions/1")
    assert res.status_code == 401

def test_delete_session_not_found():
    # 4. Delete sessie die niet bestaat
    admin_token = get_admin_token()
    assert admin_token is not None
    
    res = requests.delete(f"{BASE_URL}/parking-lots/1/sessions/99999", 
        headers={"Authorization": admin_token})
    assert res.status_code == 404, f"Status: {res.status_code}, Response: {res.text}"