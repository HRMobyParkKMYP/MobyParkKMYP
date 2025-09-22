# tests/test_auth.py
import requests


def test_register_and_login(api_server):
    # Register user
    res = requests.post(
        f"{api_server}/register",
        json={"username": "testuser", "password": "secret", "name": "Gloobert"},
    )
    assert res.status_code == 201

    # Duplicate register should fail
    res2 = requests.post(
        f"{api_server}/register",
        json={"username": "testuser", "password": "another", "name": "Dup"},
    )
    assert res2.status_code == 400

    # Wrong password
    bad_login = requests.post(
        f"{api_server}/login", json={"username": "testuser", "password": "wrong"}
    )
    assert bad_login.status_code == 401

    # Correct login
    good_login = requests.post(
        f"{api_server}/login", json={"username": "testuser", "password": "secret"}
    )
    assert good_login.status_code == 200
    token = good_login.json()["session_token"]

    # Profile requires token
    no_auth = requests.get(f"{api_server}/profile")
    assert no_auth.status_code == 401

    with_auth = requests.get(f"{api_server}/profile", headers={"Authorization": token})
    assert with_auth.status_code == 200
    assert with_auth.json()["username"] == "testuser"