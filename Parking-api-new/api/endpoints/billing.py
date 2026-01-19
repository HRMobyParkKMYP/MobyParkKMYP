from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from utils import billing_utils
from utils.session_manager import get_session

router = APIRouter()


@router.get("/billing")
async def get_user_billing(authorization: Optional[str] = Header(None)):
    """Get billing information for the authenticated user"""
    if not authorization or not get_session(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing session token")
    
    session_user = get_session(authorization)
    user_id = session_user.get("id")
    
    try:
        sessions = billing_utils.get_user_sessions(user_id)
        return billing_utils.format_billing_data(sessions)
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
        sessions = billing_utils.get_user_sessions_by_username(username)
        return billing_utils.format_billing_data(sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
