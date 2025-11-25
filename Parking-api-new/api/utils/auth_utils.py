import hashlib
import bcrypt
from cryptography.fernet import Fernet
import constants

_fernet = Fernet(constants.FERNET_KEY)

def hash_password_bcrypt(password: str) -> tuple[str, str]:
    """
    Hash password met bcrypt, dan encrypt de hash voor opslag
    Geeft (encrypted_hash, salt) voor database
    """
    salt = bcrypt.gensalt()
    # Hash password met bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Encrypt hash met fernet
    encrypted_hash = _fernet.encrypt(hashed).decode('utf-8')
    return encrypted_hash, salt.decode('utf-8')


def verify_password(password: str, stored_encrypted_hash: str, hash_version: str) -> bool:
    """Verifieer wachtwoord op basis van hash versie (md5 of bcrypt)"""
    if hash_version == 'md5':
        # Oude accounts: MD5 hash was gehasht met bcrypt (geen encryptie laag)
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        return bcrypt.checkpw(md5_hash.encode('utf-8'), stored_encrypted_hash.encode('utf-8'))
    else:
        # Nieuwe accounts: decrypt de hash, dan verifieer met bcrypt
        # Decrypt de opgeslagen hash
        decrypted_hash = _fernet.decrypt(stored_encrypted_hash.encode('utf-8'))
        # Check wachtwoord met de bcrypt hash
        return bcrypt.checkpw(password.encode('utf-8'), decrypted_hash)


