def test_login_returns_token_and_profile(login):
    me = login("coffee").get("/me").json()
    assert me["role"] == "CLIENT"
    assert me["company"]["inn"] == "7701234567"


def test_wrong_password(api):
    response = api.post("/api/v1/auth/login", json={"login": "coffee", "password": "nope"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_requests_without_token_are_rejected(api):
    assert api.get("/api/v1/applications").status_code == 401
    assert api.get("/api/v1/me", headers={"Authorization": "Bearer broken"}).status_code == 401


def test_roles_are_separated(login):
    assert login("coffee").get("/bank/applications").status_code == 403
    assert login("manager").get("/applications").status_code == 403
