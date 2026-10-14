"""Single source of truth for the current date.

Keeping ``today`` in one place makes it monkeypatchable by the tests, so due
dates, loan dates and the overdue boundary are all derived from the same value.
"""

from datetime import date


def today() -> date:
    """Return the current local date."""
    return date.today()
