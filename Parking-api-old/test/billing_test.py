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
        reg_res = requests.post(f"{BASE_URL}/register", json={
            "username": username,
            "password": password,
            "name": name,
            "email": email,
            "phone": num,
            "birth_year": 1990,
            "role": role
        })
        assert reg_res.status_code in (200, 201, 409), f"Registration failed: {reg_res.text}"

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

    if any(u.get("username") == admin_username for u in users):
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


def login_admin():
    res = requests.post(f"{BASE_URL}/login", json={
        "username": "admin_user",
        "password": "securepass"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    data = res.json()
    assert "session_token" in data, f"No session_token in response: {data}"
    return data["session_token"]


def test_user_can_get_own_billing(register_and_login):
    token = register_and_login("alice", "test123", "Alice", "alice@test.local", "+3111111111")
    headers = {"Authorization": token}

    res = requests.get(f"{BASE_URL}/billing", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert isinstance(data, list)
    assert all("session" in b for b in data or [])


def test_user_cannot_get_other_user_billing(register_and_login):
    register_and_login("alice", "test123", "Alice", "alice@test.local", "+3111111111")
    token_bob = register_and_login("bob", "test123", "Bob", "bob@test.local", "+3222222222")
    headers = {"Authorization": token_bob}

    res = requests.get(f"{BASE_URL}/billing/alice", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert "Access denied" in res.text


def test_unauthorized_billing_access_fails():
    res = requests.get(f"{BASE_URL}/billing")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "Unauthorized" in res.text


def test_admin_can_get_specific_user_billing(register_and_login):
    add_admin()
    token_admin = login_admin()
    headers = {"Authorization": token_admin}

    register_and_login("charlie", "pass123", "Charlie", "charlie@test.local", "+3333333333")

    res = requests.get(f"{BASE_URL}/billing/charlie", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert all("session" in b and "amount" in b for b in data)


def test_admin_cannot_access_billing_with_invalid_token():
    headers = {"Authorization": "invalid-token-123"}
    res = requests.get(f"{BASE_URL}/billing/anyuser", headers=headers)
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "Unauthorized" in res.text
