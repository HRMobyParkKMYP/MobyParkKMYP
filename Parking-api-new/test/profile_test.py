import pytest
import requests
import sqlite3
import os
from datetime import datetime
import time
import uuid

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

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
def cleanup_before_and_after_tests():
    """Clear users table before and after tests"""
    db_path = get_test_db_path()
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE username != 'admin'")
            conn.commit()
            print("Cleaned up test users before tests")
        except Exception:
            pass
        finally:
            conn.close()
    
    yield  # run tests
    
    # cleanup after
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE username != 'admin'")
            conn.commit()
            print("Cleaned up test users after tests")
        except Exception:
            pass
        finally:
            conn.close()

def register_user(payload):
    res = requests.post(f"{BASE_URL}/register", json=payload)
    return res

def login_user(username, password):
    res = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    return res

def create_and_login(username=None, password="testpw"):
    # Generate unique username and phone if not provided
    if username is None:
        username = f"user_{uuid.uuid4().hex[:8]}"
    
    unique_id = uuid.uuid4().hex[:6]
    user = {
        "username": username,
        "password": password,
        "name": "Test User",
        "email": f"{username}_{unique_id}@example.com",
        "phone": f"+3160{unique_id}",  # unique phone
        "birth_year": 1990
    }
    r = register_user(user)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    
    time.sleep(0.1)
    
    login_res = login_user(username, password)
    assert login_res.status_code == 200, f"Login failed: {login_res.status_code} {login_res.text}"
    token = login_res.json().get("session_token")
    assert token, "No session_token returned"
    return token, user

def test_profile_get_and_update():
    token, user = create_and_login()

    # GET profile
    res = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res.status_code == 200, f"GET /profile failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("username") == user["username"]
    assert data.get("name") == user["name"]
    assert data.get("email") == user["email"]

    # Update profile: provide all fields
    update_payload = {
        "name": "Updated Name",
        "email": f"updated_{uuid.uuid4().hex[:6]}@example.com",
        "phone": user.get("phone"),
        "birth_year": user.get("birth_year", 1990)
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
    # Create a user with unique credentials
    token, user = create_and_login()

    # Attempt to update name to empty string -> should return 400
    bad_payload = {"name": ""}
    res = requests.put(f"{BASE_URL}/profile", json=bad_payload, headers={"Authorization": token})
    assert res.status_code == 400

def test_create_update_and_verify():
    """
    Complete user lifecycle test:
    1. Create a new user
    2. Verify initial profile
    3. Update multiple fields
    4. Verify all updates were applied
    5. Verify session reflects changes
    """
    # Step 1: Create user
    token, user = create_and_login()
    original_username = user["username"]
    original_phone = user["phone"]
    
    # Step 2: Verify initial profile
    res = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res.status_code == 200
    profile = res.json()
    assert profile.get("username") == original_username
    assert profile.get("name") == "Test User"
    assert profile.get("phone") == original_phone
    assert profile.get("birth_year") == 1990
    
    # Step 3: Update multiple fields
    new_email = f"newemail_{uuid.uuid4().hex[:6]}@example.com"
    new_phone = f"+3161{uuid.uuid4().hex[:6]}"
    new_name = "Updated Test User"
    new_birth_year = 1985
    
    update_payload = {
        "name": new_name,
        "email": new_email,
        "phone": new_phone,
        "birth_year": new_birth_year
    }
    
    res_update = requests.put(
        f"{BASE_URL}/profile",
        json=update_payload,
        headers={"Authorization": token}
    )
    assert res_update.status_code == 200, f"PUT failed: {res_update.status_code} {res_update.text}"
    
    # Step 4: Verify all updates were applied
    res_verify = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res_verify.status_code == 200
    updated_profile = res_verify.json()
    
    # Check all fields were updated
    assert updated_profile.get("name") == new_name, f"Name not updated: {updated_profile.get('name')}"
    assert updated_profile.get("email") == new_email, f"Email not updated: {updated_profile.get('email')}"
    assert updated_profile.get("phone") == new_phone, f"Phone not updated: {updated_profile.get('phone')}"
    assert updated_profile.get("birth_year") == new_birth_year, f"Birth year not updated: {updated_profile.get('birth_year')}"
    
    # Username and initial data should remain unchanged
    assert updated_profile.get("username") == original_username
    
    # Step 5: Verify session is also updated (session data should match profile)
    res_final = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res_final.status_code == 200
    final_profile = res_final.json()
    assert final_profile.get("name") == new_name
    assert final_profile.get("email") == new_email
    assert final_profile.get("phone") == new_phone
    assert final_profile.get("birth_year") == new_birth_year


def test_update_password():
    """Test that password can be updated without exposing it in response"""
    token, user = create_and_login()
    old_password = user["password"]
    
    # Update password
    new_password = "newSecurePassword123!"
    res = requests.put(
        f"{BASE_URL}/profile",
        json={"password": new_password},
        headers={"Authorization": token}
    )
    assert res.status_code == 200
    
    # Old token should still work (session not invalidated)
    res_profile = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res_profile.status_code == 200
    
    # Login with new password should work
    login_new = login_user(user["username"], new_password)
    assert login_new.status_code == 200
    new_token = login_new.json().get("session_token")
    assert new_token
    
    # Old password should no longer work
    login_old = login_user(user["username"], old_password)
    assert login_old.status_code == 401


def test_partial_update():
    """Test updating only some fields while others remain unchanged"""
    token, user = create_and_login()
    
    # Only update name, leave everything else
    new_name = "Partially Updated"
    res = requests.put(
        f"{BASE_URL}/profile",
        json={"name": new_name},
        headers={"Authorization": token}
    )
    assert res.status_code == 200
    
    # Verify name changed but email/phone/birth_year unchanged
    res_profile = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res_profile.status_code == 200
    profile = res_profile.json()
    assert profile.get("name") == new_name
    assert profile.get("email") == user["email"]
    assert profile.get("phone") == user["phone"]
    assert profile.get("birth_year") == 1990