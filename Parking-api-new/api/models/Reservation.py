from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='Reservation')


class Reservation(ModelInterface):

    def __init__(self, rid: int, user_id: int = None, parking_lot_id: int = None,
                 vehicle_id: int = None, start_time: str = None, end_time: str = None,
                 status: str = 'pending', created_at: str = None, cost: float = None):
        self.id = int(rid) if rid is not None and rid != '' else None
        self.user_id = int(user_id) if user_id is not None else None
        self.parking_lot_id = int(parking_lot_id) if parking_lot_id is not None else None
        self.vehicle_id = int(vehicle_id) if vehicle_id is not None else None
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.created_at = created_at
        self.cost = float(cost) if cost is not None else None

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            rid=data.get('id'),
            user_id=data.get('user_id'),
            parking_lot_id=data.get('parking_lot_id') or data.get('parkinglot'),
            vehicle_id=data.get('vehicle_id'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            status=data.get('status', 'pending'),
            created_at=data.get('created_at'),
            cost=data.get('cost'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'parking_lot_id': self.parking_lot_id,
            'vehicle_id': self.vehicle_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status,
            'created_at': self.created_at,
            'cost': self.cost,
        }
