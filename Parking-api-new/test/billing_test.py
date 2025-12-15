import pytest
import requests
import sqlite3
import os

BASE_URL = "http://localhost:8000"


def get_test_db_path():
    """Test database path"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(test_dir, '..', 'api')
    return os.path.join(api_dir, 'data', 'parking_test.sqlite3')


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_all_tests():
    """Clear users, sessions, and payments tables na tests"""
    yield  # Eerst alle tests uitvoeren
    # Daarna de cleanup uitvoeren
    db_path = get_test_db_path()
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM payments")
        cursor.execute("DELETE FROM p_sessions")
        conn.commit()
        conn.close()
        print("Cleaned up payments, sessions, and users")


def get_admin_token():
    """Login with the admin user created by create_test_db.py"""
    username = "admin"
    password = "admin"
    
    res = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    if res.status_code == 200:
        return res.json().get("session_token")
    
    raise AssertionError(
        f"Could not login as admin. Make sure to run 'python test/create_test_db.py' first "
        f"to create the test database with admin user."
    )


# Test 1: User can get own billing
def test_user_can_get_own_billing(register_and_login):
    token = register_and_login("alice", "test123", "Alice", "alice@test.local", "+3111111111", 1990)
    headers = {"Authorization": token}

    res = requests.get(f"{BASE_URL}/billing", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert isinstance(data, list)
    # Check for session in billing data if not empty
    if len(data) > 0:
        assert all("session" in b for b in data)


# Test 2: User cannot get other user's billing
def test_user_cannot_get_other_user_billing(register_and_login):
    register_and_login("alice_b", "test123", "Alice B", "alice_b@test.local", "+3111111112", 1990)
    token_bob = register_and_login("bob", "test123", "Bob", "bob@test.local", "+3222222222", 1990)
    headers = {"Authorization": token_bob}

    res = requests.get(f"{BASE_URL}/billing/alice_b", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert "Access denied" in res.text


# Test 3: Unauthorized billing access fails
def test_unauthorized_billing_access_fails():
    res = requests.get(f"{BASE_URL}/billing")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "Unauthorized" in res.text or "Invalid or missing session token" in res.text


# Test 4: Admin can get specific user billing
def test_admin_can_get_specific_user_billing(register_and_login):
    token_admin = get_admin_token()
    headers = {"Authorization": token_admin}

    register_and_login("charlie", "pass123", "Charlie", "charlie@test.local", "+3333333333", 1990)

    res = requests.get(f"{BASE_URL}/billing/charlie", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert all("session" in b and "amount" in b for b in data)


# Test 5: Admin cannot access billing with invalid token
def test_admin_cannot_access_billing_with_invalid_token():
    headers = {"Authorization": "invalid-token-123"}
    res = requests.get(f"{BASE_URL}/billing/anyuser", headers=headers)
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "Unauthorized" in res.text or "Invalid or missing session token" in res.text
