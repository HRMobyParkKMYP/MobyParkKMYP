import pytest
import requests
import json
import os
import hashlib
import datetime

BASE_URL = "http://localhost:8000"

def _data_users_path():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, "api", "data", "users.json")
    
@pytest.fixture
def register_and_login():
    def _register_and_login(username, password, name, email, num, role="USER"):
        # Register user
        reg_res = requests.post(f"{BASE_URL}/register", json={
            "username": username,
            "password": password,
            "name": name,
            "email": email,
            "phone": num,
            "birth_year": 1990,
            "role": role
        })
        # Allow 200/201 for success, or ignore if user already exists (409)
        assert reg_res.status_code in (200, 201, 409), f"Registration failed: {reg_res.text}"

        # Login to get session token
        res = requests.post(f"{BASE_URL}/login", json={
            "username": username,
            "password": password
        })
        assert res.status_code == 200, f"Login failed for {username}: {res.text}"
        return res.json().get("session_token")
    return _register_and_login

def add_admin():
    path = _data_users_path()
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            users = json.load(f)
            if not isinstance(users, list):
                users = []
    except FileNotFoundError:
        users = []
    
    admin_username = "admin_user"
    admin_password = "securepass"
    hashed = hashlib.md5(admin_password.encode()).hexdigest()
    
    # If already exists, skip
    if any(u.get("username") == admin_username for u in users):
        print("Admin already exists in users.json.")
        return
    
    new_admin = {
        "id": str(len(users) + 1),
        "username": admin_username,
        "password": hashed,
        "name": "Admin User",
        "email": "admin@example.local",
        "phone": "+0000000000",
        "role": "ADMIN",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
        "birth_year": 1980,
        "active": True
    }
    
    users.append(new_admin)
    
    # Write updated list back to file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    
    print(f"Admin user '{admin_username}' added successfully.")


def login_admin():
    """Logs in using the pre-existing admin account."""
    res = requests.post(f"{BASE_URL}/login", json={
        "username": "admin_user",
        "password": "securepass"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    data = res.json()
    assert "session_token" in data, f"No session_token in response: {data}"
    return data["session_token"]


def test_admin_can_create_and_get_parkinglot():
    add_admin()

    token = login_admin()
    headers = {"Authorization": token}

    lot_data = {
        "name": "Central Garage",
        "location": "Downtown",
        "capacity": 100
    }

    res = requests.post(f"{BASE_URL}/parking-lots/", json=lot_data, headers=headers)    
    assert res.status_code in (200, 201), f"Failed to create parking lot: {res.text}"

    res_get = requests.get(f"{BASE_URL}/parking-lots/", headers=headers)
    assert res_get.status_code == 200, f"Failed to fetch parking lots: {res_get.text}"
    lots = res_get.json()
    assert isinstance(lots, dict)
    assert any(lot.get("name") == "Central Garage" for lot in lots.values())

def test_admin_can_update_parkinglot_capacity():
    add_admin()
    token = login_admin()
    headers = {"Authorization": token}
    
    # Create a parking lot first
    lot_data = {"name": "Test Lot", "location": "Test", "capacity": 100}
    requests.post(f"{BASE_URL}/parking-lots/", json=lot_data, headers=headers)
    
    # Now update it
    update_data = {"capacity": 120}
    res = requests.put(f"{BASE_URL}/parking-lots/1", json=update_data, headers=headers)
    assert res.status_code in (200, 204), f"Failed to update: {res.text}"

def test_admin_can_delete_parkinglot():
    add_admin()
    token = login_admin()
    headers = {"Authorization": token}
    
    # Create a parking lot first
    lot_data = {"name": "Test Lot", "location": "Test", "capacity": 100}
    requests.post(f"{BASE_URL}/parking-lots/", json=lot_data, headers=headers)
    
    # Now delete it
    res = requests.delete(f"{BASE_URL}/parking-lots/1", headers=headers)
    assert res.status_code in (200, 204), f"Failed to delete: {res.text}"

def test_create_parkinglot_missing_fields_fails():
    add_admin()
    token = login_admin()
    headers = {"Authorization": token}
    res = requests.post(f"{BASE_URL}/parking-lots/", json={"name": "Bad Lot"}, headers=headers)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"


def test_non_admin_cannot_create_parkinglot(register_and_login):
    token = register_and_login("bob", "securepass", "Bob", "bob@gmail.com", "+3129384985")
    headers = {"Authorization": token}
    res = requests.post(f"{BASE_URL}/parking-lots", json={
        "name": "Bob’s Secret Lot",
        "location": "Nowhere",
        "capacity": 1 }, headers=headers) 
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
