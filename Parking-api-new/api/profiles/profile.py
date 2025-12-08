from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from models.User import User
from utils import database_utils as db
from utils import auth_utils
from utils.session_manager import get_session, update_session

router = APIRouter()

class ProfileUpdateRequest(BaseModel):
    password: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_year: Optional[int] = None

@router.get("/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    """
    Get the profile of the logged-in user.
    Requires `Authorization` header with a valid session token.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Invalid session token")

    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Invalid session token")

    username = session_user.get("username")
    user_row = db.get_user_by_username(username)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    user = User.from_dict(user_row)
    out = user.to_dict()
    # Do not expose password_hash or salt
    out.pop("password_hash", None)
    out.pop("salt", None)
    out.pop("hash_v", None)
    return out


@router.put("/profile")
async def update_profile(data: ProfileUpdateRequest, authorization: Optional[str] = Header(None)):
    """
    Update profile fields for the logged-in user.
    Fields: password, name, email, phone, birth_year
    Password will be hashed with bcrypt and stored encrypted (consistent with auth_utils).
    Session is automatically refreshed with updated user data.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Invalid session token")

    session_user = get_session(authorization)
    if not session_user:
        raise HTTPException(status_code=401, detail="Invalid session token")

    username = session_user.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session token")

    # Validate non-empty values if provided
    for field_name in ["password", "name", "email", "phone"]:
        val = getattr(data, field_name, None)
        if val is not None:
            if isinstance(val, str) and val.strip() == "":
                raise HTTPException(status_code=400, detail=f"{field_name} cannot be empty")

    # If changing email or phone, ensure uniqueness
    if data.email:
        existing = db.get_user_by_email(data.email)
        if existing and existing.get("username") != username:
            raise HTTPException(status_code=409, detail="Email already registered")

    if data.phone:
        existing = db.get_user_by_phone(data.phone)
        if existing and existing.get("username") != username:
            raise HTTPException(status_code=409, detail="Phone already registered")

    # Build update fields
    update_fields = {}
    session_updates = {}

    if data.password:
        hashed, salt = auth_utils.hash_password_bcrypt(data.password)
        update_fields["password_hash"] = hashed
        update_fields["salt"] = salt
        update_fields["hash_v"] = "bcrypt"
        # Don't expose password in session

    if data.name is not None:
        update_fields["name"] = data.name
        session_updates["name"] = data.name

    if data.email is not None:
        update_fields["email"] = data.email
        session_updates["email"] = data.email

    if data.phone is not None:
        update_fields["phone"] = data.phone
        session_updates["phone"] = data.phone

    if data.birth_year is not None:
        update_fields["birth_year"] = data.birth_year
        session_updates["birth_year"] = data.birth_year

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Update user in database
    rows = db.update_user_by_username(username, update_fields)
    if rows == 0:
        raise HTTPException(status_code=404, detail="User not found")

    # Refresh session with updated data
    if session_updates:
        update_session(authorization, session_updates)

    return {"message": "User updated successfully"}
