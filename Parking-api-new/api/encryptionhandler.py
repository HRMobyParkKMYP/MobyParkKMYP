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
        Docstring for encryptAndHashPassword

        :param data: password string to encrypt
        :type data: str
        :param salt: salt string to encrypt
        :type salt: str
        :return: encrypted and hashed password
        :rtype: str
        """
        try:
            enc_data = self.fn.encrypt(data)
            return str(bcrypt.hashpw(enc_data, bytes(salt)))

        except Exception as e:
            self.logger.info(e)


    def encrypt(self, data: str) -> str:
        """
        encrypts data
        
        :param data: any data you want encrypted
        :type data: str
        :return: encrypted data
        :rtype: str
        """
        try:
            enc_data = self.fn.encrypt(data)
            return str(enc_data)

        except Exception as e:
            self.logger.info(e)
    

    def decrypt(self, data: str) -> str:
        """
        decrypts data
        
        :param data: Any data encrypted with the encrypt or encryptAndHashPassword function
        :type data: str
        :return: decrypted data
        :rtype: str
        """
        try:
            return str(self.fn.decrypt(data))
        
        except Exception as e:
            self.logger.info(e) 