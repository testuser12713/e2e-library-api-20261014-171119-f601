# Stadtbibliothek Ausleih-API

Eine REST-API in Python für die Ausleihe einer kleinen Stadtbibliothek: Bücher,
Mitglieder und Ausleihen als Ressourcen, CRUD für Bücher und Mitglieder,
Buchsuche mit Paginierung, Ausleihen und Rückgabe über eigene Endpunkte, eine
Overdue-Liste, API-Key-geschützte Schreibzugriffe und einheitliche
Fehlerantworten. Es gibt kein Frontend — die Schnittstelle selbst ist das Produkt
und wird über OpenAPI dokumentiert. Getestet wird mit pytest und dem
FastAPI-TestClient gegen eine eigene Test-Datenbank.

> Hinweis: Dies ist das laufende Grundgerüst (Skeleton) des Sprints. Alle
> Endpunkte sind bereits mit Pfad, Modellen, Fehler-Statuscodes und
> API-Key-Abhängigkeit deklariert, aber noch nicht implementiert; ihre Handler
> antworten derzeit mit **501 Not Implemented** in der einheitlichen
> Fehler-Envelope. Fertig ist in diesem Schritt ausschließlich `GET /health`.

## Tech-Stack

- **Sprache**: Python 3.12+
- **Web-Framework**: FastAPI mit Uvicorn
- **Validierung**: Pydantic v2, Konfiguration via pydantic-settings
- **ORM**: SQLAlchemy 2.0 (typisierte Modelle, Session als Dependency)
- **Datenbank**: SQLite als Datei neben der Anwendung (kein Datenbankserver)
- **Tests**: pytest mit FastAPI-TestClient und eigener Test-Datenbank
- **Dokumentation**: OpenAPI/Swagger automatisch über FastAPI

## Installation

```bash
python -m pip install -r requirements.txt
```

## Konfiguration

| Variable           | Erforderlich | Beschreibung                                                                 |
| ------------------ | ------------ | ---------------------------------------------------------------------------- |
| `LIBRARY_API_KEY`  | optional     | API-Key für alle Schreibzugriffe (`X-API-Key`). Ist er nicht gesetzt, startet die Anwendung trotzdem; alle Schreibzugriffe antworten dann mit `401`. Der Wert ist ein Geheimnis und gehört nicht ins Repository; `RUN.json` erzeugt ihn pro Lauf. |
| `DATABASE_URL`     | optional     | SQLAlchemy-URL der Datenbank. Standard: `sqlite:///./library.db` (Datei neben der Anwendung). |

Lokal setzt man den Key zum Beispiel als Umgebungsvariable:

