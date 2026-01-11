import os
import sys
import uuid
import time
from typing import Tuple

import requests

# Ensure we can import API utilities for DB setup
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(WORKSPACE_ROOT, "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

try:
    from utils import database_utils
except Exception:
    database_utils = None


BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def unique_identity() -> str:
    return uuid.uuid4().hex[:12]


def admin_login(username: str = "admin", password: str = "admin") -> str:
    resp = requests.post(
        f"{BASE_URL}/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if resp.status_code != 200:
        raise AssertionError(f"Admin login failed: {resp.status_code} {resp.text}")
    token = resp.json().get("session_token")
    if not token:
        raise AssertionError("No admin session token returned")
    return token


def create_lot_via_api(admin_token: str, name: str = None, address: str = None, capacity: int = 100, tariff: float = 3.5) -> int:
    name = name or f"Lot-{unique_identity()}"
    address = address or f"Teststraat {unique_identity()}"
    payload = {
        "name": name,
        "address": address,
        "capacity": capacity,
        "tariff": tariff,
        "day_tariff": 0.0,
        "location": None,
        "lat": None,
        "lng": None,
    }
    resp = requests.post(
        f"{BASE_URL}/parking-lots",
        json=payload,
        headers={"Authorization": admin_token},
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        raise AssertionError(f"Create lot via API failed: {resp.status_code} {resp.text}")
    lot_id = resp.json().get("lot_id")
    if not lot_id:
        # Fallback: try reading from returned object
        lot = resp.json().get("parking_lot", {})
        lot_id = lot.get("id") or lot.get("pid")
    assert lot_id, "No lot_id returned when creating lot"
    return int(lot_id)


def get_reserved_count_via_api(lot_id: int) -> int:
    resp = requests.get(f"{BASE_URL}/parking-lots/{lot_id}", timeout=10)
    if resp.status_code != 200:
        raise AssertionError(f"Get lot failed: {resp.status_code} {resp.text}")
    return int(resp.json().get("reserved", 0))


def setup_user_and_lot(register_and_login) -> Tuple[str, str, str, int]:
    unique_id = unique_identity()
    username = f"user_{unique_id}"
    password = f"pw_{unique_identity()}"
    name = f"Name {unique_identity()}"
    email = f"{unique_identity()}@test.local"
    phone = f"+31{hash(unique_id) % 900000000 + 100000000}"  # Ensures unique 9-digit phone
    birth_year = 1990

    token = register_and_login(username, password, name, email, phone, birth_year)
    assert token, "login failed: no token"

    # Login admin and create lot via API
    admin_token = admin_login()
    lot_id = create_lot_via_api(admin_token)

    return username, token, phone, lot_id


def auth_headers(token: str) -> dict:
    # parking_lots and other endpoints expect raw token in Authorization
    return {"Authorization": token}


def test_user_can_create_and_get_reservation(register_and_login):
    username, token, _, lot_id = setup_user_and_lot(register_and_login)

    payload = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,  # Assume a vehicle exists or this is a placeholder
        "start_time": "2025-12-16 10:00:00",
        "end_time": "2025-12-16 12:00:00",
        "status": "pending"
    }
    created = requests.post(f"{BASE_URL}/reservations", json=payload, headers=auth_headers(token), timeout=10)
    if created.status_code not in (200, 201):
        print(f"DEBUG: Status={created.status_code}, Response={created.text}")
    assert created.status_code in (200, 201), f"create reservation failed: {created.status_code} {created.text}"
    res_obj = created.json()
    reservation = res_obj.get("reservation", {})
    res_id = reservation.get("id")
    assert res_id, "reservation id missing"

    # reserved count increments
    assert get_reserved_count_via_api(lot_id) == 1

    got = requests.get(f"{BASE_URL}/reservations/{res_id}", headers=auth_headers(token), timeout=10)
    assert got.status_code == 200
    assert got.json().get("parking_lot_id") == lot_id


def test_create_reservation_invalid_lot_returns_404(register_and_login):
    _, token, _, lot_id = setup_user_and_lot(register_and_login)
    invalid_lot_id = lot_id + 99999
    payload = {
        "parking_lot_id": invalid_lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-16 10:00:00",
        "end_time": "2025-12-16 12:00:00",
    }
    resp = requests.post(f"{BASE_URL}/reservations", json=payload, headers=auth_headers(token), timeout=10)
    assert resp.status_code == 404


def test_get_reservation_not_found(register_and_login):
    _, token, _, _ = setup_user_and_lot(register_and_login)
    resp = requests.get(f"{BASE_URL}/reservations/999999", headers=auth_headers(token), timeout=10)
    assert resp.status_code == 404


def test_update_reservation_by_owner(register_and_login):
    _, token, _, lot_id = setup_user_and_lot(register_and_login)

    # Create
    payload = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-16 14:00:00",
        "end_time": "2025-12-16 16:00:00",
    }
    created = requests.post(f"{BASE_URL}/reservations", json=payload, headers=auth_headers(token), timeout=10)
    assert created.status_code in (200, 201)
    res_id = created.json().get("reservation", {}).get("id")

    # Update
    new_payload = {
        "end_time": "2025-12-16 18:00:00",
    }
    updated = requests.put(
        f"{BASE_URL}/reservations/{res_id}", json=new_payload, headers=auth_headers(token), timeout=10
    )
    assert updated.status_code == 200
    assert updated.json().get("reservation", {}).get("end_time") == new_payload["end_time"]


def test_delete_reservation_decrements_reserved(register_and_login):
    _, token, _, lot_id = setup_user_and_lot(register_and_login)

    payload = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-16 18:00:00",
        "end_time": "2025-12-16 20:00:00",
    }
    created = requests.post(f"{BASE_URL}/reservations", json=payload, headers=auth_headers(token), timeout=10)
    assert created.status_code in (200, 201)
    res_id = created.json().get("reservation", {}).get("id")

    assert get_reserved_count_via_api(lot_id) == 1

    deleted = requests.delete(f"{BASE_URL}/reservations/{res_id}", headers=auth_headers(token), timeout=10)
    assert deleted.status_code in (200, 204)

    # reserved count decremented
    assert get_reserved_count_via_api(lot_id) == 0


