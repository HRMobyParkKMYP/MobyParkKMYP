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
            INSERT INTO reservations (licenseplate, startdate, enddate, parkinglot, user)
            VALUES (?, ?, ?, ?, ?)
        """, (data["licenseplate"], data["startdate"], data["enddate"], data["parkinglot"], data["user"]))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_reservation(reservation_id: int, data: dict):
    """Update reservation"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE reservations
            SET licenseplate=?, startdate=?, enddate=?, parkinglot=?, user=?
            WHERE id=?
        """, (data["licenseplate"], data["startdate"], data["enddate"], data["parkinglot"], data["user"], reservation_id))
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
