#!/usr/bin/env python3
"""
Combined setup script for test database and parking lot manager tests
Creates test database with main database schema, adds necessary tables, and creates test data
"""
import sqlite3
import os
import sys

# Add API directory to path so we can import utils
script_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.abspath(os.path.join(script_dir, '..', 'api'))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

def get_db_path(test_mode=None):
    """Get the database path (main or test)"""
    if test_mode is None:
        test_mode = os.environ.get('TEST_MODE') == 'true'
    
    db_name = 'parking_test.sqlite3' if test_mode else 'parking.sqlite3'
    return os.path.join(api_dir, 'data', db_name)


def create_test_database():
    """Create test database with the same structure as main database"""
    main_db = get_db_path(test_mode=False)
    test_db = get_db_path(test_mode=True)
    
    print(f"  Main DB: {main_db}")
    print(f"  Test DB: {test_db}")
    
    if not os.path.exists(main_db):
        print(f"[ERROR] Main database not found at {main_db}")
        return False
    
    try:
        # Connect to main database and get schema
        main_conn = sqlite3.connect(main_db)
        main_cursor = main_conn.cursor()
        
        # Get all table schemas
        main_cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND sql IS NOT NULL
            AND name != 'sqlite_sequence'
            ORDER BY name
        """)
        schemas = main_cursor.fetchall()
        main_conn.close()
        
        # Create test database
        if os.path.exists(test_db):
            print(f"  Removing existing test database")
            os.remove(test_db)
        
        test_conn = sqlite3.connect(test_db)
        test_cursor = test_conn.cursor()
        
        # Create tables in test database
        print("  Creating tables:")
        for schema_tuple in schemas:
            schema = schema_tuple[0]
            table_name = schema.split()[2]
            print(f"    - {table_name}")
            
            # Update users table schema to include PARKING_LOT_MANAGER role
            if table_name == 'users' and "CHECK (role IN ('USER','ADMIN','MANAGER'))" in schema:
                schema = schema.replace(
                    "CHECK (role IN ('USER','ADMIN','MANAGER'))",
                    "CHECK (role IN ('USER','ADMIN','MANAGER','PARKING_LOT_MANAGER'))"
                )
            
            test_cursor.execute(schema)
        
        test_conn.commit()
        test_conn.close()
        
        print("[OK] Test database created successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create test database: {e}")
        return False


def update_users_table_role_constraint():
    """Update users table to include PARKING_LOT_MANAGER role"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        current_schema = cursor.fetchone()[0]
        
        # Check if already updated
        if 'PARKING_LOT_MANAGER' in current_schema:
            print("[OK] Users table already supports PARKING_LOT_MANAGER role")
            conn.close()
            return True
        
        print("  Updating users table to support PARKING_LOT_MANAGER role...")
        
        # Clean up any leftover temp table
        cursor.execute("DROP TABLE IF EXISTS users_new")
        
        # Disable foreign keys temporarily
        cursor.execute("PRAGMA foreign_keys=OFF")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Create new table with updated constraint (without UNIQUE constraint initially)
        cursor.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                password_hash TEXT,
                name TEXT,
                email TEXT,
                phone TEXT,
                role TEXT CHECK (role IN ('USER','ADMIN','MANAGER','PARKING_LOT_MANAGER')) DEFAULT 'USER',
                created_at TEXT,
                birth_year INTEGER CHECK (birth_year BETWEEN 1900 AND 2100),
                active INTEGER CHECK (active IN (0,1)) DEFAULT 1,
                hash_v TEXT,
                salt TEXT
            )
        """)
        
        # Copy data, keeping only first occurrence of each username
        cursor.execute("""
            INSERT INTO users_new 
            SELECT id, username, password_hash, name, email, phone, role, created_at, 
                   birth_year, active, hash_v, salt 
            FROM users
            WHERE id IN (
                SELECT MIN(id) FROM users GROUP BY username
            )
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # Add unique index
        cursor.execute("CREATE UNIQUE INDEX idx_users_username ON users(username)")
        
        # Commit transaction
        cursor.execute("COMMIT")
        
        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        
        conn.commit()
        conn.close()
        print("[OK] Updated users table with PARKING_LOT_MANAGER role (removed duplicates)")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to update users table: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def ensure_parking_lot_managers_table():
    """Create parking_lot_managers table if it doesn't exist"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='parking_lot_managers'"
        )
        if cursor.fetchone():
            print("[OK] parking_lot_managers table already exists")
            conn.close()
            return True
        
        # Create table
        cursor.execute("""
            CREATE TABLE parking_lot_managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                parking_lot_id INTEGER NOT NULL,
                assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (parking_lot_id) REFERENCES parking_lots(id) ON DELETE CASCADE,
                UNIQUE(user_id, parking_lot_id)
            )
        """)
        
        # Create indexes
        cursor.execute(
            "CREATE INDEX idx_parking_lot_managers_user_id ON parking_lot_managers(user_id)"
        )
        cursor.execute(
            "CREATE INDEX idx_parking_lot_managers_parking_lot_id ON parking_lot_managers(parking_lot_id)"
        )
        
        conn.commit()
        conn.close()
        print("[OK] Created parking_lot_managers table")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create table: {e}")
        return False


def add_parking_lot_id_to_discounts():
    """Add parking_lot_id column to discounts if it doesn't exist"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(discounts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'parking_lot_id' in columns:
            print("[OK] parking_lot_id column already exists in discounts table")
            conn.close()
            return True
        
        # Add column
        cursor.execute("ALTER TABLE discounts ADD COLUMN parking_lot_id INTEGER DEFAULT NULL")
        
        # Create index
        cursor.execute(
            "CREATE INDEX idx_discounts_parking_lot_id ON discounts(parking_lot_id)"
        )
        
        conn.commit()
        conn.close()
        print("[OK] Added parking_lot_id column to discounts table")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to add column: {e}")
        return False


