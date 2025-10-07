import json
import hashlib
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from storage_utils import load_json, save_data, save_user_data, load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data, load_payment_data, save_payment_data
from session_manager import add_session, remove_session, get_session
import session_calculator as sc

class BillingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/billing":
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Unauthorized: Invalid or missing session token")
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
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
            return
        

        elif self.path.startswith("/billing/"):
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Unauthorized: Invalid or missing session token")
                return
            data = []
            session_user = get_session(token)
            user = self.path.replace("/billing/", "")
            if not "ADMIN" == session_user.get('role'):
                self.send_response(403)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Access denied")
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
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
            return