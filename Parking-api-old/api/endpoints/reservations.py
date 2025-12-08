import json
from storage_utils import load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data
from session_manager import get_session
from endpoints.baseEndpoints import BaseEndpoint

class ReservationHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler)

        def _ensure_reservations_dict(reservations):
            # No more list-to-dict conversion madness
            if isinstance(reservations, dict):
                return reservations
            return {}

        def _read_json_body():
            try:
                length = int(request_handler.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length <= 0:
                return {}

            raw = request_handler.rfile.read(length)
            try:
                body = json.loads(raw.decode('utf-8'))
                return body if isinstance(body, dict) else {}
            except Exception:
                return {}

        # POST /reservations
        if method == "POST" and path == "/reservations":
            token = request_handler.headers.get('Authorization')
            if not token:
                send(401); send_header("Content-type", "application/json"); end_headers()
                w.write(b'{"error":"Unauthorized: missing token"}')
                return
            session_user = get_session(token)
            if not session_user or not isinstance(session_user, dict):
                send(401); send_header("Content-type", "application/json"); end_headers()
                w.write(b'{"error":"Unauthorized: invalid session"}')
                return

            data = _read_json_body()
            reservations = _ensure_reservations_dict(load_reservation_data())
            parking_lots = load_parking_lot_data() or {}

            for field in ("licenseplate", "startdate", "enddate", "parkinglot"):
                if field not in data:
                    send(400); send_header("Content-type", "application/json"); end_headers()
                    w.write(json.dumps({"error": "Required field missing", "field": field}).encode("utf-8"))
                    return

            pid = str(data.get("parkinglot"))
            if pid not in parking_lots:
                send(404); send_header("Content-type", "application/json"); end_headers()
                w.write(json.dumps({"error": "Parking lot not found", "field": "parkinglot"}).encode("utf-8"))
                return

            if session_user.get("role") == "ADMIN":
                if "user" not in data:
                    send(400); send_header("Content-type", "application/json"); end_headers()
                    w.write(json.dumps({"error": "Required field missing", "field": "user"}).encode("utf-8"))
                    return
            else:
                data["user"] = session_user.get("username")

            # new id (string!)
            new_id = str(len(reservations) + 1)
            data["id"] = new_id
            reservations[new_id] = data

            parking_lots.setdefault(pid, {}).setdefault("reserved", 0)
            parking_lots[pid]["reserved"] = parking_lots[pid].get("reserved", 0) + 1

            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)

            send(201); send_header("Content-type", "application/json"); end_headers()
            w.write(json.dumps({"status": "Success", "reservation": data}).encode("utf-8"))
            return

        # Endpoints with /reservations/<rid>
        if path.startswith("/reservations/"):
            rid = path.replace("/reservations/", "").strip()
            reservations = _ensure_reservations_dict(load_reservation_data())
            parking_lots = load_parking_lot_data() or {}

            if method in ("PUT", "DELETE", "GET"):
                token = request_handler.headers.get('Authorization')
                if not token:
                    send(401); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Unauthorized: missing token"}')
                    return
                session_user = get_session(token)
                if not session_user or not isinstance(session_user, dict):
                    send(401); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Unauthorized: invalid session"}')
                    return

            # PUT update
            if method == "PUT":
                if not rid:
                    send(400); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"No reservation id provided"}')
                    return
                if rid not in reservations:
                    send(404); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Reservation not found"}')
                    return

                data = _read_json_body()
                for field in ("licenseplate", "startdate", "enddate", "parkinglot"):
                    if field not in data:
                        send(400); send_header("Content-type", "application/json"); end_headers()
                        w.write(json.dumps({"error": "Required field missing", "field": field}).encode("utf-8"))
                        return

                if session_user.get("role") == "ADMIN":
                    if "user" not in data:
                        send(400); send_header("Content-type", "application/json"); end_headers()
                        w.write(json.dumps({"error": "Required field missing", "field": "user"}).encode("utf-8"))
                        return
                else:
                    data["user"] = session_user.get("username")

                data["id"] = rid
                reservations[rid] = data
                save_reservation_data(reservations)

                send(200); send_header("Content-type", "application/json"); end_headers()
                w.write(json.dumps({"status": "Updated", "reservation": data}).encode("utf-8"))
                return

            # DELETE
            if method == "DELETE":
                if not rid:
                    send(400); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"No reservation id provided"}')
                    return
                if rid not in reservations:
                    send(404); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Reservation not found"}')
                    return

                if session_user.get("role") != "ADMIN" and session_user.get("username") != reservations[rid].get("user"):
                    send(403); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Access denied"}')
                    return

                pid = str(reservations[rid].get("parkinglot"))

                del reservations[rid]

                if pid in parking_lots:
                    parking_lots[pid]["reserved"] = max(0, parking_lots[pid].get("reserved", 1) - 1)

                save_reservation_data(reservations)
                save_parking_lot_data(parking_lots)

                send(200); send_header("Content-type", "application/json"); end_headers()
                w.write(json.dumps({"status": "Deleted"}).encode("utf-8"))
                return

            # GET
            if method == "GET":
                if not rid:
                    send(400); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"No reservation id provided"}')
                    return
                if rid not in reservations:
                    send(404); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Reservation not found"}')
                    return

                if session_user.get("role") != "ADMIN" and session_user.get("username") != reservations[rid].get("user"):
                    send(403); send_header("Content-type", "application/json"); end_headers()
                    w.write(b'{"error":"Access denied"}')
                    return

                send(200); send_header("Content-type", "application/json"); end_headers()
                w.write(json.dumps(reservations[rid]).encode("utf-8"))
                return

        send(404); send_header("Content-type", "application/json"); end_headers()
        w.write(b'{"error":"Not found"}')
