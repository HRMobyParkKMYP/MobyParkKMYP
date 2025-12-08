from typing import Optional, List, Dict, Any
from datetime import datetime
from utils.database_utils import get_db_connection, execute_query


def get_vehicles_by_user_id(user_id: int) -> List[Dict[str, Any]]:
    """Get all vehicles for a specific user"""
    query = "SELECT * FROM vehicles WHERE user_id = ?"
    return execute_query(query, (user_id,))


def get_vehicle_by_id(vehicle_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific vehicle by ID for a user"""
    query = "SELECT * FROM vehicles WHERE id = ? AND user_id = ?"
    results = execute_query(query, (vehicle_id, user_id))
    return results[0] if results else None


def get_vehicle_by_license_plate(license_plate: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Check if vehicle with license plate exists for user"""
    query = "SELECT * FROM vehicles WHERE license_plate = ? AND user_id = ?"
    results = execute_query(query, (license_plate, user_id))
    return results[0] if results else None


def create_vehicle(user_id: int, license_plate: str, make: str = None, model: str = None, color: str = None, year: int = None) -> int:
    """Create a new vehicle for a user"""
    created_at = datetime.now().strftime("%Y-%m-%d")
    
    query = """
        INSERT INTO vehicles (user_id, license_plate, make, model, color, year, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (user_id, license_plate, make, model, color, year, created_at))
        return cursor.lastrowid


def update_vehicle(vehicle_id: str, user_id: int, make: str = None, model: str = None, color: str = None, year: int = None) -> bool:
    """Update vehicle information"""
    updates = []
    params = []
    
    if make is not None:
        updates.append("make = ?")
        params.append(make)
    if model is not None:
        updates.append("model = ?")
        params.append(model)
    if color is not None:
        updates.append("color = ?")
        params.append(color)
    if year is not None:
        updates.append("year = ?")
        params.append(year)
    
    if not updates:
        return False
    
    params.extend([vehicle_id, user_id])
    query = f"UPDATE vehicles SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.rowcount > 0


def delete_vehicle(vehicle_id: str, user_id: int) -> bool:
    """Delete a vehicle"""
    query = "DELETE FROM vehicles WHERE id = ? AND user_id = ?"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (vehicle_id, user_id))
        return cursor.rowcount > 0
