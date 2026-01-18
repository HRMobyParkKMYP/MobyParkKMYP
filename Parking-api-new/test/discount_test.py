import pytest
import requests
import uuid
import sqlite3
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add API directory to path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(WORKSPACE_ROOT, "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


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
def user_token(register_and_login):
    """Create a regular user and return their token"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"testuser_{unique_id}"
    password = "secret123"
    name = "Test User"
    email = f"testuser_{unique_id}@test.local"
    phone = f"+31{hash(unique_id) % 900000000 + 100000000}"
    
    token = register_and_login(username, password, name, email, phone, 1990)
    return token


@pytest.fixture
def auth_token(register_and_login):
    """Create a test user and return their auth token"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"discuser_{unique_id}"
    password = "secret123"
    name = "Discount User"
    email = f"discuser_{unique_id}@test.local"
    phone = f"+31{hash(unique_id) % 900000000 + 100000000}"
    
    token = register_and_login(username, password, name, email, phone, 1990)
    return token


@pytest.fixture(scope="function")
def manager_token_with_role(register_and_login):
    """Create a parking lot manager user"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"manager_{unique_id}"
    phone = f"+3161234{unique_id[:4]}"
    token = register_and_login(username, "secure123", "Manager", f"mgr_{unique_id}@test.local", phone, 1990)
    
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
            update_session(token, {"role": "PARKING_LOT_MANAGER"})
    except Exception as e:
        print(f"[WARN] Could not update user role: {e}")
    
    return token


@pytest.fixture
def discount_db():
    """Get the appropriate database path"""
    if os.environ.get('TEST_MODE') == 'true':
        db_path = Path(__file__).parent.parent / "api" / "data" / "parking_test.sqlite3"
    else:
        db_path = Path(__file__).parent.parent / "api" / "data" / "parking.sqlite3"
    return str(db_path)


@pytest.fixture
def parking_lot_for_manager(admin_token, manager_token_with_role):
    """Create a parking lot and assign manager to it"""
    lot_data = {
        "name": f"Test Lot {uuid.uuid4().hex[:4]}",
        "address": "123 Test Street",
        "capacity": 50,
        "tariff": 2.50,
        "day_tariff": 15.0,
        "lat": 52.0,
        "lng": 5.0
    }
    
    res = requests.post(f"{BASE_URL}/parking-lots", headers={"Authorization": admin_token}, json=lot_data)
    assert res.status_code == 200, f"Failed to create parking lot: {res.text}"
    lot_id = res.json()["parking_lot"]["id"]
    
    try:
        from utils.session_manager import get_session
        session_user = get_session(manager_token_with_role)
        if session_user and session_user.get("id"):
            manager_id = session_user["id"]
            
            from utils import database_utils
            conn = sqlite3.connect(database_utils.get_db_path())
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO parking_lot_managers (user_id, parking_lot_id) VALUES (?, ?)",
                (manager_id, lot_id)
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[WARN] Could not assign manager to lot: {e}")
    
    return lot_id


@pytest.fixture
def parking_lot_for_conftest_manager(admin_token, parking_lot_manager_token):
    """Create a parking lot for the conftest parking_lot_manager_token fixture"""
    lot_data = {
        "name": f"Test Lot for Manager {uuid.uuid4().hex[:4]}",
        "address": "456 Test Avenue",
        "capacity": 75,
        "tariff": 3.00,
        "day_tariff": 18.0,
        "lat": 51.5,
        "lng": 4.5
    }
    
    res = requests.post(f"{BASE_URL}/parking-lots", headers={"Authorization": admin_token}, json=lot_data)
    assert res.status_code == 200, f"Failed to create parking lot: {res.text}"
    lot_id = res.json()["parking_lot"]["id"]
    
    try:
        from utils.session_manager import get_session
        session_user = get_session(parking_lot_manager_token)
        if session_user and session_user.get("id"):
            manager_id = session_user["id"]
            
            from utils import database_utils
            conn = sqlite3.connect(database_utils.get_db_path())
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO parking_lot_managers (user_id, parking_lot_id) VALUES (?, ?)",
                (manager_id, lot_id)
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[WARN] Could not assign manager to lot: {e}")
    
    return lot_id


def insert_discount(db_path, code, percent=None, amount=None, description="Test Discount", 
                   starts_at=None, ends_at=None):
    """Helper to insert a discount into the database"""
    import time
    
    time.sleep(0.1)
    
    conn = sqlite3.connect(db_path, timeout=5.0)
    cursor = conn.cursor()
    
    if starts_at is None:
        starts_at = (datetime.now() - timedelta(days=1)).isoformat()
    if ends_at is None:
        ends_at = (datetime.now() + timedelta(days=30)).isoformat()
    
    unique_code = f"{code}_{uuid.uuid4().hex[:4]}"
    
    try:
        cursor.execute("""
            INSERT INTO discounts (code, description, percent, amount, applies_to, starts_at, ends_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (unique_code, description, percent, amount, "reservation", starts_at, ends_at))
        
        conn.commit()
        return unique_code
    finally:
        conn.close()


# ============================================================================
# Admin Discount Creation Tests
# ============================================================================

class TestDiscountCreation:
    """Test discount creation endpoints"""
    
    def test_admin_can_create_percent_discount(self, admin_token):
        """Admin should be able to create a percentage discount"""
        unique_code = f"SAVE10_{uuid.uuid4().hex[:4]}"
        
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "Save 10% on parking",
                "percent": 10.0,
                "applies_to": "reservation"
            },
            timeout=10,
        )
        
        assert res.status_code == 201, f"Failed: {res.text}"
        body = res.json()
        assert body["status"] == "success"
        assert body["discount"]["code"] == unique_code
        assert body["discount"]["percent"] == 10.0
        assert body["discount"]["amount"] is None
        assert body["discount"]["id"] is not None
    
    def test_admin_can_create_flat_discount(self, admin_token):
        """Admin should be able to create a flat amount discount"""
        unique_code = f"SAVE5EUR_{uuid.uuid4().hex[:4]}"
        
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "Save €5",
                "amount": 5.0,
                "applies_to": "both"
            },
            timeout=10,
        )
        
        assert res.status_code == 201, f"Failed: {res.status_code} - {res.text}"
        body = res.json()
        assert body["discount"]["code"] == unique_code
        assert body["discount"]["amount"] == 5.0
        assert body["discount"]["percent"] is None
    
    def test_admin_can_create_discount_with_date_range(self, admin_token):
        """Admin should be able to create a discount with specific date range"""
        unique_code = f"SEASONAL_{uuid.uuid4().hex[:4]}"
        start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
        
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "Seasonal discount",
                "percent": 15.0,
                "starts_at": start,
                "ends_at": end
            },
            timeout=10,
        )
        
        assert res.status_code == 201
        body = res.json()
        assert body["discount"]["starts_at"] == start
        assert body["discount"]["ends_at"] == end
    



