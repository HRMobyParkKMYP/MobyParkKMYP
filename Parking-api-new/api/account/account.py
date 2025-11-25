from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
from models.User import User
from utils import database_utils as db
from utils import auth_utils
from utils.session_manager import add_session, remove_session, get_session

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
    
    # Check duplicates
    if db.get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username already taken")
    
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    if db.get_user_by_phone(phone):
        raise HTTPException(status_code=409, detail="Phone number already registered")
    
    hashed_password, salt = auth_utils.hash_password_bcrypt(password)
    
    # Create new user in database
    user_id = db.create_user(
        username=username,
        password_hash=hashed_password,
        name=name,
        email=email,
        phone=phone,
        birth_year=birth_year,
        role='USER',
        hash_v='bcrypt',
        salt=salt
    )
    
    return {"message": "User created", "user_id": user_id}

@router.post("/login")
async def login(request: LoginRequest):
    """Login user"""
    username = request.username
    password = request.password
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")
    
    # Get user from database
    user_data = db.get_user_by_username(username)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Convert to User model
    user = User.from_dict(user_data)
    
    # Verify password based on hash version
    hash_version = user.hash_v or 'md5'  # Default to md5 for old accounts without hash_v
    
    if not auth_utils.verify_password(password, user.password_hash, hash_version):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    token = str(uuid.uuid4())
    add_session(token, user.to_dict())
    
    return {"message": "User logged in", "session_token": token}

@router.get("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout user"""
    if not authorization:
        raise HTTPException(status_code=400, detail="Invalid session token")
    
    if authorization and get_session(authorization):
        remove_session(authorization)
        return {"message": "User logged out"}
    
    raise HTTPException(status_code=400, detail="Invalid session token")
