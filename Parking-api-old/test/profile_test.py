import pytest
import requests
import json

BASE_URL = "http://localhost:8000"

@pytest.fixture
def register_and_login():
    def _register_and_login(username, password, name, email, phone, birth_year):
        # Register user (ignore if already exists)
        requests.post(f"{BASE_URL}/register", json={
            "username": username,
            "password": password,
            "name": name,
            "email": email,
            "phone": phone,
            "birth_year": birth_year
        })

        # Login to get session token
        res = requests.post(f"{BASE_URL}/login", json={
            "username": username,
            "password": password
        })
        assert res.status_code == 200, f"Login failed for {username}: {res.text}"
        return res.json().get("session_token")
    return _register_and_login

def test_get_profile_authorized(register_and_login):
    token = register_and_login(
        "hbn",
        "testpass",
        "Test User",
        "test@example.com",
        "0612345678",
        1990
    )

    res = requests.get(f"{BASE_URL}/profile",
                       headers={"Authorization": token})

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    profile = res.json()
    assert profile["username"] == "hbn"
    assert profile["name"] == "Test User"
    assert "email" in profile
    assert "birth_year" in profile