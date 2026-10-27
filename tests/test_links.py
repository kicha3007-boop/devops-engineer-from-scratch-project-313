from tests.conftest import BASE_URL

MISSING_ID = 999_999


def test_create_link(client):
    payload = {
        "original_url": "https://example.com/long-url",
        "short_name": "exmpl",
    }

    response = client.post("/api/links", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["original_url"] == payload["original_url"]
    assert body["short_name"] == "exmpl"
    assert body["short_url"] == f"{BASE_URL}/r/exmpl"
    assert body["created_at"]


def test_create_link_generates_short_name(client):
    for payload in (
        {"original_url": "https://example.com/a"},
        {"original_url": "https://example.com/b", "short_name": ""},
        {"original_url": "https://example.com/c", "short_name": None},
    ):
        response = client.post("/api/links", json=payload)

        assert response.status_code == 201
        short_name = response.json()["short_name"]
        assert len(short_name) == 12
        assert short_name.isalnum()


def test_create_link_requires_body_fields(client):
    response = client.post("/api/links", json={})

    assert response.status_code == 422
    fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert "original_url" in fields


def test_create_link_rejects_invalid_values(client):
    bad_payloads = [
        {"original_url": "not-a-url", "short_name": "ok"},
        {"original_url": "ftp://example.com/file", "short_name": "ok"},
        {"original_url": "https://example.com", "short_name": "with space"},
        {"original_url": "https://example.com", "short_name": "x" * 65},
    ]
    for payload in bad_payloads:
        response = client.post("/api/links", json=payload)

        assert response.status_code == 422, payload
        assert isinstance(response.json()["detail"], list)


def test_create_link_with_taken_short_name(client, make_link):
    make_link(short_name="taken")

    response = client.post(
        "/api/links",
        json={"original_url": "https://example.org", "short_name": "taken"},
    )

    assert response.status_code == 409
    assert "taken" in response.json()["detail"]


def test_get_link(client, make_link):
    link = make_link()

    response = client.get(f"/api/links/{link['id']}")

    assert response.status_code == 200
    assert response.json() == link


def test_get_unknown_link(client):
    response = client.get(f"/api/links/{MISSING_ID}")

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_update_link(client, make_link):
    link = make_link()
    payload = {"original_url": "https://example.org/new", "short_name": "new"}

    response = client.put(f"/api/links/{link['id']}", json=payload)

    assert response.status_code == 200
    assert response.json()["short_url"] == f"{BASE_URL}/r/new"
    stored = client.get(f"/api/links/{link['id']}").json()
    assert stored["original_url"] == payload["original_url"]
    assert stored["short_name"] == "new"


def test_update_unknown_link(client):
    response = client.put(
        f"/api/links/{MISSING_ID}",
        json={"original_url": "https://example.org", "short_name": "any"},
    )

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_update_link_rejects_malformed_body(client, make_link):
    link = make_link()

    response = client.put(
        f"/api/links/{link['id']}",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_update_link_requires_short_name(client, make_link):
    link = make_link()

    response = client.put(
        f"/api/links/{link['id']}",
        json={"original_url": "https://example.org"},
    )

    assert response.status_code == 422


def test_update_link_to_taken_short_name(client, make_link):
    make_link(short_name="first")
    second = make_link(short_name="second")

    response = client.put(
        f"/api/links/{second['id']}",
        json={"original_url": "https://example.org", "short_name": "first"},
    )

    assert response.status_code == 409
    assert "first" in response.json()["detail"]
    stored = client.get(f"/api/links/{second['id']}").json()
    assert stored["short_name"] == "second"


def test_delete_link(client, make_link):
    link = make_link()

    response = client.delete(f"/api/links/{link['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/links/{link['id']}").status_code == 404


def test_delete_unknown_link(client):
    response = client.delete(f"/api/links/{MISSING_ID}")

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_redirect_by_short_name(client, make_link):
    link = make_link(original_url="https://example.com/target?q=1")

    response = client.get(f"/r/{link['short_name']}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target?q=1"


def test_redirect_unknown_short_name(client):
    response = client.get("/r/unknown", follow_redirects=False)

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_redirect_follows_renamed_link(client, make_link):
    link = make_link(short_name="old")
    client.put(
        f"/api/links/{link['id']}",
        json={"original_url": link["original_url"], "short_name": "renamed"},
    )

    assert client.get("/r/old", follow_redirects=False).status_code == 404
    renamed = client.get("/r/renamed", follow_redirects=False)
    assert renamed.status_code == 302
