import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime

def get_db_path():
    """Geeft database pad (test DB als TEST_MODE=true)"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Gebruik een test database als TEST_MODE=true
    if os.environ.get('TEST_MODE') == 'true':
        db_name = 'parking_test.sqlite3'
    else:
        db_name = 'parking.sqlite3'
    
    return os.path.join(current_dir, '..', 'data', db_name)

@contextmanager
def get_db_connection():
    """Database connectie context manager"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row 
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Voer SELECT query uit, geeft list van dicts"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def create_user(username: str, password_hash: str, name: str, email: str, 
                phone: str, birth_year: int, role: str = 'USER', 
                hash_v: str = 'bcrypt', salt: str = None) -> int:
    """Maak nieuwe gebruiker, geeft user ID"""
    created_at = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    
    query = """
        INSERT INTO users (username, password_hash, name, email, phone, 
                          role, birth_year, active, hash_v, salt, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (username, password_hash, name, email, phone, 
                              role, birth_year, hash_v, salt, created_at))
        return cursor.lastrowid

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username"""
    query = "SELECT * FROM users WHERE username = ?"
    results = execute_query(query, (username,))
    return results[0] if results else None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    query = "SELECT * FROM users WHERE email = ?"
    results = execute_query(query, (email,))
    return results[0] if results else None

def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Get user by phonenumber"""
    query = "SELECT * FROM users WHERE phone = ?"
    results = execute_query(query, (phone,))
    return results[0] if results else None

def get_all_users() -> List[Dict[str, Any]]:
    """Get alle users"""
    query = "SELECT * FROM users ORDER BY created_at DESC"
    return execute_query(query)