def create_admin_user():
    """Create an admin user for testing"""
    try:
        from utils import auth_utils, database_utils
        
        # Check if admin user exists
        admin = database_utils.get_user_by_username("admin")
        if admin:
            print("[OK] Admin user already exists")
            return True
        
        # Hash password using the same method as registration
        hashed_password, salt = auth_utils.hash_password_bcrypt("admin")
        
        # Create admin user
        user_id = database_utils.create_user(
            username="admin",
            password_hash=hashed_password,
            name="Admin User",
            email="admin@mobypark.com",
            phone="+31612345678",
            birth_year=1990,
            role='ADMIN',
            hash_v='bcrypt',
            salt=salt
        )
        
        print(f"[OK] Created admin user (username: admin, password: admin, user_id: {user_id})")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create admin user: {e}")
        return False


def create_test_manager_user():
    """Create a test manager user for testing"""
    try:
        from utils import auth_utils, database_utils
        
        # Check if test manager exists
        test_manager = database_utils.get_user_by_username("test_manager")
        if test_manager:
            print("[OK] Test manager user already exists")
            return True
        
        # Create test manager
        hashed_password, salt = auth_utils.hash_password_bcrypt("password123")
        
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users 
            (username, password_hash, name, email, phone, role, birth_year, active, hash_v, salt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            "test_manager",
            hashed_password,
            "Test Manager",
            "test_manager@mobypark.local",
            "+31612345678",
            "PARKING_LOT_MANAGER",
            1990,
            1,
            "bcrypt",
            salt
        ))
        
        conn.commit()
        conn.close()
        print("[OK] Created test manager user (username: test_manager, password: password123)")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create test manager: {e}")
        return False


def main():
    """Run all setup steps"""
    print("=" * 80)
    print("Test Database and Parking Lot Manager Tests - Setup")
    print("=" * 80)
    
    # Parse command line arguments
    create_test_db = "--test-db" in sys.argv
    with_admin = "--with-admin" in sys.argv
    no_admin = "--no-admin" in sys.argv
    
    # Set test mode if requested
    if create_test_db:
        os.environ['TEST_MODE'] = 'true'
        print("\n[MODE] Test database mode enabled")
    else:
        print("\n[MODE] Main database mode")
    
    steps = []
    
    # Add test database creation step if requested
    if create_test_db:
        steps.append(("Creating test database", create_test_database))
    
    # Add table and user creation steps
    steps.extend([
        ("Updating users table for PARKING_LOT_MANAGER role", update_users_table_role_constraint),
        ("Creating parking_lot_managers table", ensure_parking_lot_managers_table),
        ("Adding parking_lot_id to discounts", add_parking_lot_id_to_discounts),
    ])
    
    # Add admin user creation if explicitly requested or in test mode without --no-admin
    if with_admin or (create_test_db and not no_admin):
        steps.append(("Creating admin user", create_admin_user))
    
    # Always add test manager
    steps.append(("Creating test manager user", create_test_manager_user))
    
    all_success = True
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        try:
            if not step_func():
                all_success = False
        except Exception as e:
            print(f"[ERROR] {step_name} failed: {e}")
            all_success = False
    
    print("\n" + "=" * 80)
    if all_success:
        print("✓ Setup completed successfully!")
        if create_test_db:
            print(f"\nTest database: {get_db_path(test_mode=True)}")
        print("\nYou can now run the tests:")
        print("  pytest test/discount_parking_lot_manager_test.py -v")
        print("\nAvailable users:")
        if with_admin or (create_test_db and not no_admin):
            print("  - admin / admin (ADMIN)")
        print("  - test_manager / password123 (PARKING_LOT_MANAGER)")
    else:
        print("✗ Setup had errors. Please fix issues above.")
    
    print("\nUsage options:")
    print("  --test-db          Create and setup test database instead of main database")
    print("  --with-admin       Create admin user (automatically enabled with --test-db)")
    print("  --no-admin         Skip admin user creation even in test mode")
    print("=" * 80)
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
