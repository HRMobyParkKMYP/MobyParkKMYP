import bcrypt
from customlogger import Logger
from cryptography.fernet import Fernet
import constants

class EncryptionHandler:

    def __init__(self, key: str):
        self.key = key
        self.logger = Logger.getLogger("EncryptionHandler")
        self.logger.info("Initialised encryption handler")
        self.fn = Fernet(constants.FERNET_KEY)

    def encryptAndHashPassword(self, data: str, salt: str) -> str:
        """
        Encrypts and hashes data with a given salt
        """
        try:
            enc_data = self.fn.encrypt(data)
            return str(bcrypt.hashpw(enc_data, bytes(salt)))

        except Exception as e:
            self.logger.info(e)


    def encrypt(self, data: str) -> str:
        try:
            enc_data = self.fn.encrypt(data)
            return str(enc_data)

        except Exception as e:
            self.logger.info(e)
    

    def decrypt(self, data: str) -> str:
        try:
            return str(self.fn.decrypt(data))
        
        except Exception as e:
            self.logger.info(e) 