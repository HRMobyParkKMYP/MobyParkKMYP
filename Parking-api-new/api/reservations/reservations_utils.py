import sqlite3
from typing import Optional, Dict, Any
from utils import database_utils

DATABASE_PATH = database_utils.get_db_path()

def get_reservation_by_id(reservation_id: int) -> Optional[Dict[str, Any]]:
    """Get reservation by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_reservation(data: dict) -> int:
    """Create new reservation"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO reservations (user_id, parking_lot_id, vehicle_id, start_time, end_time, status, cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (data["user_id"], data["parking_lot_id"], data["vehicle_id"], data["start_time"], data["end_time"], data.get("status", "pending"), data.get("cost")))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_reservation(reservation_id: int, data: dict):
    """Update reservation - only updates provided fields"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        # Build dynamic update query
        update_fields = []
        values = []
        for field in ["parking_lot_id", "vehicle_id", "start_time", "end_time", "status", "cost"]:
            if field in data:
                update_fields.append(f"{field}=?")
                values.append(data[field])
        
        if not update_fields:
            return  # Nothing to update
        
        query = f"UPDATE reservations SET {', '.join(update_fields)} WHERE id=?"
        values.append(reservation_id)
        cursor.execute(query, values)
        conn.commit()
    finally:
        conn.close()

def delete_reservation(reservation_id: int):
    """Delete reservation"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        conn.commit()
    finally:
        conn.close()

def get_parking_lot_by_id(lot_id: int) -> Optional[Dict[str, Any]]:
    """Get parking lot by ID (used for validation)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM parking_lots WHERE id = ?", (lot_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def increment_reserved_count(lot_id: int):
    """Increment the reserved count for a parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE parking_lots
            SET reserved = COALESCE(reserved, 0) + 1
            WHERE id = ?
        """, (lot_id,))
        conn.commit()
    finally:
        conn.close()

def decrement_reserved_count(lot_id: int):
    """Decrement the reserved count for a parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE parking_lots
            SET reserved = MAX(0, COALESCE(reserved, 1) - 1)
            WHERE id = ?
        """, (lot_id,))
        conn.commit()
    finally:
        conn.close()

def get_overlapping_reservations(lot_id: int, start_time: str, end_time: str, exclude_reservation_id: int = None) -> int:
    """Count reservations that overlap with the given time range"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        # Count reservations that overlap with the requested time period
        # Two time ranges overlap if: start1 < end2 AND start2 < end1
        query = """
            SELECT COUNT(*) FROM reservations 
            WHERE parking_lot_id = ? 
            AND status IN ('pending', 'confirmed')
            AND datetime(start_time) < datetime(?)
            AND datetime(end_time) > datetime(?)
        """
        params = [lot_id, end_time, start_time]
        
        # Exclude a specific reservation (for updates)
        if exclude_reservation_id is not None:
            query += " AND id != ?"
            params.append(exclude_reservation_id)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        return count
    finally:
        conn.close()