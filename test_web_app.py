"""Smoke-test the Flask API and browser entry point."""
from __future__ import annotations
import os
import site
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "test_web.db"
site.addsitedir(str(ROOT / ".deps"))
os.environ["DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-only-secret"

from app import app
from data_store import engine


def run() -> None:
    app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    client = app.test_client()
    assert client.get("/").status_code == 200
    signup = client.post("/api/signup", json={"display_name": "Amara Eze", "email": "amara@example.com",
                                               "password": "a-secure-password"})
    assert signup.status_code == 201, signup.get_json()
    assert client.get("/api/habits").status_code == 200
    assert client.put("/api/habits", json={"habits": ["Deep work", "Exercise"]}).status_code == 200
    assert client.put("/api/days/2026-08-23", json={"checks": {"Deep work": True},
                                                     "intention": "Ship", "reflection": "Focused"}).status_code == 200
    cv = {"full_name": "Amara Eze", "education": [], "work_experience": [],
          "leadership_experience": [], "certifications": []}
    assert client.post("/api/cv/docx", json=cv).data.startswith(b"PK")
    assert client.post("/api/cv/pdf", json=cv).data.startswith(b"%PDF-")
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/habits").status_code == 401
    engine.dispose(); DB.unlink(missing_ok=True)
    print("All Flask web tests passed.")


if __name__ == "__main__": run()
