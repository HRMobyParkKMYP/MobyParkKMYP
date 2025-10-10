import json
from storage_utils import load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data
from session_manager import get_session
from endpoints.baseEndpoints import BaseEndpoint

class ReservationHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler, method)

        if method == "POST" and path == "/reservations":
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            reservations = load_reservation_data()
            parking_lots = load_parking_lot_data()
            rid = str(len(reservations) + 1)
            for field in ["licenseplate", "startdate", "enddate", "parkinglot"]:
                if not field in data:
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            if data.get("parkinglot", -1) not in parking_lots:
                send(404)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps({"error": "Parking lot not found", "field": "parkinglot"}).encode("utf-8"))
                return
            if 'ADMIN' == session_user.get('role'):
                if not "user" in data:
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"error": "Require field missing", "field": "user"}).encode("utf-8"))
                    return
            else:
                data["user"] = session_user["username"]
            reservations[rid] = data
            data["id"] = rid
            parking_lots[data["parkinglot"]]["reserved"] += 1
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
            send(201)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps({"status": "Success", "reservation": data}).encode("utf-8"))
            return
        
        if method == "PUT" and path.startswith("/reservations/"):
            data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
            reservations = load_reservation_data()
            rid = path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = request_handler.headers.get('Authorization')
                    if not token or not get_session(token):
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    for field in ["licenseplate", "startdate", "enddate", "parkinglot"]:
                        if not field in data:
                            send(401)
                            send_header("Content-type", "application/json")
                            end_headers()
                            w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                            return
                    if 'ADMIN' == session_user.get('role'):
                        if not "user" in data:
                            send(401)
                            send_header("Content-type", "application/json")
                            end_headers()
                            w.write(json.dumps({"error": "Require field missing", "field": "user"}).encode("utf-8"))
                            return
                    else:
                        data["user"] = session_user["username"]
                    reservations[rid] = data
                    save_reservation_data(reservations)
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"status": "Updated", "reservation": data}).encode("utf-8"))
                    return
                else:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Reservation not found")
                    return
                
        if method == "DELETE" and path.startswith("/reservations/"):
            reservations = load_reservation_data()
            parking_lots = load_parking_lot_data()
            rid = path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = request_handler.headers.get('Authorization')
                    if not token or not get_session(token):
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if "ADMIN" == session_user.get('role') or session_user["username"] == reservations[rid].get("user"):
                        del reservations[rid]
                    else:
                        send(403)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Access denied")
                        return
                    pid = reservations[rid]["parkinglot"]
                    parking_lots[pid]["reserved"] -= 1
                    save_reservation_data(reservations)
                    save_parking_lot_data(parking_lots)
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"status": "Deleted"}).encode("utf-8"))
                    return
                else:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Reservation not found")
                    return
                
        if method == "GET" and path.startswith("/reservations/"):
            reservations = load_reservation_data()
            rid = path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = request_handler.headers.get('Authorization')
                    if not token or not get_session(token):
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not "ADMIN" == session_user.get('role') and not session_user["username"] == reservations[rid].get("user"):
                        send(403)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Access denied")
                        return
                    save_reservation_data(reservations)
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps(reservations[rid]).encode("utf-8"))
                    return
                else:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Reservation not found")
                    return