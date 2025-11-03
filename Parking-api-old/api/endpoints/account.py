import json
import hashlib
import uuid
from storage_utils import load_json, save_user_data
from session_manager import add_session, remove_session, get_session
from endpoints.baseEndpoints import BaseEndpoint

class AccountHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler)

        #[{"id":"1","username":"cindy.leenders42","password":"6b37d1ec969838d29cb611deaff50a6b","name":"Cindy Leenders",
        #"email":"cindyleenders@upcmail.nl","phone":"+310792215694","role":"USER","created_at":"2017-10-06","birth_year":1937,"active":true}

        if method == "POST" and path == "/register":
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            name = data.get("name")
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if username == user['username']:
                    request_handler.send_response(200)
                    request_handler.send_header("Content-Type", "application/json")
                    request_handler.end_headers()
                    request_handler.wfile.write(b'{"error": "Username already taken"}')
                    return

            users.append({
                'id': str(len(users) + 1),
                'username': username,
                'password': hashed_password,
                'name': name
            })
            save_user_data(users)

            request_handler.send_response(201)
            request_handler.send_header("Content-Type", "application/json")
            request_handler.end_headers()
            request_handler.wfile.write(b'{"message": "User created"}')
            return

        if method == "POST" and path == "/login":
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            if not username or not password:
                send(400)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Missing credentials")
                return
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if user.get("username") == username and user.get("password") == hashed_password:
                    token = str(uuid.uuid4())
                    add_session(token, user)
                    request_handler.send_response(200)
                    request_handler.send_header("Content-Type", "application/json")
                    request_handler.end_headers()
                    response = json.dumps({"message": "User logged in", "session_token": token}).encode("utf-8")
                    request_handler.wfile.write(response)
                    return

            request_handler.send_response(401)
            request_handler.send_header("Content-Type", "application/json")
            request_handler.end_headers()
            request_handler.wfile.write(b'{"error": "Invalid credentials"}')
            return

        if method == "GET" and path == "/logout":
            token = request_handler.headers.get('Authorization')
            if token and get_session(token):
                remove_session(token)
                send(200)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"User logged out")
                return
            send(400)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(b"Invalid session token")
            return