import json
import hashlib
import uuid
from storage_utils import load_json, save_user_data
from session_manager import add_session, remove_session, get_session
from endpoints.baseEndpoints import BaseEndpoint

class AccountHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler, method)

        if method == "POST" and path == "/register":
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            name = data.get("name")
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if username == user['username']:
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Username already taken")
                    return
            users.add({
                'username': username,
                'password': hashed_password,
                'name': name
            })
            save_user_data(users)
            send(201)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(b"User created")
            return

        if method == "POST" and path == "/login":
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
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
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"message": "User logged in", "session_token": token}).encode('utf-8'))
                    return
                else:
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Invalid credentials")
                    return
            send(401)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(b"User not found")
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