def test_unauthorized_access_requires_token():
    # No token
    resp = requests.post(
        f"{BASE_URL}/reservations",
        json={"parking_lot_id": 1, "vehicle_id": 1, "start_time": "2025-12-16 10:00:00", "end_time": "2025-12-16 12:00:00"},
        timeout=10,
    )
    assert resp.status_code in (401, 403)

    # Invalid token
    resp2 = requests.get(f"{BASE_URL}/reservations/1", headers=auth_headers("invalid.token"), timeout=10)
    assert resp2.status_code in (401, 403)


def test_update_reservation_invalid_lot_returns_404(register_and_login):
    _, token, _, lot_id = setup_user_and_lot(register_and_login)
    created = requests.post(
        f"{BASE_URL}/reservations",
        json={"parking_lot_id": lot_id, "vehicle_id": 1, "start_time": "2025-12-16 22:00:00", "end_time": "2025-12-17 00:00:00"},
        headers=auth_headers(token),
        timeout=10,
    )
    assert created.status_code in (200, 201)
    res_id = created.json().get("reservation", {}).get("id")

    invalid_lot_id = lot_id + 77777
    updated = requests.put(
        f"{BASE_URL}/reservations/{res_id}",
        json={"parking_lot_id": invalid_lot_id},
        headers=auth_headers(token),
        timeout=10,
    )
    assert updated.status_code == 404


def test_delete_reservation_not_found(register_and_login):
    _, token, _, _ = setup_user_and_lot(register_and_login)
    resp = requests.delete(f"{BASE_URL}/reservations/999999", headers=auth_headers(token), timeout=10)
    assert resp.status_code == 404


