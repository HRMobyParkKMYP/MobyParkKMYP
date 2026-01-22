import os
import socket
import sqlite3
import uuid
import sys
import threading
import time

import pytest
import requests
import uvicorn


def _reserve_port() -> int:
    """Pick a free localhost port for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# Configure test env before tests are collected so module-level BASE_URL in tests is correct
TEST_API_PORT = int(os.environ.get("TEST_API_PORT", _reserve_port()))
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("API_BASE_URL", f"http://127.0.0.1:{TEST_API_PORT}")

BASE_URL = os.environ["API_BASE_URL"]

def get_test_db_path():
    """Get test database path"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(test_dir, '..', 'api')
    return os.path.join(api_dir, 'data', 'parking_test.sqlite3')


def _start_test_api_server(api_dir: str):
    """Start uvicorn in a background thread for integration tests."""
    # Ensure api directory and parent directory on sys.path for imports
    parent_dir = os.path.dirname(api_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)

    from apiroutes import run as create_app

    config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=TEST_API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to respond
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=1)
            if resp.status_code == 200:
                return server, thread
        except Exception:
            pass
        time.sleep(0.2)

    raise RuntimeError("Test API server failed to start on 127.0.0.1:{TEST_API_PORT}")


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
    # Set TEST_MODE environment variable FIRST
    os.environ['TEST_MODE'] = 'true'

    # Ensure test database exists and mirror schema + admin via helper
    db_path = get_test_db_path()
    try:
        # Import and run the combined setup script
        import sys
        setup_script_dir = os.path.dirname(os.path.abspath(__file__))
        if setup_script_dir not in sys.path:
            sys.path.insert(0, setup_script_dir)
        
        # Add API directory and parent directory to path
        api_dir = os.path.join(setup_script_dir, '..', 'api')
        parent_dir = os.path.dirname(os.path.abspath(api_dir))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        if api_dir not in sys.path:
            sys.path.insert(0, os.path.abspath(api_dir))
        
        # Import the setup module
        import setup_parking_lot_manager_tests as setup_script
        
        # Create test database
        print("\n[SETUP] Creating test database...")
        success = setup_script.create_test_database()
        if not success:
            print("[SETUP ERROR] Failed to create test database")
        else:
            print("[SETUP] Test database created successfully")
        
        # Create admin user
        print("[SETUP] Creating admin user...")
        success = setup_script.create_admin_user()
        if not success:
            print("[SETUP ERROR] Failed to create admin user")
        else:
            print("[SETUP] Admin user created successfully")
            
    except Exception as e:
        print(f"[SETUP] setup failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Verify DB directory
    db_path = get_test_db_path()
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Start dedicated test API server using the test database
    api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
    server, thread = _start_test_api_server(api_dir)
    
    yield
    
    # Signal server shutdown
    try:
        server.should_exit = True
        thread.join(timeout=5)
    except Exception:
        pass
    
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


@pytest.fixture
def admin_token():
    """Login as admin and return session token"""
    res = requests.post(
        f"{BASE_URL}/login",
        json={"username": "admin", "password": "admin"},
        timeout=10,
    )
    if res.status_code != 200:
        pytest.fail(f"Admin login failed: {res.status_code} - {res.text}")
    token = res.json().get("session_token")
    if not token:
        pytest.fail("No admin session token returned")
    return token


@pytest.fixture
def parking_lot_manager_token(register_and_login):
    """Create a parking lot manager user and return their token"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"manager_{unique_id}"
    password = "secure123"
    name = "Parking Lot Manager"
    email = f"manager_{unique_id}@test.local"
    phone = f"+31{hash(unique_id) % 900000000 + 100000000}"
    
    token = register_and_login(username, password, name, email, phone, 1990)
    
    # Update user role in database AND session
    try:
        from utils import database_utils
        from utils.session_manager import update_session
        user = database_utils.get_user_by_username(username)
        if user:
            conn = sqlite3.connect(database_utils.get_db_path())
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE id = ?", ("PARKING_LOT_MANAGER", user["id"]))
            conn.commit()
            conn.close()
            # Also update the session
            update_session(token, {"role": "PARKING_LOT_MANAGER"})
    except Exception as e:
        print(f"[WARN] Could not update user role: {e}")
    
    return token
