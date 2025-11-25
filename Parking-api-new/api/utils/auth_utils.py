import hashlib
import bcrypt
from cryptography.fernet import Fernet
import constants

# Initialize Fernet for password hash encryption
_fernet = Fernet(constants.FERNET_KEY)


def hash_password_bcrypt(password: str) -> tuple[str, str]:
    """
    Hash password with bcrypt, then encrypt the hash for storage
    Returns (encrypted_hash, salt) for database storage
    """
    salt = bcrypt.gensalt()
    # 1. Hash password with bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # 2. Encrypt the hash for additional security
    encrypted_hash = _fernet.encrypt(hashed).decode('utf-8')
    return encrypted_hash, salt.decode('utf-8')


def verify_password(password: str, stored_encrypted_hash: str, hash_version: str) -> bool:
    """
    Verify password based on hash version
    
    Args:
        password: Plain text password to verify
        stored_encrypted_hash: Encrypted hash from database
        hash_version: 'md5' for old accounts, 'bcrypt' for new accounts
    
    Returns:
        True if password matches, False otherwise
    """
    if hash_version == 'md5':
        # Old accounts: MD5 hash was hashed with bcrypt (no encryption layer)
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        return bcrypt.checkpw(md5_hash.encode('utf-8'), stored_encrypted_hash.encode('utf-8'))
    else:
        # New accounts: decrypt the hash, then verify with bcrypt
        # 1. Decrypt the stored hash
        decrypted_hash = _fernet.decrypt(stored_encrypted_hash.encode('utf-8'))
        # 2. Verify password against the bcrypt hash
        return bcrypt.checkpw(password.encode('utf-8'), decrypted_hash)


