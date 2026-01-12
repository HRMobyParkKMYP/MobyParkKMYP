from datetime import datetime
from api.utils.database_utils import execute_query
import math
import uuid
import hashlib

def calculate_price(parkinglot, sid, data):
    """Bereken prijs voor parking sessie - uit session_calculator.py"""
    price = 0
    start = datetime.strptime(data["started"], "%Y-%m-%d %H:%M:%S")

    if data.get("stopped"):
        end = datetime.strptime(data["stopped"], "%Y-%m-%d %H:%M:%S")
    else:
        end = datetime.now()

    diff = end - start
    hours = math.ceil(diff.total_seconds() / 3600)

    if diff.total_seconds() < 180:
        price = 0
    elif end.date() > start.date():
        price = float(parkinglot.get("day_tariff", 999)) * (diff.days + 1)
    else:
        price = float(parkinglot.get("tariff")) * hours

        if price > float(parkinglot.get("day_tariff", 999)):
            price = float(parkinglot.get("day_tariff", 999))

    return (price, hours, diff.days + 1 if end.date() > start.date() else 0)


def generate_payment_hash(sid, data):
    """Genereer payment hash - met bcrypt"""
    hash_input = str(str(sid) + data["licenseplate"]).encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()

def generate_transaction_validation_hash():
    """Genereer transactie validatie hash - uit session_calculator.py"""
    return str(uuid.uuid4())


def check_payment_amount(hash):
    """Check betaald bedrag voor transactie - aangepast voor database"""
    query = """
        SELECT SUM(amount) as total 
        FROM payments 
        WHERE external_ref = ? AND status = 'completed'
    """
    result = execute_query(query, (hash,))
    return float(result[0]['total']) if result and result[0]['total'] else 0