# ============================================================================
# Discount Update and Delete Tests
# ============================================================================

class TestDiscountModification:
    """Test updating and deleting discounts"""
    
    def test_admin_can_update_discount(self, admin_token):
        """Admin should be able to update a discount"""
        unique_code = f"UPDATE_TEST_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "Original description",
                "percent": 10.0
            },
            timeout=10,
        )
        
        discount_id = create_res.json()["discount"]["id"]
        
        new_end = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        res = requests.put(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": admin_token},
            json={
                "description": "Updated description",
                "percent": 15.0,
                "ends_at": new_end
            },
            timeout=10,
        )
        
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["discount"]["description"] == "Updated description"
        assert body["discount"]["percent"] == 15.0
    
    def test_admin_can_delete_discount(self, admin_token):
        """Admin should be able to delete a discount"""
        unique_code = f"DELETE_TEST_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "To be deleted",
                "percent": 5.0
            },
            timeout=10,
        )
        
        discount_id = create_res.json()["discount"]["id"]
        
        res = requests.delete(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": admin_token},
            timeout=10,
        )
        
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        
        get_res = requests.get(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": admin_token},
            timeout=10,
        )
        assert get_res.status_code == 404


# ============================================================================
# Discount Validation Tests
# ============================================================================

class TestDiscountValidation:
    """Test validation of discount creation"""
    
    def test_cannot_create_discount_with_both_percent_and_amount(self, admin_token):
        """Should fail if both percent and amount are provided"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": f"INVALID_{uuid.uuid4().hex[:4]}",
                "description": "Invalid discount",
                "percent": 10.0,
                "amount": 5.0
            },
            timeout=10,
        )
        
        assert res.status_code == 400
        assert "percent or amount" in res.text.lower()
    
    def test_cannot_create_discount_with_neither_percent_nor_amount(self, admin_token):
        """Should fail if neither percent nor amount is provided"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": f"INVALID_{uuid.uuid4().hex[:4]}",
                "description": "Invalid discount"
            },
            timeout=10,
        )
        
        assert res.status_code == 400
    
    def test_cannot_create_discount_with_empty_code(self, admin_token):
        """Should fail if code is empty"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": "",
                "description": "Invalid discount",
                "percent": 10.0
            },
            timeout=10,
        )
        
        assert res.status_code == 400
        assert "code" in res.text.lower()
    
    def test_cannot_create_duplicate_discount_code(self, admin_token):
        """Should fail if discount code already exists"""
        unique_code = f"DUP_TEST_{uuid.uuid4().hex[:4]}"
        
        requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "First discount",
                "percent": 10.0
            },
            timeout=10,
        )
        
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={
                "code": unique_code,
                "description": "Duplicate discount",
                "percent": 15.0
            },
            timeout=10,
        )
        
        assert res.status_code == 409
        assert "already exists" in res.text.lower()


# ============================================================================
# Authorization Tests
# ============================================================================

class TestDiscountAuthz:
    """Test authorization for discount endpoints"""
    
    def test_user_cannot_create_discount(self, user_token):
        """Non-admin user should not be able to create discounts"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": user_token},
            json={
                "code": f"UNAUTHORIZED_{uuid.uuid4().hex[:4]}",
                "description": "Should fail",
                "percent": 10.0
            },
            timeout=10,
        )
        
        assert res.status_code == 403
        assert "admin" in res.text.lower()
    
    def test_user_cannot_list_discounts(self, user_token):
        """Non-admin user should not be able to list discounts"""
        res = requests.get(
            f"{BASE_URL}/discounts",
            headers={"Authorization": user_token},
            timeout=10,
        )
        
        assert res.status_code == 403
    
    def test_missing_token_returns_401(self):
        """Missing authorization header should return 401"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            json={
                "code": f"NO_TOKEN_{uuid.uuid4().hex[:4]}",
                "description": "Should fail",
                "percent": 10.0
            },
            timeout=10,
        )
        
        assert res.status_code == 401


# ============================================================================
# Manager Discount Tests
# ============================================================================

class TestManagerDiscountCreation:
    """Test discount creation by managers"""
    
    def test_manager_can_create_discount(self, manager_token_with_role, parking_lot_for_manager):
        """Manager can create discount for their lot"""
        code = f"TEST_{uuid.uuid4().hex[:4]}"
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": manager_token_with_role},
            json={"code": code, "description": "10% discount", "percent": 10.0, "parking_lot_id": parking_lot_for_manager}
        )
        assert res.status_code == 201, f"Got {res.status_code}: {res.text}"
        assert res.json()["discount"]["parking_lot_id"] == parking_lot_for_manager
    
    def test_manager_must_specify_parking_lot(self, manager_token_with_role):
        """Manager must specify parking_lot_id"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": manager_token_with_role},
            json={"code": f"NOPARK_{uuid.uuid4().hex[:4]}", "percent": 5.0}
        )
        assert res.status_code == 400
        assert "parking_lot_id" in res.text.lower()
    
    def test_manager_cannot_create_for_unassigned_lot(self, manager_token_with_role, admin_token):
        """Manager cannot create for unassigned lot"""
        lot_data = {"name": f"Other_{uuid.uuid4().hex[:4]}", "address": "456 Other St", "capacity": 30, "tariff": 1.50, "day_tariff": 10.0, "lat": 51.0, "lng": 4.0}
        res = requests.post(f"{BASE_URL}/parking-lots", headers={"Authorization": admin_token}, json=lot_data)
        other_lot_id = res.json()["parking_lot"]["id"]
        
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": manager_token_with_role},
            json={"code": f"NOAUTH_{uuid.uuid4().hex[:4]}", "percent": 10.0, "parking_lot_id": other_lot_id}
        )
        assert res.status_code == 403


