from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from utils import billing_utils
from utils.session_manager import get_session
from utils.database_utils import execute_query

router = APIRouter()


@router.get("/billing")
async def get_user_billing(authorization: Optional[str] = Header(None)):
    """Get billing information for the authenticated user"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    try:
        # Haal sessies op voor gebruiker met parking lot info
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
        sessions = execute_query(query, (user_id,))
        
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
            amount, hours, days = billing_utils.calculate_price(parkinglot, row["session_id"], session)
            transaction = billing_utils.generate_payment_hash(row["session_id"], session)
            payed = billing_utils.check_payment_amount(transaction)
            
            data.append({
                "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
                "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
                "amount": amount,
                "thash": transaction,
                "payed": payed,
                "balance": amount - payed
            })
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/billing/{username}")
async def get_user_billing_by_username(username: str, authorization: Optional[str] = Header(None)):
    """Get billing information for a specific user (admin only)"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    
    if session_user.get('role') != 'ADMIN':
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Haal sessies op voor specifieke gebruiker met parking lot info
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
        sessions = execute_query(query, (username,))
        
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
            amount, hours, days = billing_utils.calculate_price(parkinglot, row["session_id"], session)
            transaction = billing_utils.generate_payment_hash(row["session_id"], session)
            payed = billing_utils.check_payment_amount(transaction)
            
            data.append({
                "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
                "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
                "amount": amount,
                "thash": transaction,
                "payed": payed,
                "balance": amount - payed
            })
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
