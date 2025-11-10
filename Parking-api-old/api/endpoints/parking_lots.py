import json
from datetime import datetime
from storage_utils import load_json, save_data, load_parking_lot_data, save_parking_lot_data
from session_manager import get_session
from endpoints.baseEndpoints import BaseEndpoint

class ParkingLotHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler)

        if method == "POST" and path.startswith("/parking-lots"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            if 'sessions' in path:
                lid = path.split("/")[2]
                data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
                sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                if path.endswith('start'):
                    if 'licenseplate' not in data:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps({"error": "Require field missing", "field": 'licenseplate'}).encode("utf-8"))
                        return
                    filtered = {key: value for key, value in sessions.items() if value.get("licenseplate") == data['licenseplate'] and not value.get('stopped')}
                    if len(filtered) > 0:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b'Cannot start a session when another sessions for this licesenplate is already started.')
                        return 
                    session = {
                        "licenseplate": data['licenseplate'],
                        "started": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                        "stopped": None,
                        "user": session_user["username"]
                    }
                    sessions[str(len(sessions) + 1)] = session
                    save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(f"Session started for: {data['licenseplate']}".encode('utf-8'))

                elif path.endswith('stop'):
                    if 'licenseplate' not in data:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps({"error": "Require field missing", "field": 'licenseplate'}).encode("utf-8"))
                        return
                    filtered = {key: value for key, value in sessions.items() if value.get("licenseplate") == data['licenseplate'] and not value.get('stopped')}
                    if len(filtered) < 0:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b'Cannot stop a session when there is no session for this licesenplate.')
                        return
                    sid = next(iter(filtered))
                    sessions[sid]["stopped"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(f"Session stopped for: {data['licenseplate']}".encode('utf-8'))

            else:
                if not 'ADMIN' == session_user.get('role'):
                    send(403)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Access denied")
                    return
                data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
                parking_lots = load_parking_lot_data()
                new_lid = str(len(parking_lots) + 1)
                parking_lots[new_lid] = data
                save_parking_lot_data(parking_lots)
                send(201)
                end_headers("Content-type", "application/json")
                end_headers()
                w.write(f"Parking lot saved under ID: {new_lid}".encode('utf-8'))

        if method == "PUT" and path.startswith("/parking-lots/"):
            lid = path.split("/")[2]
            parking_lots = load_parking_lot_data()
            if lid:
                if lid in parking_lots:
                    token = request_handler.headers.get('Authorization')
                    if not token or not get_session(token):
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not 'ADMIN' == session_user.get('role'):
                        send(403)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Access denied")
                        return
                    data  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", -1))))
                    parking_lots[lid] = data
                    save_parking_lot_data(parking_lots)
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Parking lot modified")
                else:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Parking lot not found")
                    return
                
        if method == "DELETE" and path.startswith("/parking-lots/"):
            lid = path.split("/")[2]
            parking_lots = load_parking_lot_data()
            if lid:
                if lid in parking_lots:
                    token = request_handler.headers.get('Authorization')
                    if not token or not get_session(token):
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not 'ADMIN' == session_user.get('role'):
                        send(403)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Access denied")
                        return
                    if 'sessions' in path:
                        sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                        sid = path.split("/")[-1]
                        if sid.isnumeric():
                            del sessions[sid]
                            save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                            send(200)
                            send_header("Content-type", "application/json")
                            end_headers()
                            w.write(b"Sessions deleted")
                        else:
                            send(403)
                            send_header("Content-type", "application/json")
                            end_headers()
                            w.write(b"Session ID is required, cannot delete all sessions")
                    else:
                        del parking_lots[lid]
                        save_parking_lot_data(parking_lots)
                        send(200)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Parking lot deleted")
                else:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Parking lot not found")
                    return
                
        if method == "GET" and path.startswith("/parking-lots/"):
            lid = path.split("/")[2]
            parking_lots = load_parking_lot_data()
            token = request_handler.headers.get('Authorization')
            if lid:
                if lid not in parking_lots:
                    send(404)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Parking lot not found")
                    return
                if 'sessions' in path:
                    if not token or not get_session(token):
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(b"Unauthorized: Invalid or missing session token")
                        return
                    sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                    rsessions = []
                    if path.endswith('/sessions'):
                        if "ADMIN" == session_user.get('role'):
                            rsessions = sessions
                        else:
                            for session in sessions:
                                if session['user'] == session_user['username']:
                                    rsessions.append(session)
                        send(200)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps(rsessions).encode('utf-8'))
                    else:
                        sid = path.split("/")[-1]
                        if not "ADMIN" == session_user.get('role') and not session_user["username"] == sessions[sid].get("user"):
                            send(403)
                            send_header("Content-type", "application/json")
                            end_headers()
                            w.write(b"Access denied")
                            return
                        send(200)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps(sessions[sid]).encode('utf-8'))
                        return
                else:
                    send(200)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps(parking_lots[lid]).encode('utf-8'))
                    return
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(parking_lots).encode('utf-8'))