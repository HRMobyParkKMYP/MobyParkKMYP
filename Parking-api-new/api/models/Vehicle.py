from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='Vehicle')


class Vehicle(ModelInterface):

    def __init__(self, vid: int, user_id: int = None, license_plate: str = None,
                 make: str = None, model: str = None, color: str = None,
                 year: int = None, created_at: str = None):
        self.id = int(vid) if vid is not None and vid != '' else None
        self.user_id = int(user_id) if user_id is not None else None
        self.license_plate = license_plate
        self.make = make
        self.model = model
        self.color = color
        self.year = int(year) if year is not None else None
        self.created_at = created_at

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            vid=data.get('id'),
            user_id=data.get('user_id'),
            license_plate=data.get('license_plate') or data.get('licenseplate'),
            make=data.get('make'),
            model=data.get('model'),
            color=data.get('color'),
            year=data.get('year'),
            created_at=data.get('created_at'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'license_plate': self.license_plate,
            'make': self.make,
            'model': self.model,
            'color': self.color,
            'year': self.year,
            'created_at': self.created_at,
        }
