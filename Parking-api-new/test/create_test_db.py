"""
Script om test database te maken met zelfde structuur als main database.
Optioneel: maak ook een admin user aan.
"""
import sqlite3
import os
import sys

# Add api directory to path so we can import utils
script_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.abspath(os.path.join(script_dir, '..', 'api'))
sys.path.insert(0, api_dir)

from utils import auth_utils, database_utils

def create_admin_user(username="admin", password="admin"):
    """Create an admin user using the same logic as account registration"""
    
    # Hash password using the same method as registration
    hashed_password, salt = auth_utils.hash_password_bcrypt(password)
    
    # Create admin user
    user_id = database_utils.create_user(
        username=username,
        password_hash=hashed_password,
        name="Admin User",
        email=f"{username}@mobypark.com",
        phone="+31612345678",
        birth_year=1990,
        role='ADMIN',
        hash_v='bcrypt',
        salt=salt
    )
    
    print(f"  - Admin user created: {username} / {password} (user_id: {user_id})")
    return user_id

def create_test_database(with_admin=True):
    # Use the api_dir from module level
    main_db = os.path.join(api_dir, 'data', 'parking.sqlite3')
    test_db = os.path.join(api_dir, 'data', 'parking_test.sqlite3')
    
    print(f"Main DB: {main_db}")
    print(f"Test DB: {test_db}")
    
    # Connect to main database and get schema
    main_conn = sqlite3.connect(main_db)
    main_cursor = main_conn.cursor()
    
    # Get all table schemas
    main_cursor.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND sql IS NOT NULL
        ORDER BY name
    """)
    schemas = main_cursor.fetchall()
    main_conn.close()
    
    # Create test database
    if os.path.exists(test_db):
        print(f"Removing test database")
        os.remove(test_db)
    
    test_conn = sqlite3.connect(test_db)
    test_cursor = test_conn.cursor()
    
    # Create tables in test database
    print("\nCreating tables in test database:")
    for schema_tuple in schemas:
        schema = schema_tuple[0]
        print(f"  - {schema.split()[2]}")  # Table name
        test_cursor.execute(schema)
    
    test_conn.commit()
    test_conn.close()
    
    print(f"\nTest database created successfully: {test_db}")
    
    # Set TEST_MODE environment variable for database_utils
    os.environ['TEST_MODE'] = 'true'
    
    # Create admin user if requested
    if with_admin:
        print("\nCreating admin user:")
        try:
            create_admin_user(username="admin", password="admin")
        except Exception as e:
            print(f"  - Error creating admin: {e}")

if __name__ == "__main__":
    import sys
    # Check if --no-admin flag is provided
    with_admin = "--no-admin" not in sys.argv
    create_test_database(with_admin=with_admin)