def test_capacity_check_rejects_reservation_when_full(register_and_login):
    """Test that reservation is rejected when parking lot capacity is exceeded"""
    # Create user and lot with capacity of 2
    admin_token = admin_login()
    lot_id = create_lot_via_api(admin_token, capacity=2)

    # Create first user and their reservation
    user1_id = unique_identity()
    user1_token = register_and_login(
        f"user1_{user1_id}", "password", "User One", 
        f"user1_{user1_id}@test.local", f"+31{hash(user1_id) % 900000000 + 100000000}", 1990
    )

    # User 1 creates first reservation
    payload1 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-20 10:00:00",
        "end_time": "2025-12-20 12:00:00",
    }
    resp1 = requests.post(f"{BASE_URL}/reservations", json=payload1, headers=auth_headers(user1_token), timeout=10)
    assert resp1.status_code in (200, 201), f"First reservation should succeed: {resp1.text}"

    # Create second user and their reservation
    user2_id = unique_identity()
    user2_token = register_and_login(
        f"user2_{user2_id}", "password", "User Two", 
        f"user2_{user2_id}@test.local", f"+31{hash(user2_id) % 900000000 + 100000000}", 1991
    )

    # User 2 creates second reservation (should fill capacity)
    payload2 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 2,
        "start_time": "2025-12-20 10:30:00",
        "end_time": "2025-12-20 11:30:00",
    }
    resp2 = requests.post(f"{BASE_URL}/reservations", json=payload2, headers=auth_headers(user2_token), timeout=10)
    assert resp2.status_code in (200, 201), f"Second reservation should succeed: {resp2.text}"

    # Create third user
    user3_id = unique_identity()
    user3_token = register_and_login(
        f"user3_{user3_id}", "password", "User Three", 
        f"user3_{user3_id}@test.local", f"+31{hash(user3_id) % 900000000 + 100000000}", 1992
    )

    # User 3 tries to create third reservation (should be REJECTED - capacity full)
    payload3 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 3,
        "start_time": "2025-12-20 11:00:00",
        "end_time": "2025-12-20 12:00:00",
    }
    resp3 = requests.post(f"{BASE_URL}/reservations", json=payload3, headers=auth_headers(user3_token), timeout=10)
    assert resp3.status_code == 409, f"Third reservation should be rejected due to capacity: {resp3.text}"
    assert "fully booked" in resp3.text.lower() or "capacity" in resp3.text.lower()


def test_capacity_check_allows_non_overlapping_reservations(register_and_login):
    """Test that reservations are allowed if they don't overlap in time"""
    admin_token = admin_login()
    lot_id = create_lot_via_api(admin_token, capacity=1)
    
    # Create two users
    user1_id = unique_identity()
    user1_token = register_and_login(
        f"user1_{user1_id}", "password", "User One", 
        f"user1_{user1_id}@test.local", f"+31{hash(user1_id) % 900000000 + 100000000}", 1990
    )
    
    user2_id = unique_identity()
    user2_token = register_and_login(
        f"user2_{user2_id}", "password", "User Two", 
        f"user2_{user2_id}@test.local", f"+31{hash(user2_id) % 900000000 + 100000000}", 1991
    )
    
    # User 1 books 10:00-12:00
    payload1 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-21 10:00:00",
        "end_time": "2025-12-21 12:00:00",
    }
    resp1 = requests.post(f"{BASE_URL}/reservations", json=payload1, headers=auth_headers(user1_token), timeout=10)
    assert resp1.status_code in (200, 201), f"First reservation should succeed: {resp1.text}"
    
    # User 2 books 13:00-15:00 (no overlap, should succeed even though capacity is 1)
    payload2 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 2,
        "start_time": "2025-12-21 13:00:00",
        "end_time": "2025-12-21 15:00:00",
    }
    resp2 = requests.post(f"{BASE_URL}/reservations", json=payload2, headers=auth_headers(user2_token), timeout=10)
    assert resp2.status_code in (200, 201), f"Non-overlapping reservation should succeed: {resp2.text}"


