from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='Discount')


class Discount(ModelInterface):

    def __init__(self, did: int, code: str = None, description: str = None,
                 percent: float = None, amount: float = None, applies_to: str = 'both',
                 starts_at: str = None, ends_at: str = None, parking_lot_id: int = None):
        self.id = int(did) if did is not None and did != '' else None
        self.code = code
        self.description = description
        self.percent = float(percent) if percent is not None else None
        self.amount = float(amount) if amount is not None else None
        self.applies_to = applies_to
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.parking_lot_id = int(parking_lot_id) if parking_lot_id is not None else None

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            did=data.get('id'),
            code=data.get('code'),
            description=data.get('description'),
            percent=data.get('percent'),
            amount=data.get('amount'),
            applies_to=data.get('applies_to', 'both'),
            starts_at=data.get('starts_at'),
            ends_at=data.get('ends_at'),
            parking_lot_id=data.get('parking_lot_id'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'percent': self.percent,
            'amount': self.amount,
            'applies_to': self.applies_to,
            'starts_at': self.starts_at,
            'ends_at': self.ends_at,
            'parking_lot_id': self.parking_lot_id,
        }
