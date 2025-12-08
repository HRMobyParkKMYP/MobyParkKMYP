from typing import Dict, Any, Type, TypeVar
from models.ModelInterface import ModelInterface

T = TypeVar('T', bound='Payment')


class Payment(ModelInterface):

    def __init__(self, pid: int = None, user_id: int = None, reservation_id: int = None,
                 p_session_id: int = None, amount: float = 0.0, currency: str = 'EUR',
                 method: str = None, status: str = 'initiated', created_at: str = None,
                 paid_at: str = None, external_ref: str = None):
        self.id = int(pid) if pid is not None and pid != '' else None
        self.user_id = int(user_id) if user_id is not None else None
        self.reservation_id = int(reservation_id) if reservation_id is not None else None
        self.p_session_id = int(p_session_id) if p_session_id is not None else None
        self.amount = float(amount)
        self.currency = currency
        self.method = method
        self.status = status
        self.created_at = created_at
        self.paid_at = paid_at
        self.external_ref = external_ref

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(
            pid=data.get('id'),
            user_id=data.get('user_id'),
            reservation_id=data.get('reservation_id'),
            p_session_id=data.get('p_session_id'),
            amount=data.get('amount', 0.0),
            currency=data.get('currency', 'EUR'),
            method=data.get('method'),
            status=data.get('status', 'initiated'),
            created_at=data.get('created_at'),
            paid_at=data.get('paid_at'),
            external_ref=data.get('external_ref'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reservation_id': self.reservation_id,
            'p_session_id': self.p_session_id,
            'amount': self.amount,
            'currency': self.currency,
            'method': self.method,
            'status': self.status,
            'created_at': self.created_at,
            'paid_at': self.paid_at,
            'external_ref': self.external_ref,
        }