```bash
export LIBRARY_API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

## Starten (Entwicklung und Betrieb)

Die Anwendung wird als Uvicorn-Server aus dem Repository-Wurzelverzeichnis
gestartet:

```bash
python -m uvicorn app.main:app --port 8000
```

Das Datenbankschema wird beim Start automatisch angelegt (`create_all` im
Lifespan), es ist keine Migration und keine manuelle Einrichtung nötig. Danach
sind erreichbar:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI-Schema: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

Ein separat auszuführender Produktions-Build existiert nicht; der Startbefehl
oben ist zugleich der Produktionsstart (ohne `--reload`). Die maschinenlesbare
Startbeschreibung liegt in [`RUN.json`](RUN.json).

## Tests

```bash
python -m pytest
```

Die Suite läuft offline gegen eine eigene, pro Test isolierte SQLite-Datenbank
und fasst die Entwicklungs-Datenbank nicht an.

## Verwendung — die API

Alle GET-Endpunkte sind öffentlich. Jeder Schreib-Endpunkt (`POST`, `PUT`,
`PATCH`, `DELETE`) verlangt den Header `X-API-Key` mit dem konfigurierten Wert.

### Fehlerformat

Jede Fehlerantwort hat dieselbe Envelope:

```json
{"error": {"code": "not_found", "message": "Book 42 not found"}}
```

Stabile Codes: `unauthorized` (401), `not_found` (404), `conflict` (409),
`validation_error` (422, nennt das betroffene Feld), `internal_error` (500),
`not_implemented` (501). Erfolgreiche Antworten enthalten niemals einen
`error`-Schlüssel.

### Endpunkte

| Methode | Pfad                        | Body / Query                          | Erfolg                | Fehler                     |
| ------- | --------------------------- | ------------------------------------- | --------------------- | -------------------------- |
| GET     | `/health`                   | –                                     | 200 `{"status":"ok"}` | –                          |
| POST    | `/books`                    | `BookWrite`                           | 201 `BookRead`        | 401, 409, 422              |
| GET     | `/books`                    | `q`, `limit` (1–100, Default 20), `offset` (≥ 0) | 200 `BookPage` | 422                 |
| GET     | `/books/{book_id}`          | –                                     | 200 `BookRead`        | 404                        |
| PUT     | `/books/{book_id}`          | `BookWrite`                           | 200 `BookRead`        | 401, 404, 409, 422         |
| PATCH   | `/books/{book_id}`          | `BookPatch`                           | 200 `BookRead`        | 401, 404, 409, 422         |
| DELETE  | `/books/{book_id}`          | –                                     | 204 (kein Body)       | 401, 404, 409              |
| POST    | `/members`                  | `MemberWrite`                         | 201 `MemberRead`      | 401, 409, 422              |
| GET     | `/members`                  | `limit`, `offset`                     | 200 `MemberPage`      | 422                        |
| GET     | `/members/{member_id}`      | –                                     | 200 `MemberRead`      | 404                        |
| PUT     | `/members/{member_id}`      | `MemberWrite`                         | 200 `MemberRead`      | 401, 404, 409, 422         |
| PATCH   | `/members/{member_id}`      | `MemberPatch`                         | 200 `MemberRead`      | 401, 404, 409, 422         |
| DELETE  | `/members/{member_id}`      | –                                     | 204 (kein Body)       | 401, 404, 409              |
| POST    | `/loans`                    | `{"book_id": int, "member_id": int}`  | 201 `LoanRead`        | 401, 404, 409, 422         |
| POST    | `/loans/{loan_id}/return`   | –                                     | 200 `LoanRead`        | 401, 404, 409              |
| GET     | `/loans/overdue`            | `limit`, `offset`                     | 200 `OverduePage`     | 422                        |

### Schemas (Auszug)

- `BookWrite` `{title, author, isbn, published_year, copies}` — `title`/`author`/`isbn` nicht leer, `published_year` 1000 bis aktuelles Jahr + 1, `copies` ≥ 0.
- `BookPatch` — dieselben Felder, alle optional.
- `BookRead` `{id, title, author, isbn, published_year, copies}`.
- `MemberWrite` `{name, email}` — gültige E-Mail; `MemberRead` zusätzlich `id`, `member_since` (ISO-Datum).
- `LoanRead` `{id, book_id, member_id, loaned_at, due_at, returned_at}`.
- `OverdueLoanRead` `{book_id, member_id, loaned_at, due_at, days_overdue}`.
- `BookPage` / `MemberPage` / `OverduePage` `{items, total, limit, offset}`.

Beispiel — Buch anlegen:

```bash
curl -X POST http://localhost:8000/books \
  -H "X-API-Key: $LIBRARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Der Process","author":"Franz Kafka","isbn":"978-3-596-90034-5","published_year":1925,"copies":3}'
```

## Funktionsumfang

- Bücher-CRUD mit Suche (`q`) und Paginierung (`limit`, `offset`)
- Mitglieder-CRUD mit Paginierung
- Ausleihen mit Ausleihdatum und Rückgabefrist (14 Tage)
- Rückgabe über einen eigenen Endpunkt
- Overdue-Liste mit `days_overdue`
- API-Key-Schutz für alle Schreibzugriffe
- Einheitliche Fehler-Envelope mit stabilen Codes
- Automatisch generierte OpenAPI-Dokumentation
