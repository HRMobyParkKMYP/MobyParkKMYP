from abc import ABC, abstractmethod
from typing import TypeVar, Type, Dict, Any

T = TypeVar('T', bound='ModelInterface')

class ModelInterface(ABC):
    @classmethod
    @abstractmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create an instance of the model from a dictionary.
        
        Params:
            data (Dict[str, Any]): The dictionary containing the model's data.
        
        Returns:
            An instance of the model.
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model instance to a dictionary.
        
        Returns:
            A dictionary representation of the model.
        """
        pass