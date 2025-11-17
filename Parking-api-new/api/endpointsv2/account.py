from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import json
import hashlib
import uuid
from datetime import datetime
from storage_utils import load_user_data, save_user_data
from session_manager import add_session, remove_session, get_session

router = APIRouter()

# Request/Response models
class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    email: str
    phone: str
    birth_year: int

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    username = request.username
    password = request.password
    name = request.name
    email = request.email
    phone = request.phone
    birth_year = request.birth_year
    
    if not username or not password or not name or not email or not phone or not birth_year:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    users = load_user_data()
    
    # Check duplicates
    for user in users:
        if username == user['username']:
            raise HTTPException(status_code=409, detail="Username already taken")
        if email == user['email']:
            raise HTTPException(status_code=409, detail="Email already registered")
        if phone == user['phone']:
            raise HTTPException(status_code=409, detail="Phone number already registered")
    
    # Create new user
    users.append({
        'id': str(len(users) + 1),
        'username': username,
        'password': hashed_password,
        'name': name,
        'email': email,
        'phone': phone,
        'role': 'USER',
        'created_at': datetime.now().strftime("%Y-%m-%d"),
        'birth_year': birth_year,
        'active': True
    })
    save_user_data(users)
    
    return {"message": "User created"}

@router.post("/login")
async def login(request: LoginRequest):
    """Login user"""
    username = request.username
    password = request.password
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")
    
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    users = load_user_data()
    
    for user in users:
        if user.get("username") == username and user.get("password") == hashed_password:
            token = str(uuid.uuid4())
            add_session(token, user)
            return {"message": "User logged in", "session_token": token}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout user"""
    if not authorization:
        raise HTTPException(status_code=400, detail="Invalid session token")
    
    if authorization and get_session(authorization):
        remove_session(authorization)
        return {"message": "User logged out"}
    
    raise HTTPException(status_code=400, detail="Invalid session token")
