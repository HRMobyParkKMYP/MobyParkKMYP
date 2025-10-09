import json
from storage_utils import load_json, load_parking_lot_data
from session_manager import get_session
import session_calculator as sc
from endpoints.baseEndpoints import BaseEndpoint

class BillingHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler, method)

        if method == "GET" and path == "/billing":
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            data = []
            session_user = get_session(token)
            for pid, parkinglot in load_parking_lot_data().items():
                for sid, session in load_json(f'data/pdata/p{pid}-sessions.json').items():
                    if session["user"] == session_user["username"]:
                        amount, hours, days = sc.calculate_price(parkinglot, sid, session)
                        transaction = sc.generate_payment_hash(sid, session)
                        payed = sc.check_payment_amount(transaction)
                        data.append({
                            "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
                            "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
                            "amount": amount,
                            "thash": transaction,
                            "payed": payed,
                            "balance": amount - payed
                        })
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(data, default=str).encode("utf-8"))
            return
        

        if method == "GET" and path.startswith("/billing/"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            data = []
            session_user = get_session(token)
            user = path.replace("/billing/", "")
            if not "ADMIN" == session_user.get('role'):
                send(403)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Access denied")
                return
            for pid, parkinglot in load_parking_lot_data().items():
                for sid, session in load_json(f'data/pdata/p{pid}-sessions.json').items():
                    if session["user"] == user:
                        amount, hours, days = sc.calculate_price(parkinglot, sid, session)
                        transaction = sc.generate_payment_hash(sid, session)
                        payed = sc.check_payment_amount(transaction)
                        data.append({
                            "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
                            "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
                            "amount": amount,
                            "thash": transaction,
                            "payed": payed,
                            "balance": amount - payed
                        })
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(data, default=str).encode("utf-8"))
            return