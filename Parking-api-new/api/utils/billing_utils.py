from typing import List, Dict, Any
from api.utils.database_utils import execute_query
from api.utils import session_calculator


def get_user_sessions(user_id: int) -> List[Dict[str, Any]]:
    """Haal sessies op voor gebruiker met parking lot info"""
    query = """
        SELECT 
            s.id as session_id,
            s.license_plate as licenseplate,
            s.started_at as started,
            s.stopped_at as stopped,
            pl.name,
            pl.location,
            pl.tariff,
            pl.day_tariff as daytariff
        FROM p_sessions s
        JOIN parking_lots pl ON s.parking_lot_id = pl.id
        WHERE s.user_id = ?
        ORDER BY s.started_at DESC
    """
    return execute_query(query, (user_id,))


def get_user_sessions_by_username(username: str) -> List[Dict[str, Any]]:
    """Haal sessies op voor specifieke gebruiker met parking lot info"""
    query = """
        SELECT 
            s.id as session_id,
            s.license_plate as licenseplate,
            s.started_at as started,
            s.stopped_at as stopped,
            pl.name,
            pl.location,
            pl.tariff,
            pl.day_tariff as daytariff
        FROM p_sessions s
        JOIN parking_lots pl ON s.parking_lot_id = pl.id
        JOIN users u ON s.user_id = u.id
        WHERE u.username = ?
        ORDER BY s.started_at DESC
    """
    return execute_query(query, (username,))


def format_billing_data(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format sessie data naar billing response"""
    data = []
    for row in sessions:
        # Maak parkinglot en session dicts voor calculate_price
        parkinglot = {
            "name": row["name"],
            "location": row["location"],
            "tariff": row["tariff"],
            "daytariff": row["daytariff"]
        }
        
        session = {
            "licenseplate": row["licenseplate"],
            "started": row["started"],
            "stopped": row["stopped"]
        }
        
        # Bereken prijs, uren en dagen
        amount, hours, days = session_calculator.calculate_price(parkinglot, row["session_id"], session)
        transaction = session_calculator.generate_payment_hash(row["session_id"], session)
        payed = session_calculator.check_payment_amount(transaction)
        
        data.append({
            "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
            "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
            "amount": amount,
            "thash": transaction,
            "payed": payed,
            "balance": amount - payed
        })
    
    return data