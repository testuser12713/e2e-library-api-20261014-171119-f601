"""SQLAlchemy 2.0 models for books, members and loans."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .clock import today
from .database import Base


class Book(Base):
    """A book title held by the library."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    isbn: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    published_year: Mapped[int] = mapped_column(Integer, nullable=False)
    copies: Mapped[int] = mapped_column(Integer, nullable=False)


class Member(Base):
    """A library member."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    member_since: Mapped[date] = mapped_column(Date, nullable=False, default=today)


class Loan(Base):
    """An open or returned loan of a book to a member.

    Foreign keys deliberately have no cascade delete: a book or member that is
    still referenced by a loan must not be deletable.
    """

    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    loaned_at: Mapped[date] = mapped_column(Date, nullable=False)
    due_at: Mapped[date] = mapped_column(Date, nullable=False)
    returned_at: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
