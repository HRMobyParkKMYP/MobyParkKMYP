import requests
import uuid
import sqlite3
import os
import sys

sys.path.insert(0, 'api')
from utils import database_utils, session_manager, auth_utils

# Setup
os.environ['TEST_MODE'] = 'true'
BASE_URL = 'http://localhost:8000'

# Create manager user  
unique_id = uuid.uuid4().hex[:6]
username = f'mgr_test_{unique_id}'
phone = f'+3161{unique_id}'

register_res = requests.post(f'{BASE_URL}/register', json={'username': username, 'password': 'pwd123', 'name': 'TestMgr', 'email': f'{username}@test.local', 'phone': phone, 'birth_year': 1990})
print(f'Register: {register_res.status_code}')

login_res = requests.post(f'{BASE_URL}/login', json={'username': username, 'password': 'pwd123'})
print(f'Login: {login_res.status_code}')

if login_res.status_code == 200:
    token = login_res.json()['session_token']
    print(f'Token: {token}')
    
    # Update user role in database
    user = database_utils.get_user_by_username(username)
    print(f'User ID: {user["id"]}')
    
    if user:
        conn = sqlite3.connect(database_utils.get_db_path())
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', ('PARKING_LOT_MANAGER', user['id']))
        conn.commit()
        
        # Update session
        session_user = session_manager.get_session(token)
        print(f'Session before update: {session_user}')
        if session_user:
            session_manager.update_session(token, {'role': 'PARKING_LOT_MANAGER'})
            updated = session_manager.get_session(token)
            print(f'Session after update: {updated}')
            print(f'Session user role: {updated.get("role")}')
        
        # Create parking lot with admin
        lot_res = requests.post(f'{BASE_URL}/login', json={'username': 'admin', 'password': 'admin'})
        admin_token = lot_res.json()['session_token']
        
        lot_data = {'name': 'Test', 'address': 'Addr', 'capacity': 10, 'tariff': 1.0, 'lat': 50.0, 'lng': 5.0}
        lot_res = requests.post(f'{BASE_URL}/parking-lots', headers={'Authorization': admin_token}, json=lot_data)
        print(f'Create lot: {lot_res.status_code}')
        
        if lot_res.status_code == 200:
            lot_id = lot_res.json()['parking_lot']['id']
            print(f'Lot ID: {lot_id}')
            
            # Assign manager to lot
            cursor.execute('INSERT OR IGNORE INTO parking_lot_managers (user_id, parking_lot_id) VALUES (?, ?)', (user['id'], lot_id))
            conn.commit()
            
            # Verify assignment
            cursor.execute('SELECT * FROM parking_lot_managers WHERE user_id = ? AND parking_lot_id = ?', (user['id'], lot_id))
            result = cursor.fetchone()
            print(f'Assignment exists: {result is not None}')
            
            # Try to create discount
            disc_res = requests.post(f'{BASE_URL}/discounts', headers={'Authorization': token}, json={'code': 'TEST001', 'percent': 10.0, 'parking_lot_id': lot_id})
            print(f'Create discount: {disc_res.status_code}')
            print(f'Response: {disc_res.text}')
        
        conn.close()
else:
    print(f'Login failed: {login_res.text}')
