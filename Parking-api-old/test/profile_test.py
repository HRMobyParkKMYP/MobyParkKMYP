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

#GET /profile tests
def test_get_profile_unauthorized():
    res = requests.get(f"{BASE_URL}/profile")
    assert res.status_code == 401
    assert b"Unauthorized" in res.content

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

# PUT /profile tests
def test_update_profile_success(register_and_login):
    token = register_and_login(
        "updateuser",
        "secretpass",
        "Old Name",
        "old@example.com",
        "0611111111",
        1988
    )

    update_payload = {
        "password": "newpass123",
        "name": "Updated User",
        "email": "new@example.com",
        "phone": "0699999999",
        "birth_year": 1995
    }

    res = requests.put(
        f"{BASE_URL}/profile",
        headers={"Authorization": token},
        json=update_payload
    )
    assert res.status_code == 200
    assert "User updated succesfully" in res.text
    res_get = requests.get(f"{BASE_URL}/profile", headers={"Authorization": token})
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["name"] == "Updated User"
    assert data["email"] == "new@example.com"
    assert data["phone"] == "0699999999"
    assert data["birth_year"] == 1995

def test_update_profile_missing_token():
    res = requests.put(
        f"{BASE_URL}/profile",
        json={
            "password": "whatever",
            "name": "No Token User",
            "email": "nope@example.com",
            "phone": "0600000000",
            "birth_year": 1999
        }
    )
    assert res.status_code == 401
    assert "Unauthorized" in res.text


def test_update_profile_invalid_token():
    res = requests.put(
        f"{BASE_URL}/profile",
        headers={"Authorization": "invalidtoken123"},
        json={
            "password": "1234",
            "name": "Invalid Token",
            "email": "fail@example.com",
            "phone": "0600000000",
            "birth_year": 2000
        }
    )
    assert res.status_code == 401
    assert "Unauthorized" in res.text


def test_update_profile_without_password(register_and_login):
    token = register_and_login(
        "nopassupdate",
        "abc123",
        "No Pass",
        "nopass@example.com",
        "0612121212",
        1992
    )

    update_payload = {
        "password": "",
        "name": "Still No Pass",
        "email": "still@example.com",
        "phone": "0613131313",
        "birth_year": 1992
    }

    res = requests.put(
        f"{BASE_URL}/profile",
        headers={"Authorization": token},
        json=update_payload
    )
    assert res.status_code == 400
    assert "Bad Request" in res.text