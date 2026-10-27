import pytest

TOTAL = 12


@pytest.fixture
def links(make_link):
    return [make_link() for _ in range(TOTAL)]


def ids(response):
    return [link["id"] for link in response.json()]


def test_list_without_range_returns_everything(client, links):
    response = client.get("/api/links")

    assert response.status_code == 200
    assert ids(response) == [link["id"] for link in links]
    assert response.headers["content-range"] == f"links 0-11/{TOTAL}"


def test_list_empty(client):
    response = client.get("/api/links", params={"range": "[0,9]"})

    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["content-range"] == "links */0"


@pytest.mark.parametrize(
    ("range_param", "expected_slice", "expected_header"),
    [
        ("[0,9]", slice(0, 10), "links 0-9/12"),
        ("[10,19]", slice(10, 12), "links 10-11/12"),
        ("[5, 9]", slice(5, 10), "links 5-9/12"),
        ("[3,3]", slice(3, 4), "links 3-3/12"),
        ("[0, 1000]", slice(0, 12), "links 0-11/12"),
    ],
)
def test_list_with_range(
    client, links, range_param, expected_slice, expected_header
):
    response = client.get("/api/links", params={"range": range_param})

    assert response.status_code == 200
    assert ids(response) == [link["id"] for link in links[expected_slice]]
    assert response.headers["content-range"] == expected_header


def test_range_beyond_total(client, links):
    response = client.get("/api/links", params={"range": "[20,29]"})

    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["content-range"] == f"links */{TOTAL}"


@pytest.mark.parametrize(
    "range_param", ["abc", "[5,1]", "[-1,3]", "[1]", "[1,2,3]", '["a",2]']
)
def test_invalid_range(client, range_param):
    response = client.get("/api/links", params={"range": range_param})

    assert response.status_code == 422
    assert response.json()["detail"]


def test_sort_and_range_together(client, make_link):
    for name in ("bravo", "alpha", "charlie"):
        make_link(short_name=name)

    response = client.get(
        "/api/links",
        params={"sort": '["short_name","DESC"]', "range": "[0,1]"},
    )

    assert response.status_code == 200
    names = [link["short_name"] for link in response.json()]
    assert names == ["charlie", "bravo"]
    assert response.headers["content-range"] == "links 0-1/3"


@pytest.mark.parametrize(
    "sort_param", ['["created_at","ASC"]', '["id","UP"]', "id"]
)
def test_invalid_sort(client, sort_param):
    response = client.get("/api/links", params={"sort": sort_param})

    assert response.status_code == 422
    assert response.json()["detail"]
