import pytest
import json
import sys
import os
from io import BytesIO
from unittest.mock import Mock, patch

# Add the api directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from api.endpoints.reservations import ReservationHandler


class MockHeaders:
    """Mock headers object."""
    def __init__(self, headers_dict):
        self._headers = headers_dict
    
    def get(self, key, default=None):
        return self._headers.get(key, default)


class MockRequestHandler:
    """Mock HTTP request handler that simulates BaseHTTPRequestHandler."""
    
    def __init__(self, method, path, body=None, headers_dict=None):
        self.command = method
        self.path = path
        self.headers = MockHeaders(headers_dict or {})
        self.rfile = BytesIO(body.encode('utf-8') if body else b'')
        self.wfile = BytesIO()
        self._status = None
        self._headers = {}
        
    def send_response(self, code):
        self._status = code
        
    def send_header(self, key, value):
        self._headers[key] = value
        
    def end_headers(self):
        pass
    
    def get_response_body(self):
        return self.wfile.getvalue().decode('utf-8')
    
    def get_status(self):
        return self._status


class TestClient:
    """Test client that calls ReservationHandler directly."""
    
    def __init__(self, session_token='test-token-123'):
        self.session_token = session_token
        
    def _make_request(self, method, path, json_data=None):
        body = json.dumps(json_data) if json_data else None
        headers = {
            'Authorization': self.session_token,
            'Content-Length': str(len(body)) if body else '0'
        }
        
        mock_request = MockRequestHandler(method, path, body, headers)
        handler = ReservationHandler()
        handler.handle(mock_request, method)
        
        response_body = mock_request.get_response_body()
        return {
            'status_code': mock_request.get_status(),
            'body': response_body,
            'json': json.loads(response_body) if response_body and response_body.strip() and response_body[0] in '{[' else None
        }
    
    def post(self, path, json=None):
        return self._make_request('POST', path, json)
    
    def get(self, path):
        return self._make_request('GET', path)
    
    def put(self, path, json=None):
        return self._make_request('PUT', path, json)
    
    def delete(self, path):
        return self._make_request('DELETE', path)


@pytest.fixture
def mock_storage():
    """Mock storage functions to use in-memory data."""
    reservations = {}
    parking_lots = {
        '1': {'id': '1', 'name': 'Lot 1', 'reserved': 0},
        '2': {'id': '2', 'name': 'Lot 2', 'reserved': 0}
    }
    
    # Patch BaseEndpoint.setup to accept method parameter
    original_setup = None
    
    def patched_setup(self, request_handler, method=None):
        return (
            request_handler.path,
            request_handler.send_response,
            request_handler.send_header,
            request_handler.end_headers,
            request_handler.wfile
        )
    
    with patch('endpoints.reservations.load_reservation_data', return_value=reservations), \
         patch('endpoints.reservations.save_reservation_data', side_effect=lambda data: reservations.update(data)), \
         patch('endpoints.reservations.load_parking_lot_data', return_value=parking_lots), \
         patch('endpoints.reservations.save_parking_lot_data', side_effect=lambda data: parking_lots.update(data)), \
         patch('endpoints.baseEndpoints.BaseEndpoint.setup', patched_setup):
        yield reservations, parking_lots


@pytest.fixture
def mock_session():
    """Mock session manager to return a test user."""
    user_data = {'username': 'testuser', 'role': 'USER'}
    
    with patch('endpoints.reservations.get_session', return_value=user_data):
        yield user_data


@pytest.fixture
def client(mock_storage, mock_session):
    """Provide a test client with mocked dependencies."""
    return TestClient()


