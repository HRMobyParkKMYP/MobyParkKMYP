import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
from utils import database_utils

DATABASE_PATH = database_utils.get_db_path()

def get_all_parking_lots():
    """Get all parking lots"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM parking_lots")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_parking_lot_by_id(lot_id: int):
    """Get parking lot by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM parking_lots WHERE id = ?", (lot_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_parking_lot(data: dict):
    """Create new parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO parking_lots (name, location, address, capacity, reserved, tariff, day_tariff, created_at, lat, lng)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data["name"], data.get("location"), data["address"], data["capacity"], data.get("reserved", 0),
              data["tariff"], data.get("day_tariff", 0), data.get("created_at"), data.get("lat"), data.get("lng")))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_parking_lot(lot_id: int, data: dict):
    """Update parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE parking_lots
            SET name=?, location=?, address=?, capacity=?, reserved=?, tariff=?, day_tariff=?, lat=?, lng=?
            WHERE id=?
        """, (data["name"], data.get("location"), data["address"], data["capacity"], data.get("reserved", 0),
              data["tariff"], data.get("day_tariff", 0), data.get("lat"), data.get("lng"), lot_id))
        conn.commit()
    finally:
        conn.close()

def delete_parking_lot(lot_id: int):
    """Delete parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM parking_lots WHERE id = ?", (lot_id,))
        conn.commit()
    finally:
        conn.close()

def get_sessions_by_lot_id(lot_id: int):
    """Get all sessions for a parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM p_sessions WHERE parking_lot_id = ?", (lot_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_active_session_by_licenseplate(lot_id: int, licenseplate: str):
    """Get active session for licenseplate (stopped_at is NULL)"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM p_sessions WHERE parking_lot_id = ? AND license_plate = ? AND stopped_at IS NULL",
            (lot_id, licenseplate)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_parking_session_by_id(session_id: int):
    """Get parking session by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM p_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_parking_session(data: dict):
    """Create new parking session"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO p_sessions (parking_lot_id, license_plate, started_at, stopped_at, user_name)
            VALUES (?, ?, ?, ?, ?)
        """, (data["lot_id"], data["licenseplate"], data["started"], data.get("stopped"), data["user"]))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_parking_session(session_id: int, data: dict):
    """Update parking session"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        # Only update stopped_at field
        cursor.execute("""
            UPDATE p_sessions
            SET stopped_at=?
            WHERE id=?
        """, (data.get("stopped"), session_id))
        conn.commit()
    finally:
        conn.close()

def delete_parking_session(session_id: int):
    """Delete parking session"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM p_sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

def count_active_sessions(lot_id: int) -> int:
    """Count active sessions (not yet stopped) in parking lot"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM p_sessions WHERE parking_lot_id = ? AND stopped_at IS NULL",
            (lot_id,)
        )
        count = cursor.fetchone()[0]
        return count
    finally:
        conn.close()

def get_upcoming_reservations(lot_id: int, minutes: int = 15) -> List[Dict]:
    """Get reservations starting within the next X minutes"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Get reservations that start within the next X minutes and are pending or confirmed
        # Use localtime instead of 'now' to match the format used when creating reservations
        cursor.execute("""
            SELECT * FROM reservations 
            WHERE parking_lot_id = ? 
            AND status IN ('pending', 'confirmed')
            AND datetime(start_time) <= datetime('now', 'localtime', '+' || ? || ' minutes')
            AND datetime(start_time) >= datetime('now', 'localtime')
        """, (lot_id, minutes))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()