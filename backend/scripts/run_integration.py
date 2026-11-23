"""Run the real PostgreSQL check using backend/.env without printing its password."""
import os
import subprocess
import sys

from app.config import BACKEND_ROOT, Settings

if __name__ == "__main__":
    settings = Settings()
    environment = os.environ.copy()
    environment["TEST_DATABASE_URL"] = settings.database_url().render_as_string(hide_password=False)
    raise SystemExit(subprocess.call(
        [sys.executable, "-m", "pytest", "-q", "-m", "integration"],
        cwd=BACKEND_ROOT, env=environment,
    ))
