import pytest
import requests
import os
import sqlite3

BASE_URL = "http://localhost:8000"

def get_test_db_path():
    """Get test database path"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(test_dir, '..', 'api')
    return os.path.join(api_dir, 'data', 'parking_test.sqlite3')


@pytest.fixture
def register_and_login():
    """
    Factory fixture that registers a user and returns their session token.
    Usage: token = register_and_login("username", "password", "name", "email", "phone", birth_year)
    """
    def _register_and_login(username: str, password: str, name: str, email: str, phone: str, birth_year: int):
        # Register user
        register_data = {
            "username": username,
            "password": password,
            "name": name,
            "email": email,
            "phone": phone,
            "birth_year": birth_year
        }
        
        register_response = requests.post(f"{BASE_URL}/register", json=register_data)
        
        # If user already exists, just login
        if register_response.status_code == 409:
            pass  # User already exists, proceed to login
        elif register_response.status_code != 200:
            raise Exception(f"Registration failed: {register_response.status_code} - {register_response.text}")
        
        # Login to get token
        login_data = {
            "username": username,
            "password": password
        }
        
        login_response = requests.post(f"{BASE_URL}/login", json=login_data)
        
        if login_response.status_code != 200:
            raise Exception(f"Login failed: {login_response.status_code} - {login_response.text}")
        
        token = login_response.json().get("session_token")
        
        if not token:
            raise Exception("No session token returned from login")
        
        return token
    
    return _register_and_login


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before all tests"""
    # Set TEST_MODE environment variable
    os.environ['TEST_MODE'] = 'true'

    # Ensure test database exists and mirror schema + admin via helper
    try:
        from create_test_db import create_test_database
        create_test_database(with_admin=True)
    except Exception as e:
        print(f"[SETUP] create_test_database failed: {e}")
    
    # Verify DB directory
    db_path = get_test_db_path()
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    yield
    
    # Cleanup after all tests
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Clear all test data except admin
            cursor.execute("DELETE FROM vehicles WHERE id > 0")
            cursor.execute("DELETE FROM reservations WHERE id > 0")
            cursor.execute("DELETE FROM users WHERE username != 'admin'")
            conn.commit()
            conn.close()
            print("\n[CLEANUP] Test database cleaned (preserved admin)")
        except Exception as e:
            print(f"\n[CLEANUP ERROR] {e}")
