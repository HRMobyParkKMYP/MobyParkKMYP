from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='PSession')


class PSession(ModelInterface):

    def __init__(self, sid: int, parking_lot_id: int, user_id: int = None,
                 vehicle_id: int = None, license_plate: str = None, user_name: str = None,
                 started_at: str = None, stopped_at: str = None, duration_minutes: int = None,
                 cost: float = None, payment_status: str = 'unpaid'):
        self.id = int(sid) if sid is not None and sid != '' else None
        self.parking_lot_id = int(parking_lot_id) if parking_lot_id is not None else None
        self.user_id = int(user_id) if user_id is not None else None
        self.vehicle_id = int(vehicle_id) if vehicle_id is not None else None
        self.license_plate = license_plate
        self.user_name = user_name
        self.started_at = started_at
        self.stopped_at = stopped_at
        self.duration_minutes = int(duration_minutes) if duration_minutes is not None else None
        self.cost = float(cost) if cost is not None else None
        self.payment_status = payment_status

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            sid=data.get('id'),
            parking_lot_id=data.get('parking_lot_id'),
            user_id=data.get('user_id'),
            vehicle_id=data.get('vehicle_id'),
            license_plate=data.get('license_plate') or data.get('licenseplate'),
            user_name=data.get('user_name') or data.get('user'),
            started_at=data.get('started_at') or data.get('started'),
            stopped_at=data.get('stopped_at') or data.get('stopped'),
            duration_minutes=data.get('duration_minutes'),
            cost=data.get('cost'),
            payment_status=data.get('payment_status', 'unpaid'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'parking_lot_id': self.parking_lot_id,
            'user_id': self.user_id,
            'vehicle_id': self.vehicle_id,
            'license_plate': self.license_plate,
            'user_name': self.user_name,
            'started_at': self.started_at,
            'stopped_at': self.stopped_at,
            'duration_minutes': self.duration_minutes,
            'cost': self.cost,
            'payment_status': self.payment_status,
        }
