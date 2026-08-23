"""Standalone smoke test for account and persistence behavior."""

from __future__ import annotations

import os
import site
from pathlib import Path


ROOT = Path(__file__).parent
DATABASE = ROOT / "test_buildmode.db"
site.addsitedir(str(ROOT / ".deps"))
os.environ["DATABASE_URL"] = f"sqlite:///{DATABASE.as_posix()}"

from data_store import (authenticate, create_user, delete_account, engine, initialise_database,
                        load_day, load_habits, save_day, save_habits)


def run() -> None:
    initialise_database()
    user_id, message = create_user("amara@example.com", "Amara Eze", "a-secure-password")
    assert user_id is not None, message
    assert authenticate("AMARA@example.com", "a-secure-password") is not None
    assert authenticate("amara@example.com", "wrong-password") is None
    save_habits(user_id, ["Deep work", "Exercise"])
    assert load_habits(user_id, []) == ["Deep work", "Exercise"]
    save_day(user_id, "2026-08-23", {"Deep work": True}, "Ship the app", "Good focus")
    record = load_day(user_id, "2026-08-23")
    assert record["checks"]["Deep work"] is True
    assert record["intention"] == "Ship the app"
    delete_account(user_id)
    assert authenticate("amara@example.com", "a-secure-password") is None
    engine.dispose()
    DATABASE.unlink(missing_ok=True)
    print("All data-store tests passed.")


if __name__ == "__main__":
    run()
