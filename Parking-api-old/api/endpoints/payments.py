import json
from datetime import datetime
from storage_utils import load_payment_data, save_payment_data
import session_calculator as sc
from session_manager import get_session
from endpoints.baseEndpoints import BaseEndpoint


class PaymentHandler(BaseEndpoint):
    def handle(self, request_handler, method):
        path, send, send_header, end_headers, w = self.setup(request_handler)

        if method == "POST" and path.startswith("/payments"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            payments = load_payment_data()
            session_user = get_session(token)
            data = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            if path.endswith("/refund"):
                if not 'ADMIN' == session_user.get('role'):
                    send(403)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(b"Access denied")
                    return 
                for field in ["amount"]:
                    if not field in data:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                        return
                payment = {
                    "transaction": data["transaction"] if data.get("transaction") else sc.generate_payment_hash(session_user["username"], str(datetime.now())),
                    "amount": -abs(data.get("amount", 0)),
                    "coupled_to": data.get("coupled_to"),
                    "processed_by": session_user["username"],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "completed": False,
                    "hash": sc.generate_transaction_validation_hash()
                }
            else:
                for field in ["transaction", "amount"]:
                    if not field in data:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                        return
                payment = {
                    "transaction": data.get("transaction"),
                    "amount": data.get("amount", 0),
                    "initiator": session_user["username"],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "completed": False,
                    "hash": sc.generate_transaction_validation_hash()
                }
            payments.append(payment)
            save_payment_data(payments)
            send(201)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps({"status": "Success", "payment": payment}).encode("utf-8"))
            return

        if method == "PUT" and path.startswith("/payments/"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            pid = path.replace("/payments/", "")
            payments = load_payment_data()
            session_user = get_session(token)
            data  = json.loads(request_handler.rfile.read(int(request_handler.headers.get("Content-Length", -1))))
            payment = next(p for p in payments if p["transaction"] == pid)
            if payment:
                for field in ["t_data", "validation"]:
                    if not field in data:
                        send(401)
                        send_header("Content-type", "application/json")
                        end_headers()
                        w.write(json.dumps({"error": "Require field missing", "field": field}).encode("utf-8"))
                        return
                if payment["hash"] != data.get("validation"):
                    send(401)
                    send_header("Content-type", "application/json")
                    end_headers()
                    w.write(json.dumps({"error": "Validation failed", "info": "The validation of the security hash could not be validated for this transaction."}).encode("utf-8"))
                    return
                payment["completed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payment["t_data"] = data.get("t_data", {})
                save_payment_data(payments)
                send(200)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(json.dumps({"status": "Success", "payment": payment}, default=str).encode("utf-8"))
                return
            else:
                send(404)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Payment not found!")
                return

        if method == "GET" and path == "/payments": 
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            payments = []
            session_user = get_session(token)
            for payment in load_payment_data():
                if payment.get("initiator") == session_user["username"] or payment.get("processed_by") == session_user["username"]:

                    payments.append(payment)
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(payments).encode("utf-8"))
            return
        
    
        if method == "GET" and path.startswith("/payments/"):
            token = request_handler.headers.get('Authorization')
            if not token or not get_session(token):
                send(401)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Unauthorized: Invalid or missing session token")
                return
            payments = []
            session_user = get_session(token)
            user = path.replace("/payments/", "")
            if not "ADMIN" == session_user.get('role'):
                send(403)
                send_header("Content-type", "application/json")
                end_headers()
                w.write(b"Access denied")
                return
            for payment in load_payment_data():
                if payment.get("initiator") == session_user["username"] or payment.get("processed_by") == session_user["username"]:
                    payments.append(payment)
            send(200)
            send_header("Content-type", "application/json")
            end_headers()
            w.write(json.dumps(payments).encode("utf-8"))
            return


