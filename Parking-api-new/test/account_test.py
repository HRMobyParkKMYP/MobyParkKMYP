import os
import pytest
import requests
import uuid
from datetime import datetime

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# POST register tests
def test_register_success():
    # 1. Succesvolle registratie
    unique_id = uuid.uuid4().hex[:6]
    data = {
        "username": f"emma_{unique_id}",
        "password": "geheim",
        "name": "Emma de Vries",
        "email": f"emma_{unique_id}@example.com",
        "phone": f"+31{hash(unique_id) % 900000000 + 100000000}",
        "birth_year": 1995
    }

    res = requests.post(f"{BASE_URL}/register", json=data)
    assert res.status_code == 200
    assert "User created" in res.text

    res2 = requests.post(f"{BASE_URL}/login", json={
            "username": data["username"],
            "password": "geheim"
        })
    assert res2.status_code == 200


def test_register_missing_fields():
    # 2. Registreren, mist verplichte velden
    res = requests.post(f"{BASE_URL}/register", json={"username": "jan"})
    assert res.status_code == 422
    # FastAPI returnt automatisch validatiefouten voor missende velden


def test_register_duplicate_username():
    # 3. Registreren, duplicate username geeft 409
    base_user = {
        "username": "jan",
        "password": "pw",
        "name": "Jan Gebruiker",
        "email": "jan@example.com",
        "phone": "+31699999999",
        "birth_year": 1980
    }
    requests.post(f"{BASE_URL}/register", json=base_user)

    res = requests.post(f"{BASE_URL}/register", json={
        **base_user,
        "email": "andere@example.com",  # andere email
        "phone": "+31688888888"        # andere phone
    })
    assert res.status_code == 409
    assert b"Username already taken" in res.content


def test_register_duplicate_email():
    # 4. Registreren, duplicate email geeft 409
    u1 = {
        "username": "user1",
        "password": "pw",
        "name": "User One",
        "email": "same@example.com",
        "phone": "+31000000000",
        "birth_year": 1980
    }
    u2 = {
        "username": "user2",
        "password": "pw",
        "name": "User Two",
        "email": "same@example.com",
        "phone": "+31000000001",
        "birth_year": 1990
    }
    requests.post(f"{BASE_URL}/register", json=u1)
    res = requests.post(f"{BASE_URL}/register", json=u2)
    assert res.status_code == 409
    assert b"Email already registered" in res.content


# POST login tests
def test_login_success():
    # 1. Succesvolle login
    reg_data = {
        "username": "klaas",
        "password": "secret",
        "name": "Klaas Klinkhamer",
        "email": "klaas@example.com",
        "phone": "+31677777777",
        "birth_year": 1991
    }
    requests.post(f"{BASE_URL}/register", json=reg_data)

    res = requests.post(f"{BASE_URL}/login", json={"username": "klaas", "password": "secret"})
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    assert data["message"] == "User logged in"


def test_login_invalid_credentials():
    # 2. Login, onjuiste login geeft 401
    res = requests.post(f"{BASE_URL}/login", json={"username": "nietbestaat", "password": "fout"})
    assert res.status_code == 401
    assert b"Invalid credentials" in res.content


def test_login_missing_fields():
    # 3. Login, ontbrekende login velden
    res = requests.post(f"{BASE_URL}/login", json={"username": "jan"})
    assert res.status_code == 422
    # FastAPI returns validation errors automatically for missing fields


# GET logout tests
def test_logout_success():
    # 1. Uitloggen met geldige token
    # registreer en log in
    reg_data = {
        "username": "lotte",
        "password": "pw",
        "name": "Lotte User",
        "email": "lotte@example.com",
        "phone": "+31611111111",
        "birth_year": 1992
    }
    requests.post(f"{BASE_URL}/register", json=reg_data)
    login = requests.post(f"{BASE_URL}/login", json={"username": "lotte", "password": "pw"}).json()
    token = login["session_token"]

    res = requests.get(f"{BASE_URL}/logout", headers={"Authorization": token})
    assert res.status_code == 200
    assert b"User logged out" in res.content


def test_logout_invalid_token():
    # 2. Uitloggen zonder of met fout token
    res = requests.get(f"{BASE_URL}/logout")
    assert res.status_code == 400
    assert b"Invalid session token" in res.content

    res2 = requests.get(f"{BASE_URL}/logout", headers={"Authorization": "fake-token"})
    assert res2.status_code == 400
    assert b"Invalid session token" in res2.content
