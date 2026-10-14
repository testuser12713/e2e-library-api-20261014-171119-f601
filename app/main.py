"""FastAPI application: routers, error envelope and the health endpoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models
from .database import engine
from .errors import register_exception_handlers
from .routers import books, loan_returns, loans, members, overdue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the database schema on startup so a fresh start is immediately usable."""
    models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Stadtbibliothek Ausleih-API",
    version="0.1.0",
    description="REST-API für die Ausleihe einer kleinen Stadtbibliothek.",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(books.router)
app.include_router(members.router)
app.include_router(loans.router)
app.include_router(loan_returns.router)
app.include_router(overdue.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