class TestManagerDiscountAccess:
    """Test manager access control"""
    
    def test_manager_can_update_own_discount(self, manager_token_with_role, parking_lot_for_manager):
        """Manager can update own discount"""
        code = f"UPD_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": manager_token_with_role},
            json={"code": code, "percent": 5.0, "parking_lot_id": parking_lot_for_manager}
        )
        discount_id = create_res.json()["discount"]["id"]
        
        res = requests.put(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": manager_token_with_role},
            json={"percent": 12.0}
        )
        assert res.status_code == 200
        assert res.json()["discount"]["percent"] == 12.0
    
    def test_manager_can_delete_own_discount(self, manager_token_with_role, parking_lot_for_manager):
        """Manager can delete own discount"""
        code = f"DEL_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": manager_token_with_role},
            json={"code": code, "percent": 3.0, "parking_lot_id": parking_lot_for_manager}
        )
        discount_id = create_res.json()["discount"]["id"]
        
        res = requests.delete(f"{BASE_URL}/discounts/{discount_id}", headers={"Authorization": manager_token_with_role})
        assert res.status_code == 200


class TestManagerRestrictedAccess:
    """Test that managers cannot access other lots"""
    
    def test_manager_cannot_update_other_lot_discount(self, manager_token_with_role, admin_token):
        """Manager cannot update discount from other lot"""
        lot_data = {"name": f"Other_{uuid.uuid4().hex[:4]}", "address": "999 St", "capacity": 40, "tariff": 2.75, "day_tariff": 18.0, "lat": 52.5, "lng": 5.5}
        lot_res = requests.post(f"{BASE_URL}/parking-lots", headers={"Authorization": admin_token}, json=lot_data)
        other_lot_id = lot_res.json()["parking_lot"]["id"]
        
        code = f"OTHER_{uuid.uuid4().hex[:4]}"
        disc_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={"code": code, "percent": 8.0, "parking_lot_id": other_lot_id}
        )
        discount_id = disc_res.json()["discount"]["id"]
        
        res = requests.put(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": manager_token_with_role},
            json={"percent": 50.0}
        )
        assert res.status_code == 403
    
    def test_manager_cannot_delete_other_lot_discount(self, manager_token_with_role, admin_token):
        """Manager cannot delete discount from other lot"""
        lot_data = {"name": f"Admin_{uuid.uuid4().hex[:4]}", "address": "222 St", "capacity": 35, "tariff": 2.25, "day_tariff": 16.0, "lat": 52.8, "lng": 5.3}
        lot_res = requests.post(f"{BASE_URL}/parking-lots", headers={"Authorization": admin_token}, json=lot_data)
        admin_lot_id = lot_res.json()["parking_lot"]["id"]
        
        code = f"ADMIN_ONLY_{uuid.uuid4().hex[:4]}"
        disc_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={"code": code, "amount": 5.0, "parking_lot_id": admin_lot_id}
        )
        discount_id = disc_res.json()["discount"]["id"]
        
        res = requests.delete(f"{BASE_URL}/discounts/{discount_id}", headers={"Authorization": manager_token_with_role})
        assert res.status_code == 403


