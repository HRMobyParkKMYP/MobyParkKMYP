"""
Script om test database te maken met zelfde structuur als main database.
"""
import sqlite3
import os

def create_test_database():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(script_dir, '..', 'api')
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

if __name__ == "__main__":
    create_test_database()
