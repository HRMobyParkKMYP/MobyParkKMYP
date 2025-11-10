import json
import hashlib
from storage_utils import save_user_data, load_json
from session_manager import get_session
from endpoints.baseEndpoints import BaseEndpoint

class ProfileHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler)

        if method == "PUT" and path == "/profile":
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            users = load_json('data/users.json')
            for user in users:
                if user["username"] == session_user["username"]:
                    # Update only the provided fields
                    if "password" in data and data["password"]:
                        user["password"] = hashlib.md5(data["password"].encode()).hexdigest()
                    if "name" in data:
                        user["name"] = data["name"]
                    if "email" in data:
                        user["email"] = data["email"]
                    if "phone" in data:
                        user["phone"] = data["phone"]
                    if "birth_year" in data:
                        user["birth_year"] = data["birth_year"]
                    break
            save_user_data(users)
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(b"User updated succesfully")

        if method == "GET" and path == "/profile":
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            username = session_user["username"]
            users = load_json('data/users.json')
            user_data = next((u for u in users if u["username"] == username), None)
            if not user_data:
                send(404)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"User not found")
                return
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(user_data).encode("utf-8"))
            return