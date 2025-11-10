import bcrypt

class EncryptionHandler:

    def __init__(self, key: str):
        self.key = key

    def encrypt(self, data: str, salt: str) -> str:
        pass
    
    def decrypt(self, data: str, salt: str) -> str:
        pass
    