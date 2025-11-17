from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='User')


class User(ModelInterface):

    def __init__(self, uid: int, username: str, password_hash: str = None, name: str = None,
                 email: str = None, phone: str = None, role: str = 'USER', created_at: str = None,
                 birth_year: int = None, active: int = 1, hash_v: str = None, salt: str = None):
        self.id = int(uid) if uid is not None and uid != '' else None
        self.username = username
        self.password_hash = password_hash
        self.name = name
        self.email = email
        self.phone = phone
        self.role = role
        self.created_at = created_at
        self.birth_year = int(birth_year) if birth_year is not None else None
        self.active = int(active) if active is not None else 1
        self.hash_v = hash_v
        self.salt = salt

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            uid=data.get('id') or data.get('uID'),
            username=data.get('username'),
            password_hash=data.get('password_hash') or data.get('password'),
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            role=data.get('role', 'USER'),
            created_at=data.get('created_at'),
            birth_year=data.get('birth_year'),
            active=data.get('active', 1),
            hash_v=data.get('hash_v'),
            salt=data.get('salt'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'created_at': self.created_at,
            'birth_year': self.birth_year,
            'active': self.active,
            'hash_v': self.hash_v,
            'salt': self.salt,
        }