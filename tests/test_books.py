"""Tests for the books CRUD, search and pagination."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Loan, Member


def _book(**overrides: object) -> dict[str, object]:
    """A valid book payload, with fields overridable per test."""
    data: dict[str, object] = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0-261-10221-7",
        "published_year": 1937,
        "copies": 3,
    }
    data.update(overrides)
    return data


def _create_book(client: TestClient, auth_headers: dict[str, str], **overrides: object) -> dict:
    response = client.post("/books", json=_book(**overrides), headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_crud_round_trip(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _create_book(client, auth_headers)
    book_id = created["id"]
    assert created["title"] == "The Hobbit"

    fetched = client.get(f"/books/{book_id}")
    assert fetched.status_code == 200
    assert fetched.json() == created

    replaced = client.put(
        f"/books/{book_id}",
        json=_book(title="The Hobbit, revised", copies=5),
        headers=auth_headers,
    )
    assert replaced.status_code == 200
    assert replaced.json()["title"] == "The Hobbit, revised"
    assert replaced.json()["copies"] == 5

    patched = client.patch(f"/books/{book_id}", json={"author": "Tolkien"}, headers=auth_headers)
    assert patched.status_code == 200
    assert patched.json()["author"] == "Tolkien"
    assert patched.json()["title"] == "The Hobbit, revised"

    deleted = client.delete(f"/books/{book_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_unknown_book_returns_404(client: TestClient) -> None:
    response = client.get("/books/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_pagination_covers_every_book_exactly_once(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for index in range(25):
        _create_book(
            client,
            auth_headers,
            isbn=f"isbn-{index}",
            title=f"Book {index:02d}",
        )

    first = client.get("/books", params={"limit": 20, "offset": 0})
    assert first.status_code == 200
    body = first.json()
    assert body["total"] == 25
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 20

    seen = [item["id"] for item in body["items"]]
    second = client.get("/books", params={"limit": 20, "offset": 20})
    assert second.status_code == 200
    assert len(second.json()["items"]) == 5
    seen.extend(item["id"] for item in second.json()["items"])

    assert len(seen) == 25
    assert len(set(seen)) == 25


def test_search_matches_title_and_author_case_insensitively(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_book(
        client,
        auth_headers,
        isbn="isbn-dune",
        title="Dune",
        author="Frank Herbert",
    )
    _create_book(
        client,
        auth_headers,
        isbn="isbn-neuromancer",
        title="Neuromancer",
        author="William Gibson",
    )

    by_title = client.get("/books", params={"q": "dune"}).json()
    assert [item["title"] for item in by_title["items"]] == ["Dune"]

    by_author = client.get("/books", params={"q": "GIBSON"}).json()
    assert [item["title"] for item in by_author["items"]] == ["Neuromancer"]

    by_substring = client.get("/books", params={"q": "eur"}).json()
    assert [item["title"] for item in by_substring["items"]] == ["Neuromancer"]


def test_duplicate_isbn_returns_409_and_keeps_one_book(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_book(client, auth_headers)

    duplicate = client.post("/books", json=_book(title="Another title"), headers=auth_headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    listing = client.get("/books", params={"q": "Hobbit"}).json()
    assert listing["total"] == 1


def test_put_to_existing_isbn_returns_409(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create_book(client, auth_headers, isbn="isbn-a", title="Alpha")
    second = _create_book(client, auth_headers, isbn="isbn-b", title="Beta")

    conflict = client.put(
        f"/books/{second['id']}",
        json=_book(isbn="isbn-a", title="Beta"),
        headers=auth_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_reducing_copies_below_open_loans_returns_409(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _create_book(client, auth_headers, copies=2)

    member = Member(name="Ada", email="ada@example.com", member_since=date(2020, 1, 1))
    db_session.add(member)
    db_session.commit()

    db_session.add(
        Loan(
            book_id=book["id"],
            member_id=member.id,
            loaned_at=date(2024, 1, 1),
            due_at=date(2024, 1, 15),
        )
    )
    db_session.commit()

    conflict = client.patch(f"/books/{book['id']}", json={"copies": 0}, headers=auth_headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_validation_errors_return_422_envelope(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    empty_title = client.post("/books", json=_book(title=""), headers=auth_headers)
    assert empty_title.status_code == 422
    body = empty_title.json()
    assert body["error"]["code"] == "validation_error"
    assert "title" in body["error"]["message"]

    bad_year = client.post(
        "/books", json=_book(isbn="isbn-year", published_year=500), headers=auth_headers
    )
    assert bad_year.status_code == 422

    negative_copies = client.post(
        "/books", json=_book(isbn="isbn-copies", copies=-1), headers=auth_headers
    )
    assert negative_copies.status_code == 422

    bad_limit = client.get("/books", params={"limit": 101})
    assert bad_limit.status_code == 422

    negative_offset = client.get("/books", params={"offset": -1})
    assert negative_offset.status_code == 422


def test_delete_is_refused_while_loans_exist_then_succeeds(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _create_book(client, auth_headers)

    member = Member(name="Grace", email="grace@example.com", member_since=date(2020, 1, 1))
    db_session.add(member)
    db_session.commit()

    loan = Loan(
        book_id=book["id"],
        member_id=member.id,
        loaned_at=date(2024, 1, 1),
        due_at=date(2024, 1, 15),
    )
    db_session.add(loan)
    db_session.commit()

    refused = client.delete(f"/books/{book['id']}", headers=auth_headers)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "conflict"
    assert "1" in refused.json()["error"]["message"]
    assert client.get(f"/books/{book['id']}").status_code == 200

    db_session.delete(loan)
    db_session.commit()

    deleted = client.delete(f"/books/{book['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404