class TestAdminOverride:
    """Test admin capabilities"""
    
    def test_admin_can_create_global_discount(self, admin_token):
        """Admin can create discount without parking_lot_id"""
        code = f"GLOBAL_{uuid.uuid4().hex[:4]}"
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": admin_token},
            json={"code": code, "percent": 20.0}
        )
        assert res.status_code == 201
        assert res.json()["discount"]["parking_lot_id"] is None
    
    def test_admin_can_view_all_discounts(self, admin_token, parking_lot_manager_token, parking_lot_for_conftest_manager):
        """Admin can see all discounts"""
        code = f"MGR_DISC_{uuid.uuid4().hex[:4]}"
        requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 9.0, "parking_lot_id": parking_lot_for_conftest_manager}
        )
        
        res = requests.get(f"{BASE_URL}/discounts", headers={"Authorization": admin_token})
        assert res.status_code == 200
        assert any(d.get("code") == code for d in res.json()["discounts"])
    
    def test_admin_can_update_any_discount(self, admin_token, parking_lot_manager_token, parking_lot_for_conftest_manager):
        """Admin can update any discount"""
        code = f"ADMIN_UPD_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 4.0, "parking_lot_id": parking_lot_for_conftest_manager}
        )
        discount_id = create_res.json()["discount"]["id"]
        
        res = requests.put(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": admin_token},
            json={"percent": 25.0}
        )
        assert res.status_code == 200
        assert res.json()["discount"]["percent"] == 25.0


class TestErrorHandling:
    """Test error responses"""
    
    def test_nonexistent_discount_returns_404(self, manager_token_with_role):
        """Non-existent discount returns 404"""
        res = requests.get(f"{BASE_URL}/discounts/99999", headers={"Authorization": manager_token_with_role})
        assert res.status_code == 404


