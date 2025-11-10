import json
import hashlib
from storage_utils import save_user_data
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
            data["username"] = session_user["username"]
            if data["password"]:
                data["password"] = hashlib.md5(data["password"].encode()).hexdigest()
            save_user_data(data)
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
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(session_user).encode('utf-8'))