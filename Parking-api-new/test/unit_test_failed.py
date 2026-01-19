
import pytest
from datetime import datetime, timedelta
import bcrypt
from cryptography.fernet import InvalidToken

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.utils import session_calculator
from api.utils import auth_utils


# ---------------------------
# Fixtures
# ---------------------------

@pytest.fixture
def sample_parkinglot():
    return {
        "id": 1,
        "name": "Test Parking",
        "tariff": "2.50",
        "day_tariff": "15.00"
    }


# ===========================
# calculate_price() – INVALID INPUT
# ===========================

class TestCalculatePriceInvalid:

    def test_negative_duration(self, sample_parkinglot):
        """Stop tijd ligt vóór start tijd"""
        session_data = {
            "started": "2025-01-15 15:00:00",
            "stopped": "2025-01-15 14:00:00",
            "licenseplate": "AB-123-CD"
        }
        # Berekening lukt maar geeft negatieve hours → we controleren dat hours < 0
        price, hours, days = session_calculator.calculate_price(sample_parkinglot, 1, session_data)
        assert hours <= 0

    def test_missing_started_time(self, sample_parkinglot):
        """Started tijd ontbreekt → KeyError"""
        session_data = {
            "stopped": "2025-01-15 16:00:00",
            "licenseplate": "AB-123-CD"
        }
        with pytest.raises(KeyError):
            session_calculator.calculate_price(sample_parkinglot, 1, session_data)

    def test_invalid_datetime_format(self, sample_parkinglot):
        """Ongeldig datetime formaat → ValueError"""
        session_data = {
            "started": "15-01-2025 14:00",
            "stopped": "15-01-2025 16:00",
            "licenseplate": "AB-123-CD"
        }
        with pytest.raises(ValueError):
            session_calculator.calculate_price(sample_parkinglot, 1, session_data)

    def test_negative_tariff(self, sample_parkinglot):
        """Negatief tarief → prijs negatief"""
        sample_parkinglot["tariff"] = "-5.00"
        session_data = {
            "started": "2025-01-15 14:00:00",
            "stopped": "2025-01-15 16:00:00",
            "licenseplate": "AB-123-CD"
        }
        price, hours, days = session_calculator.calculate_price(sample_parkinglot, 1, session_data)
        assert price < 0


# ===========================
# generate_payment_hash() – INVALID INPUT
# ===========================

class TestGeneratePaymentHashInvalid:

    def test_missing_licenseplate(self):
        """Licenseplate ontbreekt → KeyError"""
        session_data = {}
        with pytest.raises(KeyError):
            session_calculator.generate_payment_hash(123, session_data)

    def test_none_session_data(self):
        """Session data is None → TypeError"""
        with pytest.raises(TypeError):
            session_calculator.generate_payment_hash(123, None)


# ===========================
# hash_password_bcrypt() – INVALID INPUT
# ===========================

class TestHashPasswordInvalid:

    def test_none_password(self):
        """Password is None → AttributeError"""
        with pytest.raises(AttributeError):
            auth_utils.hash_password_bcrypt(None)

    def test_non_string_password(self):
        """Password is int → AttributeError"""
        with pytest.raises(AttributeError):
            auth_utils.hash_password_bcrypt(12345)


# ===========================
# verify_password() – INVALID INPUT
# ===========================

class TestVerifyPasswordInvalid:

    def test_none_hash(self):
        """Hash is None → AttributeError"""
        with pytest.raises(AttributeError):
            auth_utils.verify_password("password", None, "bcrypt")

    def test_none_password(self):
        """Password is None → InvalidToken bij decryptie"""
        import cryptography
        with pytest.raises(cryptography.fernet.InvalidToken):
            auth_utils.verify_password(None, "somehash", "bcrypt")


    def test_invalid_fernet_hash(self):
        """Ongeldige Fernet hash → InvalidToken"""
        invalid_hash = "not_a_valid_hash"
        with pytest.raises(InvalidToken):
            auth_utils.verify_password("password", invalid_hash, "bcrypt")

    def test_unknown_hash_version(self):
        """Onbekende hash version → default bcrypt gebruikt, AttributeError mogelijk"""
        # Als hash ongeldig is → AttributeError
        with pytest.raises(AttributeError):
            auth_utils.verify_password("password", None, "unknown")
