FRONTEND = "http://localhost:5173"


def test_preflight_from_frontend_is_allowed(client):
    response = client.options(
        "/api/links",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    allowed = response.headers["access-control-allow-methods"]
    for method in ("GET", "POST", "PUT", "DELETE"):
        assert method in allowed


def test_frontend_can_read_content_range(client, make_link):
    make_link()

    response = client.get(
        "/api/links", params={"range": "[0,9]"}, headers={"Origin": FRONTEND}
    )

    assert response.headers["access-control-allow-origin"] == FRONTEND
    exposed = response.headers["access-control-expose-headers"]
    assert "content-range" in exposed.lower()


def test_foreign_origin_is_not_allowed(client):
    response = client.get(
        "/api/links", headers={"Origin": "https://evil.example"}
    )

    assert "access-control-allow-origin" not in response.headers


def test_preflight_from_foreign_origin_is_rejected(client):
    response = client.options(
        "/api/links",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 400
