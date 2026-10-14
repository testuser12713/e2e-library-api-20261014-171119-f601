"""Skeleton tests: the app boots, documents its contract and answers the envelope."""

from fastapi.testclient import TestClient

from app.main import app

EXPECTED_PATHS: dict[str, set[str]] = {
    "/health": {"get"},
    "/books": {"get", "post"},
    "/books/{book_id}": {"get", "put", "patch", "delete"},
    "/members": {"get", "post"},
    "/members/{member_id}": {"get", "put", "patch", "delete"},
    "/loans": {"post"},
    "/loans/{loan_id}/return": {"post"},
    "/loans/overdue": {"get"},
}

EXPECTED_SCHEMAS = {
    "BookWrite",
    "BookPatch",
    "BookRead",
    "BookPage",
    "MemberWrite",
    "MemberPatch",
    "MemberRead",
    "MemberPage",
    "LoanCreate",
    "LoanRead",
    "OverdueLoanRead",
    "OverduePage",
    "ErrorResponse",
}


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_boots_through_lifespan_startup() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_every_endpoint_with_models_and_error_statuses(
    client: TestClient,
) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]

    for path, methods in EXPECTED_PATHS.items():
        assert path in paths, f"missing declared path {path}"
        for method in methods:
            assert method in paths[path], f"missing {method.upper()} {path}"

    schemas = spec["components"]["schemas"]
    for name in EXPECTED_SCHEMAS:
        assert name in schemas, f"missing schema {name}"

    assert "requestBody" in paths["/books"]["post"]
    assert {"201", "401", "409", "422"} <= set(paths["/books"]["post"]["responses"])
    assert {"200", "422"} <= set(paths["/books"]["get"]["responses"])
    assert {"200", "401", "404", "409", "422"} <= set(paths["/books/{book_id}"]["put"]["responses"])
    assert {"201", "401", "409", "422"} <= set(paths["/members"]["post"]["responses"])
    assert {"204", "401", "404", "409"} <= set(paths["/members/{member_id}"]["delete"]["responses"])
    assert {"201", "401", "404", "409", "422"} <= set(paths["/loans"]["post"]["responses"])
    assert {"200", "401", "404", "409"} <= set(
        paths["/loans/{loan_id}/return"]["post"]["responses"]
    )
    assert {"200", "422"} <= set(paths["/loans/overdue"]["get"]["responses"])


def test_docs_page_is_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200


def test_declared_read_routes_are_wired(client: TestClient) -> None:
    assert client.get("/books").status_code != 404
    assert client.get("/members").status_code != 404
    assert client.get("/loans/overdue").status_code != 404


def test_unknown_path_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "not_found"
    assert isinstance(body["error"]["message"], str)


def test_invalid_body_returns_validation_envelope_naming_the_field(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/books",
        json={
            "title": "",
            "author": "Ada Lovelace",
            "isbn": "978-3-16-148410-0",
            "published_year": 2020,
            "copies": 1,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert "title" in body["error"]["message"]
