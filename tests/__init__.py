"""Test package.

Point the application engine at an isolated per-session SQLite file before any
application module is imported, so the test run never touches the development
database.
"""

import os
import tempfile

_TEST_DB_DIR = tempfile.mkdtemp(prefix="library-api-test-db-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(_TEST_DB_DIR, 'app.db')}")
