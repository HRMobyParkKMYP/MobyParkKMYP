import json
import hashlib
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from storage_utils import load_json, save_data, save_user_data, load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data, load_payment_data, save_payment_data
from session_manager import add_session, remove_session, get_session
import session_calculator as sc

class ReservationHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/reservations":
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            reservations = load_reservation_data()
            parking_lots = load_parking_lot_data()
            rid = str(len(reservations) + 1)
            for field in ["licenseplate", "startdate", "enddate", "parkinglot"]:
                if not field in data:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            if data.get("parkinglot", -1) not in parking_lots:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Parking lot not found", "field": "parkinglot"}).encode("utf-8"))
                return
            if 'ADMIN' == session_user.get('role'):
                if not "user" in data:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Require field missing", "field": "user"}).encode("utf-8"))
                    return
            else:
                data["user"] = session_user["username"]
            reservations[rid] = data
            data["id"] = rid
            parking_lots[data["parkinglot"]]["reserved"] += 1
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "Success", "reservation": data}).encode("utf-8"))
            return
        
    def do_PUT(self):
        if self.path.startswith("/reservations/"):
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            reservations = load_reservation_data()
            rid = self.path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    for field in ["licenseplate", "startdate", "enddate", "parkinglot"]:
                        if not field in data:
                            self.send_response(401)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                            return
                    if 'ADMIN' == session_user.get('role'):
                        if not "user" in data:
                            self.send_response(401)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": "Require field missing", "field": "user"}).encode("utf-8"))
                            return
                    else:
                        data["user"] = session_user["username"]
                    reservations[rid] = data
                    save_reservation_data(reservations)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "Updated", "reservation": data}).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Reservation not found")
                    return
                
    def do_DELETE(self):
        if self.path.startswith("/reservations/"):
            reservations = load_reservation_data()
            parking_lots = load_parking_lot_data()
            rid = self.path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if "ADMIN" == session_user.get('role') or session_user["username"] == reservations[rid].get("user"):
                        del reservations[rid]
                    else:
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    pid = reservations[rid]["parkinglot"]
                    parking_lots[pid]["reserved"] -= 1
                    save_reservation_data(reservations)
                    save_parking_lot_data(parking_lots)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "Deleted"}).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Reservation not found")
                    return
                
    def do_GET(self):
        if self.path.startswith("/reservations/"):
            reservations = load_reservation_data()
            rid = self.path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not "ADMIN" == session_user.get('role') and not session_user["username"] == reservations[rid].get("user"):
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    save_reservation_data(reservations)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(reservations[rid]).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Reservation not found")
                    return