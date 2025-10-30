import json
from datetime import datetime
from storage_utils import load_json, save_data
from session_manager import get_session
from endpoints.baseEndpoints import BaseEndpoint

class VehicleHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler)

        # POST /vehicles voegt een nieuw voertuig toe aan users account
        if method == "POST" and path == "/vehicles":
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            vehicles = load_json("data/vehicles.json")
            uvehicles = [v for v in vehicles if v.get("user_id") == session_user.get("id")]
            # Checkt of verplichte velden aanwezig zijn
            for field in ["name", "license_plate"]:
                if not field in data:
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            lid = data["license_plate"].replace("-", "")
            # Checkt of voertuig al bestaat
            if lid in uvehicles:
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps({"error": "Vehicle already exists", "data": uvehicles.get(lid)}).encode("utf-8"))
                return
            # Voegt voertuig toe aan de gebruikerslijst
            new_vehicle = {
                "id": str(len(vehicles) + 1),
                "user_id": session_user.get("id"),
                "license_plate": data["license_plate"],
                "name": data["name"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            vehicles.append(new_vehicle)
            save_data("data/vehicles.json", vehicles)
            send(201)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps({"status": "Success", "vehicle": data}).encode("utf-8"))
            return

        # POST /vehicles/<id>/entry registreert de entry tot een parkeerplaats van een voertuig
        if method == "POST" and path.startswith("/vehicles/"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            vehicles = load_json("data/vehicles.json")
            uvehicles = [v for v in vehicles if v.get("user_id") == session_user.get("id")]
            # Checkt of verplichte velden aanwezig zijn
            for field in ["parkinglot"]:
                if not field in data:
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            lid = path.replace("/vehicles/", "").replace("/entry", "")
            # Checkt of voertuig bestaat
            if lid not in uvehicles:
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps({"error": "Vehicle does not exist", "data": lid}).encode("utf-8"))
                return
            # Registreert de entry
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps({"status": "Accepted", "vehicle": vehicles[session_user["username"]][lid]}).encode("utf-8"))
            return
        
        if method == "PUT" and path.startswith("/vehicles/"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            vehicles = load_json("data/vehicles.json")
            uvehicles = vehicles.get(session_user["username"], {})
            for field in ["name"]:
                if not field in data:
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            lid = path.replace("/vehicles/", "")
            if not uvehicles:
                vehicles[session_user["username"]] = {}
            if lid not in uvehicles:
                vehicles[session_user["username"]][lid] = {
                    "licenseplate": data.get("license_plate"),
                    "name": data["name"],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            vehicles[session_user["username"]][lid]["name"] = data["name"]
            vehicles[session_user["username"]][lid]["updated_at"] = datetime.now()
            save_data("data/vehicles.json", vehicles)
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps({"status": "Success", "vehicle": vehicles[session_user["username"]][lid]}, default=str).encode("utf-8"))
            return
        
        if method == "DELETE" and path.startswith("/vehicles/"):
            lid = path.replace("/vehicles/", "")
            if lid:
                token = request_handler.headers.get('Authorization')
                if not token or not get_session(token):
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Unauthorized: Invalid or missing session token")
                    return
                session_user = get_session(token)
                vehicles = load_json("data/vehicles.json")
                uvehicles = vehicles.get(session_user["username"], {})
                if lid not in uvehicles:
                    send(403)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Vehicle not found!")
                    return
                del vehicles[session_user["username"]][lid]
                save_data("data/vehicles.json", vehicles)
                send(200)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps({"status": "Deleted"}).encode("utf-8"))
                return
            
        if method == "GET" and path.startswith("/vehicles"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            if path.endswith("/reservations"):
                vid = path.split("/")[2]
                vehicles = load_json("data/vehicles.json")
                uvehicles = vehicles.get(session_user["username"], {}) 
                if vid not in uvehicles:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Not found!")
                    return
                send(200)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps([]).encode("utf-8"))
                return
            elif path.endswith("/history"):
                vid = path.split("/")[2]
                vehicles = load_json("data/vehicles.json")
                uvehicles = vehicles.get(session_user["username"], {})
                if vid not in uvehicles:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Not found!")
                    return
                send(200)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps([]).encode("utf-8"))
                return
            else:
                vehicles = load_json("data/vehicles.json")
                users = load_json('data/users.json')
                user = session_user["username"]
                if "ADMIN" == session_user.get("role") and path != "/vehicles":
                    user = path.replace("/vehicles/", "")
                    if user not in [u["username"] for u in users]:
                        send(404)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"User not found")
                        return
                    user_vehicles = [v for v in vehicles if v.get("user_id") == session_user.get("id")]
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps(user_vehicles, default=str).encode("utf-8"))
                    return