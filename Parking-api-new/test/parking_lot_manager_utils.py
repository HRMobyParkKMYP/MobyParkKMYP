"""
Utility functions and fixtures for parking lot manager testing
"""
import sqlite3
import sys
import requests
import os
api_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api')
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from utils import database_utils


def assign_user_to_parking_lot_manager_role(username):
    """
    Update a user to have PARKING_LOT_MANAGER role.
    
    Args:
        username: The username to update
        
    Returns:
        User dict or None if user not found
    """
    user = database_utils.get_user_by_username(username)
    if not user:
        return None
    
    conn = sqlite3.connect(database_utils.get_db_path())
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", ("PARKING_LOT_MANAGER", user["id"]))
    conn.commit()
    conn.close()
    
    return user


def assign_manager_to_parking_lot(user_id, parking_lot_id):
    """
    Assign a user as manager for a specific parking lot.
    
    Args:
        user_id: The user's ID
        parking_lot_id: The parking lot's ID
        
    Returns:
        True if assignment successful, False otherwise
    """
    try:
        conn = sqlite3.connect(database_utils.get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO parking_lot_managers (user_id, parking_lot_id) VALUES (?, ?)",
            (user_id, parking_lot_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error assigning manager: {e}")
        return False


def remove_manager_from_parking_lot(user_id, parking_lot_id):
    """
    Remove a user as manager from a specific parking lot.
    
    Args:
        user_id: The user's ID
        parking_lot_id: The parking lot's ID
        
    Returns:
        True if removal successful, False otherwise
    """
    try:
        conn = sqlite3.connect(database_utils.get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM parking_lot_managers WHERE user_id = ? AND parking_lot_id = ?",
            (user_id, parking_lot_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing manager: {e}")
        return False


def get_user_managed_parking_lots(user_id):
    """
    Get all parking lots managed by a user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        List of parking lot IDs
    """
    try:
        conn = sqlite3.connect(database_utils.get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT parking_lot_id FROM parking_lot_managers WHERE user_id = ?",
            (user_id,)
        )
        results = cursor.fetchall()
        conn.close()
        return [row[0] for row in results]
    except Exception as e:
        print(f"Error getting managed parking lots: {e}")
        return []


def create_parking_lot(admin_token, lot_data, base_url="http://localhost:8000"):
    """
    Helper to create a parking lot via API.
    
    Args:
        admin_token: Admin's session token
        lot_data: Dict with parking lot details
        base_url: API base URL
        
    Returns:
        Parking lot ID if successful, None otherwise
    """
    res = requests.post(
        f"{base_url}/parking_lots",
        headers={"Authorization": admin_token},
        json=lot_data,
        timeout=10
    )
    
    if res.status_code != 201:
        print(f"Failed to create parking lot: {res.status_code} - {res.text}")
        return None
    
    return res.json()["parking_lot"]["id"]


def create_discount_for_parking_lot(manager_token, parking_lot_id, code, percent=None, 
                                   amount=None, description="", base_url="http://localhost:8000"):
    """
    Helper to create a discount for a parking lot.
    
    Args:
        manager_token: Manager's session token
        parking_lot_id: Parking lot ID
        code: Discount code
        percent: Percentage discount (optional)
        amount: Flat amount discount (optional)
        description: Discount description
        base_url: API base URL
        
    Returns:
        Discount ID if successful, None otherwise
    """
    discount_data = {
        "code": code,
        "description": description,
        "parking_lot_id": parking_lot_id
    }
    
    if percent is not None:
        discount_data["percent"] = percent
    elif amount is not None:
        discount_data["amount"] = amount
    else:
        raise ValueError("Must specify either percent or amount")
    
    res = requests.post(
        f"{base_url}/discounts",
        headers={"Authorization": manager_token},
        json=discount_data,
        timeout=10
    )
    
    if res.status_code != 201:
        print(f"Failed to create discount: {res.status_code} - {res.text}")
        return None
    
    return res.json()["discount"]["id"]
