"""
Script to create test database with proper schema and test data.
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import bcrypt

# Add api directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.abspath(os.path.join(script_dir, '..', 'api'))
sys.path.insert(0, api_dir)

# Set TEST_MODE before importing utils
os.environ['TEST_MODE'] = 'true'


def hash_password(password):
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8'), salt.decode('utf-8')


def get_schemas():
    """Return actual database schemas"""
    return [
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            role TEXT CHECK (role IN ('USER','ADMIN','MANAGER')) DEFAULT 'USER',
            created_at TEXT,
            birth_year INTEGER CHECK (birth_year BETWEEN 1900 AND 2100),
            active INTEGER CHECK (active IN (0,1)) DEFAULT 1,
            hash_v TEXT,
            salt TEXT
        )""",
        """CREATE TABLE vehicles (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            license_plate TEXT NOT NULL,
            make TEXT,
            model TEXT,
            color TEXT,
            year INTEGER,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
        )""",
        """CREATE TABLE parking_lots (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            address TEXT,
            capacity INTEGER CHECK (capacity >= 0),
            reserved INTEGER CHECK (reserved >= 0),
            tariff REAL,
            day_tariff REAL,
            created_at TEXT,
            lat REAL,
            lng REAL
        )""",
        """CREATE TABLE parking_lot_managers (
            user_id INTEGER NOT NULL,
            parkinglot_id INTEGER NOT NULL,
            FOREIGN KEY(parkinglot_id) REFERENCES parking_lots(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""",
        """CREATE TABLE reservations (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            parking_lot_id INTEGER,
            vehicle_id INTEGER,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT CHECK (status IN ('pending','confirmed','cancelled','expired','completed')) DEFAULT 'pending',
            created_at TEXT,
            cost REAL CHECK (cost IS NULL OR cost >= 0),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
            FOREIGN KEY (parking_lot_id) REFERENCES parking_lots(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
        )""",
        """CREATE TABLE p_sessions (
            id INTEGER PRIMARY KEY,
            parking_lot_id INTEGER NOT NULL,
            user_id INTEGER,
            vehicle_id INTEGER,
            license_plate TEXT,
            user_name TEXT,
            started_at TEXT NOT NULL,
            stopped_at TEXT,
            duration_minutes INTEGER,
            cost REAL,
            payment_status TEXT DEFAULT 'unpaid',
            verified_exit_at TEXT,
            FOREIGN KEY(parking_lot_id) REFERENCES parking_lots(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        )""",
        """CREATE TABLE payments (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            reservation_id INTEGER,
            p_session_id INTEGER,
            amount REAL CHECK (amount >= 0) NOT NULL,
            currency TEXT DEFAULT 'EUR',
            method TEXT,
            status TEXT CHECK (status IN ('initiated','authorized','paid','failed','refunded','void')) DEFAULT 'initiated',
            created_at TEXT,
            paid_at TEXT,
            external_ref TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
            FOREIGN KEY (p_session_id) REFERENCES p_sessions(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
        )""",
        """CREATE TABLE discounts (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            description TEXT,
            percent REAL CHECK (percent BETWEEN 0 AND 100),
            amount REAL CHECK (amount >= 0),
            applies_to TEXT CHECK (applies_to IN ('reservation','session','both')) DEFAULT 'both',
            starts_at TEXT,
            ends_at TEXT
        )"""
    ]