# ============================================================================
# Integration Tests - Discount with Payments
# ============================================================================

class TestDiscountWithPayments:
    """Test discount code functionality with payments"""
    
    def test_create_payment_with_valid_percent_discount(self, auth_token, discount_db):
        """Create payment with valid percentage discount code"""
        code = insert_discount(discount_db, "SAVE10", percent=10.0)
        
        res = requests.post(
            f"{BASE_URL}/payments",
            headers={"Authorization": auth_token},
            json={
                "reservation_id": None,
                "amount": 100.0,
                "currency": "EUR",
                "method": "CARD",
                "discount_code": code
            }
        )

        assert res.status_code == 201, f"Failed: {res.text}"
        body = res.json()
        assert body["status"] == "success"
        assert "discount" in body
        assert body["discount"]["code"] == code
        assert body["discount"]["original_amount"] == 100.0
        assert body["discount"]["discount_amount"] == 10.0
        assert body["discount"]["final_amount"] == 90.0
        assert body["payment"]["amount"] == 90.0
    
    def test_create_payment_with_valid_flat_discount(self, auth_token, discount_db):
        """Create payment with valid flat amount discount code"""
        code = insert_discount(discount_db, "SAVE15EUR", amount=15.0)
        
        res = requests.post(
            f"{BASE_URL}/payments",
            headers={"Authorization": auth_token},
            json={
                "reservation_id": None,
                "amount": 100.0,
                "currency": "EUR",
                "method": "CARD",
                "discount_code": code
            }
        )

        assert res.status_code == 201
        body = res.json()
        assert "discount" in body
        assert body["discount"]["code"] == code
        assert body["discount"]["original_amount"] == 100.0
        assert body["discount"]["discount_amount"] == 15.0
        assert body["discount"]["final_amount"] == 85.0
        assert body["payment"]["amount"] == 85.0
    
    def test_discount_cannot_exceed_payment_amount(self, auth_token, discount_db):
        """Verify discount never exceeds payment amount"""
        code = insert_discount(discount_db, "HUGE80", percent=80.0)
        
        res = requests.post(
            f"{BASE_URL}/payments",
            headers={"Authorization": auth_token},
            json={
                "reservation_id": None,
                "amount": 100.0,
                "currency": "EUR",
                "method": "CARD",
                "discount_code": code
            }
        )

        assert res.status_code == 201
        body = res.json()
        assert body["discount"]["final_amount"] >= 0
        assert body["discount"]["discount_amount"] <= body["discount"]["original_amount"]
    
    def test_create_payment_with_expired_discount(self, auth_token, discount_db):
        """Create payment with expired discount code - should fail"""
        expired_time = (datetime.now() - timedelta(days=1)).isoformat()
        code = insert_discount(
            discount_db, "EXPIRED_CODE", percent=10.0, 
            ends_at=expired_time
        )
        
        res = requests.post(
            f"{BASE_URL}/payments",
            headers={"Authorization": auth_token},
            json={
                "reservation_id": None,
                "amount": 100.0,
                "currency": "EUR",
                "method": "CARD",
                "discount_code": code
            }
        )

        assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
        assert "expired" in res.text.lower()
    
    def test_create_payment_with_future_discount(self, auth_token, discount_db):
        """Create payment with discount that hasn't started yet - should fail"""
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        code = insert_discount(
            discount_db, "FUTURE_CODE", percent=10.0, 
            starts_at=future_time
        )
        
        res = requests.post(
            f"{BASE_URL}/payments",
            headers={"Authorization": auth_token},
            json={
                "reservation_id": None,
                "amount": 100.0,
                "currency": "EUR",
                "method": "CARD",
                "discount_code": code
            }
        )

        assert res.status_code == 400
        assert "expired" in res.text.lower() or "not valid" in res.text.lower()
    
    def test_discount_code_case_insensitive(self, auth_token, discount_db):
        """Verify discount codes are case-insensitive"""
        code = insert_discount(discount_db, "casetest", percent=20.0)
        
        res = requests.post(
            f"{BASE_URL}/payments",
            headers={"Authorization": auth_token},
            json={
                "reservation_id": None,
                "amount": 100.0,
                "currency": "EUR",
                "method": "CARD",
                "discount_code": code.upper()
            }
        )

        assert res.status_code == 201
        body = res.json()
        assert body["discount"]["code"].lower() == code.lower()
        assert body["discount"]["discount_amount"] == 20.0
