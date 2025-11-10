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
        # Register user (ignore if already exists)
        requests.post(f"{BASE_URL}/register", json={
            "username": username,
            "password": password,
            "name": name,
            "email": email,
            "phone": num,
            "role": role
        })

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
    
    # Load existing users or create new list
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
    token = login_admin()
    headers = {"Authorization": token}

    lot_data = {
        "name": "Central Garage",
        "location": "Downtown",
        "capacity": 100
    }

    res = requests.post(f"{BASE_URL}/parking-lots", json=lot_data, headers=headers)
    assert res.status_code in (200, 201), f"Failed to create parking lot: {res.text}"

    res_get = requests.get(f"{BASE_URL}/parking-lots", headers=headers)
    assert res_get.status_code == 200, f"Failed to fetch parking lots: {res_get.text}"
    lots = res_get.json()
    assert isinstance(lots, dict)
    assert any(lot.get("name") == "Central Garage" for lot in lots.values())


def test_non_admin_cannot_create_parkinglot(register_and_login):
    token = register_and_login("bob", "securepass", "Bob", "bob@gmail.com", "+3129384985")
    headers = {"Authorization": token}
    res = requests.post(f"{BASE_URL}/parking-lots", json={
        "name": "Bob’s Secret Lot",
        "location": "Nowhere",
        "capacity": 1 }, headers=headers) 
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