def test_capacity_check_on_reservation_update(register_and_login):
    """Test that capacity is checked when updating reservation times"""
    admin_token = admin_login()
    lot_id = create_lot_via_api(admin_token, capacity=1)
    
    # Create two users
    user1_id = unique_identity()
    user1_token = register_and_login(
        f"user1_{user1_id}", "password", "User One", 
        f"user1_{user1_id}@test.local", f"+31{hash(user1_id) % 900000000 + 100000000}", 1990
    )
    
    user2_id = unique_identity()
    user2_token = register_and_login(
        f"user2_{user2_id}", "password", "User Two", 
        f"user2_{user2_id}@test.local", f"+31{hash(user2_id) % 900000000 + 100000000}", 1991
    )
    
    # User 1 books 10:00-12:00
    payload1 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-22 10:00:00",
        "end_time": "2025-12-22 12:00:00",
    }
    resp1 = requests.post(f"{BASE_URL}/reservations", json=payload1, headers=auth_headers(user1_token), timeout=10)
    assert resp1.status_code in (200, 201)
    res1_id = resp1.json().get("reservation", {}).get("id")
    
    # User 2 books 13:00-15:00 (no overlap)
    payload2 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 2,
        "start_time": "2025-12-22 13:00:00",
        "end_time": "2025-12-22 15:00:00",
    }
    resp2 = requests.post(f"{BASE_URL}/reservations", json=payload2, headers=auth_headers(user2_token), timeout=10)
    assert resp2.status_code in (200, 201)
    res2_id = resp2.json().get("reservation", {}).get("id")
    
    # User 2 tries to update their reservation to overlap with User 1 (should be rejected)
    update_payload = {
        "start_time": "2025-12-22 11:00:00",
        "end_time": "2025-12-22 14:00:00",
    }
    update_resp = requests.put(
        f"{BASE_URL}/reservations/{res2_id}",
        json=update_payload,
        headers=auth_headers(user2_token),
        timeout=10
    )
    assert update_resp.status_code == 409, f"Update causing overlap should be rejected: {update_resp.text}"


def test_capacity_independent_of_current_sessions(register_and_login):
    """Test that reservation capacity check doesn't consider current active sessions"""
    admin_token = admin_login()
    lot_id = create_lot_via_api(admin_token, capacity=2)
    
    # Create user
    user_id = unique_identity()
    user_token = register_and_login(
        f"user_{user_id}", "password", "User Test", 
        f"user_{user_id}@test.local", f"+31{hash(user_id) % 900000000 + 100000000}", 1990
    )
    
    # Start a parking session NOW (to simulate current occupation)
    session_payload = {
        "licenseplate": f"ABC-{unique_identity()[:3]}"
    }
    session_resp = requests.post(
        f"{BASE_URL}/parking-lots/{lot_id}/sessions/start",
        json=session_payload,
        headers=auth_headers(user_token),
        timeout=10
    )
    # Session might succeed or fail depending on implementation, but we continue
    
    # Create reservation for TOMORROW - should NOT be affected by today's active session
    # Even if there's 1 active session now, we should still be able to reserve 2 spots for tomorrow
    payload1 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 1,
        "start_time": "2025-12-25 10:00:00",
        "end_time": "2025-12-25 12:00:00",
    }
    resp1 = requests.post(f"{BASE_URL}/reservations", json=payload1, headers=auth_headers(user_token), timeout=10)
    assert resp1.status_code in (200, 201), f"Future reservation should succeed regardless of current sessions: {resp1.text}"
    
    # Create a second user
    user2_id = unique_identity()
    user2_token = register_and_login(
        f"user2_{user2_id}", "password", "User Two", 
        f"user2_{user2_id}@test.local", f"+31{hash(user2_id) % 900000000 + 100000000}", 1991
    )
    
    # Second reservation for same time should also succeed (capacity = 2)
    payload2 = {
        "parking_lot_id": lot_id,
        "vehicle_id": 2,
        "start_time": "2025-12-25 10:00:00",
        "end_time": "2025-12-25 12:00:00",
    }
    resp2 = requests.post(f"{BASE_URL}/reservations", json=payload2, headers=auth_headers(user2_token), timeout=10)
    assert resp2.status_code in (200, 201), f"Second future reservation should succeed: {resp2.text}"

