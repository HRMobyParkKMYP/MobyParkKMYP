from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='ParkingLot')


class ParkingLot(ModelInterface):

    def __init__(self, pid: int, name: str, location: str = None, address: str = None,
                 capacity: int = 0, reserved: int = 0, tariff: float = 0.0,
                 day_tariff: float = 0.0, created_at: str = None, lat: float = None, lng: float = None):
        self.id = int(pid) if pid is not None and pid != '' else None
        self.name = name
        self.location = location
        self.address = address
        self.capacity = int(capacity) if capacity is not None else 0
        self.reserved = int(reserved) if reserved is not None else 0
        self.tariff = float(tariff) if tariff is not None else 0.0
        self.day_tariff = float(day_tariff) if day_tariff is not None else 0.0
        self.created_at = created_at
        self.lat = float(lat) if lat is not None else None
        self.lng = float(lng) if lng is not None else None

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            pid=data.get('id'),
            name=data.get('name'),
            location=data.get('location'),
            address=data.get('address'),
            capacity=data.get('capacity', 0),
            reserved=data.get('reserved', 0),
            tariff=data.get('tariff'),
            day_tariff=data.get('day_tariff') or data.get('daytariff'),
            created_at=data.get('created_at'),
            lat=data.get('lat'),
            lng=data.get('lng'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'address': self.address,
            'capacity': self.capacity,
            'reserved': self.reserved,
            'tariff': self.tariff,
            'day_tariff': self.day_tariff,
            'created_at': self.created_at,
            'lat': self.lat,
            'lng': self.lng,
        }