def insert_test_data(cursor):
    """Insert test data for testing"""
    now = datetime.now().isoformat()
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    next_week = (datetime.now() + timedelta(days=7)).isoformat()
    
    print("\nInserting test data:")
    
    # Users
    print("  - Creating users...")
    admin_pw_hash, admin_salt = hash_password("admin123")
    user_pw_hash, user_salt = hash_password("user123")
    manager_pw_hash, manager_salt = hash_password("manager123")
    
    cursor.execute("""
        INSERT INTO users (id, username, password_hash, name, email, phone, role, created_at, birth_year, active, hash_v, salt)
        VALUES (1, 'admin', ?, 'Admin User', 'admin@mobypark.com', '+31612345678', 'ADMIN', ?, 1990, 1, 'bcrypt', ?)
    """, (admin_pw_hash, now, admin_salt))
    
    cursor.execute("""
        INSERT INTO users (id, username, password_hash, name, email, phone, role, created_at, birth_year, active, hash_v, salt)
        VALUES (2, 'testuser', ?, 'Test User', 'test@mobypark.com', '+31687654321', 'USER', ?, 1995, 1, 'bcrypt', ?)
    """, (user_pw_hash, now, user_salt))
    
    cursor.execute("""
        INSERT INTO users (id, username, password_hash, name, email, phone, role, created_at, birth_year, active, hash_v, salt)
        VALUES (3, 'manager', ?, 'Manager User', 'manager@mobypark.com', '+31698765432', 'MANAGER', ?, 1988, 1, 'bcrypt', ?)
    """, (manager_pw_hash, now, manager_salt))
    
    # Vehicles
    print("  - Creating vehicles...")
    cursor.execute("""
        INSERT INTO vehicles (id, user_id, license_plate, make, model, color, year, created_at)
        VALUES (1, 2, 'AB-123-CD', 'Toyota', 'Corolla', 'Blue', 2020, ?)
    """, (now,))
    
    cursor.execute("""
        INSERT INTO vehicles (id, user_id, license_plate, make, model, color, year, created_at)
        VALUES (2, 2, 'XY-456-ZW', 'Honda', 'Civic', 'Red', 2019, ?)
    """, (now,))
    
    # Parking lots
    print("  - Creating parking lots...")
    cursor.execute("""
        INSERT INTO parking_lots (id, name, location, address, capacity, reserved, tariff, day_tariff, created_at, lat, lng)
        VALUES (1, 'Central Parking', 'City Center', 'Main Street 123', 100, 0, 2.5, 20.0, ?, 52.3676, 4.9041)
    """, (now,))
    
    cursor.execute("""
        INSERT INTO parking_lots (id, name, location, address, capacity, reserved, tariff, day_tariff, created_at, lat, lng)
        VALUES (2, 'Station Parking', 'Train Station', 'Station Road 45', 150, 0, 3.0, 25.0, ?, 52.3792, 4.9003)
    """, (now,))
    
    # Parking lot managers
    print("  - Assigning parking lot managers...")
    cursor.execute("INSERT INTO parking_lot_managers (user_id, parkinglot_id) VALUES (3, 1)")
    
    # Reservations
    print("  - Creating reservations...")
    cursor.execute("""
        INSERT INTO reservations (id, user_id, parking_lot_id, vehicle_id, start_time, end_time, status, created_at, cost)
        VALUES (1, 2, 1, 1, ?, ?, 'confirmed', ?, 10.0)
    """, (tomorrow, next_week, now))
    
    # P_sessions
    print("  - Creating parking sessions...")
    cursor.execute("""
        INSERT INTO p_sessions (id, parking_lot_id, user_id, vehicle_id, license_plate, user_name, started_at, stopped_at, duration_minutes, cost, payment_status)
        VALUES (1, 1, 2, 1, 'AB-123-CD', 'Test User', ?, ?, 120, 5.0, 'paid')
    """, (yesterday, now))
    
    # Payments
    print("  - Creating payments...")
    cursor.execute("""
        INSERT INTO payments (id, user_id, reservation_id, p_session_id, amount, currency, method, status, created_at, paid_at)
        VALUES (1, 2, NULL, 1, 5.0, 'EUR', 'card', 'paid', ?, ?)
    """, (now, now))
    
    # Discounts
    print("  - Creating discounts...")
    cursor.execute("""
        INSERT INTO discounts (id, code, description, percent, amount, applies_to, starts_at, ends_at)
        VALUES (1, 'WELCOME10', '10% off for new users', 10.0, NULL, 'both', ?, ?)
    """, (yesterday, next_week))
    
    cursor.execute("""
        INSERT INTO discounts (id, code, description, percent, amount, applies_to, starts_at, ends_at)
        VALUES (2, 'FIXED5', '5 EUR discount', NULL, 5.0, 'reservation', ?, ?)
    """, (yesterday, next_week))


def create_test_database():
    """Create test database with schema and test data"""
    data_dir = os.path.join(api_dir, 'data')
    test_db = os.path.join(data_dir, 'parking_test.sqlite3')
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"Test DB: {test_db}")
    
    # Remove existing test database
    if os.path.exists(test_db):
        print("Removing existing test database...")
        os.remove(test_db)
    
    # Create test database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    # Create tables
    print("\nCreating tables:")
    for schema in get_schemas():
        table_name = schema.split()[2]
        print(f"  - {table_name}")
        cursor.execute(schema)
    
    # Insert test data
    insert_test_data(cursor)
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Test database created successfully: {test_db}")
    print("\nTest users created:")
    print("  - admin / admin123 (ADMIN)")
    print("  - testuser / user123 (USER)")
    print("  - manager / manager123 (MANAGER)")


if __name__ == "__main__":
    create_test_database()
