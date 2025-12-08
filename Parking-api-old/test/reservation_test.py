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
    """Logs in using the pre-existing admin account."""
    res = requests.post(f"{BASE_URL}/login", json={
        "username": "admin_user",
        "password": "securepass"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    data = res.json()
    assert "session_token" in data, f"No session_token in response: {data}"
    return data["session_token"]


class TestReservation:
    def test_create_reservation(self, register_and_login):
        """Test creating a new reservation."""
        token = register_and_login("user1", "pass1", "User One", "user1@example.com", "+31600000001")
        headers = {"Authorization": token}
        
        response = requests.post(f"{BASE_URL}/reservations", json={
            "licenseplate": "ABC-123",
            "parkinglot": "1",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        }, headers=headers)
        assert response.status_code in (200, 201), f"Failed to create reservation: {response.text}"
        data = response.json()
        assert "reservation" in data or "id" in data
    
    def test_create_reservation_missing_field(self, register_and_login):
        """Test that creating a reservation without required fields fails."""
        token = register_and_login("user2", "pass2", "User Two", "user2@example.com", "+31600000002")
        headers = {"Authorization": token}
        
        response = requests.post(f"{BASE_URL}/reservations", json={
            "licenseplate": "ABC-123",
            "startdate": "2024-07-01T10:00:00Z"
            # Missing enddate and parkinglot
        }, headers=headers)
        assert response.status_code == 400 or response.status_code == 401, f"Expected 400/401, got {response.status_code}"
    
    def test_create_reservation_invalid_parking_lot(self, register_and_login):
        """Test that creating a reservation with invalid parking lot fails."""
        token = register_and_login("user3", "pass3", "User Three", "user3@example.com", "+31600000003")
        headers = {"Authorization": token}
        
        response = requests.post(f"{BASE_URL}/reservations", json={
            "licenseplate": "ABC-123",
            "parkinglot": "9999999999999",  # Non-existent parking lot
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        }, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_get_reservation(self, register_and_login):
        """Test getting a specific reservation."""
        token = register_and_login("user4", "pass4", "User Four", "user4@example.com", "+31600000004")
        headers = {"Authorization": token}
        
        # First create a reservation
        create_res = requests.post(f"{BASE_URL}/reservations", json={
            "licenseplate": "XYZ-789",
            "parkinglot": "1",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        }, headers=headers)
        
        if create_res.status_code in (200, 201):
            res_data = create_res.json()
            res_id = res_data.get("id") or res_data.get("reservation", {}).get("id")
            
            # Now get the reservation
            response = requests.get(f"{BASE_URL}/reservations/{res_id}", headers=headers)
            assert response.status_code == 200, f"Failed to get reservation: {response.text}"
    
    def test_get_nonexistent_reservation(self, register_and_login):
        """Test getting a reservation that doesn't exist."""
        token = register_and_login("user5", "pass5", "User Five", "user5@example.com", "+31600000005")
        headers = {"Authorization": token}
        
        response = requests.get(f"{BASE_URL}/reservations/999", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_update_reservation(self, register_and_login):
        """Test updating an existing reservation."""
        token = register_and_login("user6", "pass6", "User Six", "user6@example.com", "+31600000006")
        headers = {"Authorization": token}
        
        # First create a reservation
        create_res = requests.post(f"{BASE_URL}/reservations", json={
            "licenseplate": "UPD-123",
            "parkinglot": "1",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        }, headers=headers)
        
        if create_res.status_code in (200, 201):
            res_data = create_res.json()
            res_id = res_data.get("id") or res_data.get("reservation", {}).get("id")
            
            # Update the reservation
            response = requests.put(f"{BASE_URL}/reservations/{res_id}", json={
                "licenseplate": "UPD-123",
                "parkinglot": "1",
                "startdate": "2024-07-01T10:00:00Z",
                "enddate": "2024-07-01T13:00:00Z"  # Updated end time
            }, headers=headers)
            assert response.status_code == 200, f"Failed to update: {response.text}"
    
    def test_delete_reservation(self, register_and_login):
        """Test deleting a reservation."""
        token = register_and_login("user7", "pass7", "User Seven", "user7@example.com", "+31600000007")
        headers = {"Authorization": token}
        
        # First create a reservation
        create_res = requests.post(f"{BASE_URL}/reservations", json={
            "licenseplate": "DEL-456",
            "parkinglot": "1",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        }, headers=headers)
        
        if create_res.status_code in (200, 201):
            res_data = create_res.json()
            res_id = res_data.get("id") or res_data.get("reservation", {}).get("id")
            
            # Delete the reservation
            response = requests.delete(f"{BASE_URL}/reservations/{res_id}", headers=headers)
            assert response.status_code == 200, f"Failed to delete: {response.text}"
    
    def test_delete_nonexistent_reservation(self, register_and_login):
        """Test deleting a reservation that doesn't exist."""
        token = register_and_login("user8", "pass8", "User Eight", "user8@example.com", "+31600000008")
        headers = {"Authorization": token}
        
        response = requests.delete(f"{BASE_URL}/reservations/999", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"