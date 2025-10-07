import json
import hashlib
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from storage_utils import load_json, save_data, save_user_data, load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data, load_payment_data, save_payment_data
from session_manager import add_session, remove_session, get_session
import session_calculator as sc

class AccountHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/register":
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            name = data.get("name")
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if username == user['username']:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Username already taken")
                    return
            users.add({
                'username': username,
                'password': hashed_password,
                'name': name
            })
            save_user_data(users)
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"User created")


        elif self.path == "/login":
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            if not username or not password:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Missing credentials")
                return
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if user.get("username") == username and user.get("password") == hashed_password:
                    token = str(uuid.uuid4())
                    add_session(token, user)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"message": "User logged in", "session_token": token}).encode('utf-8'))
                    return
                else:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Invalid credentials")
                    return
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"User not found")

    def do_GET(self):
        if self.path == "/logout":
            token = self.headers.get('Authorization')
            if token and get_session(token):
                remove_session(token)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"User logged out")
                return
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"Invalid session token")