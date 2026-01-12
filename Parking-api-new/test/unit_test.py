"""
Unit tests voor core utility functies
Test coverage voor: calculate_price, generate_payment_hash, hash_password_bcrypt, verify_password
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
import bcrypt
import hashlib

# Voeg parent directory aan path toe voor imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.utils import session_calculator
from api.utils import auth_utils
from api.utils import database_utils

@pytest.fixture
def sample_parkinglot():
    """Standard parking lot configuratie voor tests"""
    return {
        "id": 1,
        "name": "Test Parking",
        "location": "Amsterdam Centrum",
        "address": "Teststraat 123, 1012 AB Amsterdam",
        "capacity": 100,
        "reserved": 25,
        "tariff": "2.50",  # €2.50 per uur
        "day_tariff": "15.00",  # €15.00 per dag
        "created_at": "2025-01-01",
        "lat": "52.3676",
        "lng": "4.9041"
    }


# TESTS: calculate_price() session calculator

class TestCalculatePrice:
    """Test suite voor prijsberekening van parking sessies"""
    
    def test_calculate_price_correct(self, sample_parkinglot):
        """Test normale prijsberekening - 3 uur parkeren = €7.50"""
        now = datetime.now()
        session_data = {
            "started": now.strftime("%d-%m-%Y %H:%M:%S"),
            "stopped": (now + timedelta(hours=3)).strftime("%d-%m-%Y %H:%M:%S"),
            "licenseplate": "AB-123-CD"
        }
        
        price, hours, days = session_calculator.calculate_price(
            sample_parkinglot, 1, session_data
        )
        
        assert price == 7.50  # 3 uur * €2.50
        assert hours == 3
        assert days == 0
    
    def test_calculate_price_short_session_free(self, sample_parkinglot):
        """Test dat sessies < 3 minuten gratis zijn"""
        now = datetime.now()
        session_data = {
            "started": now.strftime("%d-%m-%Y %H:%M:%S"),
            "stopped": (now + timedelta(minutes=2)).strftime("%d-%m-%Y %H:%M:%S"),
            "licenseplate": "AB-123-CD"
        }
        
        price, hours, days = session_calculator.calculate_price(
            sample_parkinglot, 1, session_data
        )
        
        assert price == 0
        assert hours == 1


# TESTS: generate_payment_hash() session calculator

class TestGeneratePaymentHash:
    """Test suite voor payment hash generatie"""
    
    def test_generate_payment_hash_correct(self):
        """Test dat hash consistent gegenereerd wordt voor zelfde input"""
        session_data = {"licenseplate": "AB-123-CD"}
        
        hash1 = session_calculator.generate_payment_hash(123, session_data)
        hash2 = session_calculator.generate_payment_hash(123, session_data)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 formaat
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_generate_payment_hash_different_input(self):
        """Test dat verschillende input verschillende hash genereert"""
        session_data1 = {"licenseplate": "AB-123-CD"}
        session_data2 = {"licenseplate": "XY-789-ZZ"}
        
        hash1 = session_calculator.generate_payment_hash(123, session_data1)
        hash2 = session_calculator.generate_payment_hash(123, session_data2)
        
        assert hash1 != hash2


# TESTS: hash_password_bcrypt() auth utils

class TestHashPasswordBcrypt:
    """Test suite voor password hashing met bcrypt + encryption"""
    
    def test_hash_password_correct(self):
        """Test dat password correct gehasht wordt met bcrypt + encryption"""
        password = "MySecurePassword123!"
        
        encrypted_hash, salt = auth_utils.hash_password_bcrypt(password)
        
        assert encrypted_hash is not None
        assert salt is not None
        assert isinstance(encrypted_hash, str)
        assert isinstance(salt, str)
        assert salt.startswith('$2b$')  # Geldige bcrypt salt
        
        # Verify dat hash gedecrypt kan worden en wachtwoord klopt
        decrypted = auth_utils._fernet.decrypt(encrypted_hash.encode('utf-8'))
        assert bcrypt.checkpw(password.encode('utf-8'), decrypted)
    
    def test_hash_password_different_salts(self):
        """Test dat zelfde password verschillende hashes krijgt door random salt"""
        password = "SamePassword123"
        
        hash1, salt1 = auth_utils.hash_password_bcrypt(password)
        hash2, salt2 = auth_utils.hash_password_bcrypt(password)
        
        assert hash1 != hash2
        assert salt1 != salt2


# TESTS: verify_password() auth utils

class TestVerifyPassword:
    """Test suite voor password verificatie (MD5 en bcrypt versies)"""
    
    def test_verify_password_correct_bcrypt(self):
        """Test correcte password verificatie met bcrypt versie"""
        password = "MySecurePassword123"
        
        encrypted_hash, salt = auth_utils.hash_password_bcrypt(password)
        result = auth_utils.verify_password(password, encrypted_hash, 'bcrypt')
        
        assert result is True
    
    def test_verify_password_incorrect_bcrypt(self):
        """Test dat incorrecte password wordt afgewezen"""
        password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        
        encrypted_hash, salt = auth_utils.hash_password_bcrypt(password)
        result = auth_utils.verify_password(wrong_password, encrypted_hash, 'bcrypt')
        
        assert result is False