"""Tests for the member CRUD, pagination and the loan-aware delete guard."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, Loan

MEMBER = {"name": "Ada Lovelace", "email": "ada@example.com"}


def _create(client: TestClient, auth_headers: dict[str, str], **overrides: str) -> dict:
    payload = {**MEMBER, **overrides}
    response = client.post("/members", json=payload, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


def test_member_crud_round_trip(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create(client, auth_headers)
    assert created["name"] == "Ada Lovelace"
    assert created["email"] == "ada@example.com"
    assert "id" in created
    assert created["member_since"] == date.today().isoformat()
    member_id = created["id"]

    fetched = client.get(f"/members/{member_id}")
    assert fetched.status_code == 200
    assert fetched.json() == created

    replaced = client.put(
        f"/members/{member_id}",
        json={"name": "Grace Hopper", "email": "grace@example.com"},
        headers=auth_headers,
    )
    assert replaced.status_code == 200
    assert replaced.json()["name"] == "Grace Hopper"
    assert replaced.json()["email"] == "grace@example.com"

    patched = client.patch(
        f"/members/{member_id}",
        json={"name": "Grace B. Hopper"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Grace B. Hopper"
    assert patched.json()["email"] == "grace@example.com"

    deleted = client.delete(f"/members/{member_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    assert client.get(f"/members/{member_id}").status_code == 404


def test_member_pagination_reports_total_limit_offset(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for index in range(3):
        _create(client, auth_headers, email=f"member{index}@example.com")

    page = client.get("/members").json()
    assert page["total"] == 3
    assert page["limit"] == 20
    assert page["offset"] == 0
    assert len(page["items"]) == 3

    second = client.get("/members", params={"limit": 2, "offset": 1}).json()
    assert second["total"] == 3
    assert second["limit"] == 2
    assert second["offset"] == 1
    assert len(second["items"]) == 2


def test_duplicate_email_returns_conflict(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create(client, auth_headers)
    response = client.post("/members", json=MEMBER, headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"

    assert client.get("/members").json()["total"] == 1


def test_duplicate_email_on_update_returns_conflict(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _create(client, auth_headers, email="first@example.com")
    second = _create(client, auth_headers, email="second@example.com")

    put = client.put(
        f"/members/{second['id']}",
        json={"name": "Second", "email": "first@example.com"},
        headers=auth_headers,
    )
    assert put.status_code == 409

    patch = client.patch(
        f"/members/{second['id']}",
        json={"email": "first@example.com"},
        headers=auth_headers,
    )
    assert patch.status_code == 409
    assert first["email"] == "first@example.com"


def test_invalid_email_returns_validation_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/members",
        json={"name": "Nope", "email": "not-an-email"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "email" in body["error"]["message"]


def test_unknown_member_returns_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/members/999").status_code == 404
    assert (
        client.put(
            "/members/999",
            json=MEMBER,
            headers=auth_headers,
        ).status_code
        == 404
    )
    assert client.patch("/members/999", json={"name": "X"}, headers=auth_headers).status_code == 404
    assert client.delete("/members/999", headers=auth_headers).status_code == 404


def test_delete_member_with_loans_is_refused_then_succeeds(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    member = _create(client, auth_headers)
    book = Book(
        title="Der Process",
        author="Franz Kafka",
        isbn="978-3-596-90034-5",
        published_year=1925,
        copies=1,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    loan = Loan(
        book_id=book.id,
        member_id=member["id"],
        loaned_at=date.today(),
        due_at=date.today(),
    )
    db_session.add(loan)
    db_session.commit()

    refused = client.delete(f"/members/{member['id']}", headers=auth_headers)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "conflict"
    assert "1" in refused.json()["error"]["message"]
    assert client.get(f"/members/{member['id']}").status_code == 200

    db_session.delete(loan)
    db_session.commit()

    deleted = client.delete(f"/members/{member['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/members/{member['id']}").status_code == 404