class TestReservation:
    def test_create_reservation(self, client, mock_storage):
        """Test creating a new reservation."""
        response = client.post("/reservations", json={
            "licenseplate": "ABC-123",
            "parkinglot": "2",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        })
        assert response['status_code'] == 201
        data = response['json']
        assert data['status'] == "Success"
        assert 'reservation' in data
        assert data['reservation']['id'] is not None
        assert data['reservation']['licenseplate'] == "ABC-123"
    
    def test_create_reservation_missing_field(self, client):
        """Test that creating a reservation without required fields fails."""
        response = client.post("/reservations", json={
            "licenseplate": "ABC-123",
            "startdate": "2024-07-01T10:00:00Z"
            # Missing enddate and parkinglot
        })
        assert response['status_code'] == 401
        data = response['json']
        assert 'error' in data
        assert data['error'] == "Require field missing"
    
    def test_create_reservation_invalid_parking_lot(self, client):
        """Test that creating a reservation with invalid parking lot fails."""
        response = client.post("/reservations", json={
            "licenseplate": "ABC-123",
            "parkinglot": "999",  # Non-existent parking lot
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T12:00:00Z"
        })
        assert response['status_code'] == 404
        data = response['json']
        assert 'error' in data
        assert data['error'] == "Parking lot not found"
    
    def test_get_reservation(self, client, mock_storage):
        """Test getting a specific reservation."""
        # First create a reservation
        reservations, _ = mock_storage
        reservations['1'] = {
            'id': '1',
            'licenseplate': 'XYZ-789',
            'parkinglot': '1',
            'startdate': '2024-07-01T10:00:00Z',
            'enddate': '2024-07-01T12:00:00Z',
            'user': 'testuser'
        }
        
        response = client.get("/reservations/1")
        assert response['status_code'] == 200
        data = response['json']
        assert data['id'] == '1'
        assert data['licenseplate'] == 'XYZ-789'
    
    def test_get_nonexistent_reservation(self, client):
        """Test getting a reservation that doesn't exist."""
        response = client.get("/reservations/999")
        assert response['status_code'] == 404
    
    def test_update_reservation(self, client, mock_storage):
        """Test updating an existing reservation."""
        # First create a reservation
        reservations, _ = mock_storage
        reservations['1'] = {
            'id': '1',
            'licenseplate': 'XYZ-789',
            'parkinglot': '1',
            'startdate': '2024-07-01T10:00:00Z',
            'enddate': '2024-07-01T12:00:00Z',
            'user': 'testuser'
        }
        
        response = client.put("/reservations/1", json={
            "licenseplate": "XYZ-789",
            "parkinglot": "1",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T13:00:00Z"  # Updated end time
        })
        assert response['status_code'] == 200
        data = response['json']
        assert data['status'] == "Updated"
        assert data['reservation']['enddate'] == "2024-07-01T13:00:00Z"
    
    def test_update_nonexistent_reservation(self, client):
        """Test updating a reservation that doesn't exist."""
        response = client.put("/reservations/999", json={
            "licenseplate": "ABC-123",
            "parkinglot": "1",
            "startdate": "2024-07-01T10:00:00Z",
            "enddate": "2024-07-01T13:00:00Z"
        })
        assert response['status_code'] == 404

    def test_delete_reservation(self, client, mock_storage):
        """Test deleting a reservation."""
        # First create a reservation
        reservations, parking_lots = mock_storage
        reservations['1'] = {
            'id': '1',
            'licenseplate': 'DEF-456',
            'parkinglot': '1',
            'startdate': '2024-07-01T10:00:00Z',
            'enddate': '2024-07-01T12:00:00Z',
            'user': 'testuser'
        }
        parking_lots['1']['reserved'] = 1
        
        response = client.delete("/reservations/1")
        assert response['status_code'] == 200
        data = response['json']
        assert data['status'] == "Deleted"
        
        # Verify deletion
        get_response = client.get("/reservations/1")
        assert get_response['status_code'] == 404
    
    def test_delete_nonexistent_reservation(self, client):
        """Test deleting a reservation that doesn't exist."""
        response = client.delete("/reservations/999")
        assert response['status_code'] == 404

