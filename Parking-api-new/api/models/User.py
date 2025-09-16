from models.ModelInterface import ModelInterface

class User(ModelInterface): 

    def __init__(self, uID : int): 
        self.uID = uID


    @classmethod
    def from_dict(cls, data):
        return cls(
            uID=data["uID"]
        )

    def to_dict(self):
        return {
            "uID": self.uID,
        }