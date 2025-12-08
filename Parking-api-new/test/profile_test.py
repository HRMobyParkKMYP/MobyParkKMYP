import pytest
import requests
import sqlite3
import os
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

def get_test_db_path():
    """Test database path"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(test_dir, '..', 'api')
    return os.path.join(api_dir, 'data', 'parking_test.sqlite3')

@pytest.fixture(scope="session", autouse=True)
def ensure_test_mode_env():
    """
    Make sure the server (when started by you) is in TEST_MODE.
    This only sets the local test process env; ensure the server is started with the same env.
    """
    os.environ['TEST_MODE'] = 'true'
    yield

@pytest.fixture(scope="session", autouse=True)
def cleanup_after_all_tests():
    """Clear users table after tests (runs once, after tests)"""
    yield  # run tests first
    db_path = get_test_db_path()
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users")
            conn.commit()
            print("Cleaned up test users")
        except Exception:
            # Silently ignore if table doesn't exist
            pass
        finally:
            conn.close()

def register_user(payload):
    res = requests.post(f"{BASE_URL}/register", json=payload)
    return res

def login_user(username, password):
    res = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    return res

def create_and_login(username="monsieur", password="monsieurpw"):
    user = {
        "username": username,
        "password": password,
        "name": "Monsieur Test",
        "email": f"{username}@example.com",
        "phone": "+31000000001",
        "birth_year": 1990
    }
    r = register_user(user)
    time.sleep(0.05)
    login_res = login_user(username, password)
    assert login_res.status_code == 200, f"Login failed: {login_res.status_code} {login_res.text}"
    token = login_res.json().get("session_token")
    assert token, "No session_token returned"
    return token, user

def test_profile_get_and_update():
    token, user = create_and_login("monsieur", "monsieurpw")

    # GET profile
    res = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res.status_code == 200, f"GET /profile failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("username") == user["username"]
    assert data.get("name") == user["name"]
    assert data.get("email") == user["email"]

    # Update profile: change name and email
    update_payload = {
        "name": "Monsieur Updated",
        "email": "monsieur.updated@example.com"
    }
    res_put = requests.put(f"{BASE_URL}/profile", json=update_payload, headers={"Authorization": token})
    assert res_put.status_code == 200, f"PUT /profile failed: {res_put.status_code} {res_put.text}"
    # verify updated
    res2 = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("name") == update_payload["name"]
    assert data2.get("email") == update_payload["email"]

def test_profile_unauthorized_access():
    # No Authorization header
    res = requests.get(f"{BASE_URL}/profile")
    assert res.status_code == 401

def test_profile_update_bad_empty_field():
    # Create a second user to avoid collisions
    token, user = create_and_login("monsieur2", "monsieurpw2")

    # Attempt to update name to empty string -> should return 400
    bad_payload = {"name": ""}
    res = requests.put(f"{BASE_URL}/profile", json=bad_payload, headers={"Authorization": token})
    assert res.status_code == 400
