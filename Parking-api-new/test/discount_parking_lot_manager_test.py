import pytest
import requests
import uuid
import sqlite3

BASE_URL = "http://localhost:8000"


@pytest.fixture
def admin_token():
    """Login as admin"""
    res = requests.post(f"{BASE_URL}/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 200
    return res.json()["session_token"]


@pytest.fixture
def parking_lot_manager_token(register_and_login):
    """Create a parking lot manager user"""
    unique_id = uuid.uuid4().hex[:6]
    username = f"manager_{unique_id}"
    # Generate unique phone number
    phone = f"+3161234{unique_id[:4]}"
    token = register_and_login(username, "secure123", "Manager", f"mgr_{unique_id}@test.local", phone, 1990)
    
    # Update role in database ONLY - don't try to update server session
    try:
        from utils import database_utils
        user = database_utils.get_user_by_username(username)
        if user:
            conn = sqlite3.connect(database_utils.get_db_path())
            cursor = conn.cursor()
            # Update user role to PARKING_LOT_MANAGER
            cursor.execute("UPDATE users SET role = ? WHERE id = ?", ("PARKING_LOT_MANAGER", user["id"]))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[WARN] Could not update user role: {e}")
    
    return token


@pytest.fixture
def parking_lot_for_manager(admin_token, parking_lot_manager_token):
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
    
    # Assign manager to parking lot by finding the manager who just logged in
    # We'll query the database to find the user with PARKING_LOT_MANAGER role created most recently
    try:
        from utils import database_utils
        conn = sqlite3.connect(database_utils.get_db_path())
        cursor = conn.cursor()
        # Get the most recently created PARKING_LOT_MANAGER user
        cursor.execute(
            "SELECT id FROM users WHERE role = 'PARKING_LOT_MANAGER' ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        if result:
            manager_id = result[0]
            cursor.execute(
                "INSERT OR IGNORE INTO parking_lot_managers (user_id, parking_lot_id) VALUES (?, ?)",
                (manager_id, lot_id)
            )
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Could not assign manager to lot: {e}")
    
    return lot_id


class TestManagerDiscountCreation:
    """Test discount creation by managers"""
    
    def test_manager_can_create_discount(self, parking_lot_manager_token, parking_lot_for_manager):
        """Manager can create discount for their lot"""
        code = f"TEST_{uuid.uuid4().hex[:4]}"
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "description": "10% discount", "percent": 10.0, "parking_lot_id": parking_lot_for_manager}
        )
        assert res.status_code == 201
        assert res.json()["discount"]["parking_lot_id"] == parking_lot_for_manager
    
    def test_manager_must_specify_parking_lot(self, parking_lot_manager_token):
        """Manager must specify parking_lot_id"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": f"NOPARK_{uuid.uuid4().hex[:4]}", "percent": 5.0}
        )
        assert res.status_code == 400
        assert "parking_lot_id" in res.text.lower()
    
    def test_manager_cannot_create_for_unassigned_lot(self, parking_lot_manager_token, admin_token):
        """Manager cannot create for unassigned lot"""
        # Create unassigned lot
        lot_data = {"name": f"Other_{uuid.uuid4().hex[:4]}", "address": "456 Other St", "capacity": 30, "tariff": 1.50, "day_tariff": 10.0, "lat": 51.0, "lng": 4.0}
        res = requests.post(f"{BASE_URL}/parking-lots", headers={"Authorization": admin_token}, json=lot_data)
        other_lot_id = res.json()["parking_lot"]["id"]
        
        # Try to create discount
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": f"NOAUTH_{uuid.uuid4().hex[:4]}", "percent": 10.0, "parking_lot_id": other_lot_id}
        )
        assert res.status_code == 403


class TestManagerDiscountAccess:
    """Test manager access control"""
    
    def test_manager_can_view_own_discounts(self, parking_lot_manager_token, parking_lot_for_manager):
        """Manager can view own discounts"""
        code = f"VIEW_{uuid.uuid4().hex[:4]}"
        requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 7.0, "parking_lot_id": parking_lot_for_manager}
        )
        
        res = requests.get(f"{BASE_URL}/discounts", headers={"Authorization": parking_lot_manager_token})
        assert res.status_code == 200
        assert any(d.get("code") == code for d in res.json()["discounts"])
    
    def test_manager_can_update_own_discount(self, parking_lot_manager_token, parking_lot_for_manager):
        """Manager can update own discount"""
        code = f"UPD_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 5.0, "parking_lot_id": parking_lot_for_manager}
        )
        discount_id = create_res.json()["discount"]["id"]
        
        res = requests.put(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": parking_lot_manager_token},
            json={"percent": 12.0}
        )
        assert res.status_code == 200
        assert res.json()["discount"]["percent"] == 12.0
    
    def test_manager_can_delete_own_discount(self, parking_lot_manager_token, parking_lot_for_manager):
        """Manager can delete own discount"""
        code = f"DEL_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 3.0, "parking_lot_id": parking_lot_for_manager}
        )
        discount_id = create_res.json()["discount"]["id"]
        
        res = requests.delete(f"{BASE_URL}/discounts/{discount_id}", headers={"Authorization": parking_lot_manager_token})
        assert res.status_code == 200


class TestManagerRestrictedAccess:
    """Test that managers cannot access other lots"""
    
    def test_manager_cannot_update_other_lot_discount(self, parking_lot_manager_token, admin_token):
        """Manager cannot update discount from other lot"""
        # Admin creates discount for different lot
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
        
        # Manager tries to update
        res = requests.put(
            f"{BASE_URL}/discounts/{discount_id}",
            headers={"Authorization": parking_lot_manager_token},
            json={"percent": 50.0}
        )
        assert res.status_code == 403
    
    def test_manager_cannot_delete_other_lot_discount(self, parking_lot_manager_token, admin_token):
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
        
        res = requests.delete(f"{BASE_URL}/discounts/{discount_id}", headers={"Authorization": parking_lot_manager_token})
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
    
    def test_admin_can_view_all_discounts(self, admin_token, parking_lot_manager_token, parking_lot_for_manager):
        """Admin can see all discounts"""
        code = f"MGR_DISC_{uuid.uuid4().hex[:4]}"
        requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 9.0, "parking_lot_id": parking_lot_for_manager}
        )
        
        res = requests.get(f"{BASE_URL}/discounts", headers={"Authorization": admin_token})
        assert res.status_code == 200
        assert any(d.get("code") == code for d in res.json()["discounts"])
    
    def test_admin_can_update_any_discount(self, admin_token, parking_lot_manager_token, parking_lot_for_manager):
        """Admin can update any discount"""
        code = f"ADMIN_UPD_{uuid.uuid4().hex[:4]}"
        create_res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": code, "percent": 4.0, "parking_lot_id": parking_lot_for_manager}
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
    
    def test_missing_token_returns_401(self):
        """Missing token returns 401"""
        res = requests.post(f"{BASE_URL}/discounts", json={"code": "TEST", "percent": 10.0})
        assert res.status_code == 401
    
    def test_invalid_code_returns_400(self, parking_lot_manager_token, parking_lot_for_manager):
        """Empty code returns 400"""
        res = requests.post(
            f"{BASE_URL}/discounts",
            headers={"Authorization": parking_lot_manager_token},
            json={"code": "", "percent": 10.0, "parking_lot_id": parking_lot_for_manager}
        )
        assert res.status_code == 400
    
    def test_nonexistent_discount_returns_404(self, parking_lot_manager_token):
        """Non-existent discount returns 404"""
        res = requests.get(f"{BASE_URL}/discounts/99999", headers={"Authorization": parking_lot_manager_token})
        assert res.status_code == 404
