import json
import hashlib
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from storage_utils import load_json, save_data, save_user_data, load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data, load_payment_data, save_payment_data
from session_manager import add_session, remove_session, get_session
import session_calculator as sc

class ParkingLotHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.startswith("/parking-lots"):
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            if 'sessions' in self.path:
                lid = self.path.split("/")[2]
                data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
                sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                if self.path.endswith('start'):
                    if 'licenseplate' not in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Require field missing", "field": 'licenseplate'}).encode("utf-8"))
                        return
                    filtered = {key: value for key, value in sessions.items() if value.get("licenseplate") == data['licenseplate'] and not value.get('stopped')}
                    if len(filtered) > 0:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'Cannot start a session when another sessions for this licesenplate is already started.')
                        return 
                    session = {
                        "licenseplate": data['licenseplate'],
                        "started": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                        "stopped": None,
                        "user": session_user["username"]
                    }
                    sessions[str(len(sessions) + 1)] = session
                    save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(f"Session started for: {data['licenseplate']}".encode('utf-8'))

                elif self.path.endswith('stop'):
                    if 'licenseplate' not in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Require field missing", "field": 'licenseplate'}).encode("utf-8"))
                        return
                    filtered = {key: value for key, value in sessions.items() if value.get("licenseplate") == data['licenseplate'] and not value.get('stopped')}
                    if len(filtered) < 0:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'Cannot stop a session when there is no session for this licesenplate.')
                        return
                    sid = next(iter(filtered))
                    sessions[sid]["stopped"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(f"Session stopped for: {data['licenseplate']}".encode('utf-8'))

            else:
                if not 'ADMIN' == session_user.get('role'):
                    self.send_response(403)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Access denied")
                    return
                data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
                parking_lots = load_parking_lot_data()
                new_lid = str(len(parking_lots) + 1)
                parking_lots[new_lid] = data
                save_parking_lot_data(parking_lots)
                self.send_response(201)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(f"Parking lot saved under ID: {new_lid}".encode('utf-8'))

    def do_PUT(self):
        if self.path.startswith("/parking-lots/"):
            lid = self.path.split("/")[2]
            parking_lots = load_parking_lot_data()
            if lid:
                if lid in parking_lots:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not 'ADMIN' == session_user.get('role'):
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
                    parking_lots[lid] = data
                    save_parking_lot_data(parking_lots)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot modified")
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot not found")
                    return
                
    def do_DELETE(self):
        if self.path.startswith("/parking-lots/"):
            lid = self.path.split("/")[2]
            parking_lots = load_parking_lot_data()
            if lid:
                if lid in parking_lots:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not 'ADMIN' == session_user.get('role'):
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    if 'sessions' in self.path:
                        sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                        sid = self.path.split("/")[-1]
                        if sid.isnumeric():
                            del sessions[sid]
                            save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                            self.send_response(200)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(b"Sessions deleted")
                        else:
                            self.send_response(403)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(b"Session ID is required, cannot delete all sessions")
                    else:
                        del parking_lots[lid]
                        save_parking_lot_data(parking_lots)
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Parking lot deleted")
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot not found")
                    return
                
    def do_GET(self):
        if self.path.startswith("/parking-lots/"):
            lid = self.path.split("/")[2]
            parking_lots = load_parking_lot_data()
            token = self.headers.get('Authorization')
            if lid:
                if lid not in parking_lots:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot not found")
                    return
                if 'sessions' in self.path:
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Unauthorized: Invalid or missing session token")
                        return
                    sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                    rsessions = []
                    if self.path.endswith('/sessions'):
                        if "ADMIN" == session_user.get('role'):
                            rsessions = sessions
                        else:
                            for session in sessions:
                                if session['user'] == session_user['username']:
                                    rsessions.append(session)
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(rsessions).encode('utf-8'))  
                    else:
                        sid = self.path.split("/")[-1]
                        if not "ADMIN" == session_user.get('role') and not session_user["username"] == sessions[sid].get("user"):
                            self.send_response(403)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(b"Access denied")
                            return
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(sessions[sid]).encode('utf-8'))
                        return
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(parking_lots[lid]).encode('utf-8'))
                    return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(parking_lots).encode('utf-8'))