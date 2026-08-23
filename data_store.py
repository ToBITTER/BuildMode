"""Authentication and persistent user data for BuildMode."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///buildmode.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
Session = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    profile: Mapped["UserProfile"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    days: Mapped[list["DailyRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    habits_json: Mapped[str] = mapped_column(Text, default="[]")
    user: Mapped[User] = relationship(back_populates="profile")


class DailyRecord(Base):
    __tablename__ = "daily_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    checks_json: Mapped[str] = mapped_column(Text, default="{}")
    intention: Mapped[str] = mapped_column(Text, default="")
    reflection: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user: Mapped[User] = relationship(back_populates="days")


def initialise_database() -> None:
    Base.metadata.create_all(engine)


def _password_hash(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=actual_salt, n=2**14, r=8, p=1)
    return f"scrypt${actual_salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, expected = stored.split("$", 2)
        if algorithm != "scrypt":
            return False
        actual = _password_hash(password, bytes.fromhex(salt_hex)).split("$", 2)[2]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_user(email: str, display_name: str, password: str) -> tuple[int | None, str]:
    normalised = email.strip().lower()
    if not normalised or "@" not in normalised or len(normalised) > 254:
        return None, "Enter a valid email address."
    if len(display_name.strip()) < 2 or len(display_name.strip()) > 100:
        return None, "Your name must contain 2–100 characters."
    if len(password) < 10 or len(password) > 128:
        return None, "Use a password containing 10–128 characters."
    with Session.begin() as session:
        if session.scalar(select(User).where(User.email == normalised)):
            return None, "An account with this email already exists."
        user = User(email=normalised, display_name=display_name.strip(), password_hash=_password_hash(password))
        user.profile = UserProfile(habits_json="[]")
        session.add(user)
        session.flush()
        return user.id, "Account created."


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    with Session() as session:
        user = session.scalar(select(User).where(User.email == email.strip().lower()))
        if not user or not _password_matches(password, user.password_hash):
            return None
        return {"id": user.id, "email": user.email, "display_name": user.display_name}


def load_habits(user_id: int, defaults: list[str]) -> list[str]:
    with Session() as session:
        profile = session.get(UserProfile, user_id)
        if not profile:
            return defaults
        try:
            values = json.loads(profile.habits_json)
            return [str(value)[:120] for value in values] if isinstance(values, list) and values else defaults
        except json.JSONDecodeError:
            return defaults


def save_habits(user_id: int, habits: list[str]) -> None:
    clean = [habit.strip()[:120] for habit in habits if habit.strip()][:30]
    with Session.begin() as session:
        profile = session.get(UserProfile, user_id)
        if profile:
            profile.habits_json = json.dumps(clean)


def load_day(user_id: int, day: str) -> dict[str, Any]:
    with Session() as session:
        record = session.scalar(select(DailyRecord).where(DailyRecord.user_id == user_id, DailyRecord.day == day))
        if not record:
            return {"checks": {}, "intention": "", "reflection": ""}
        try:
            checks = json.loads(record.checks_json)
        except json.JSONDecodeError:
            checks = {}
        return {"checks": checks if isinstance(checks, dict) else {}, "intention": record.intention,
                "reflection": record.reflection}


def save_day(user_id: int, day: str, checks: dict[str, bool], intention: str, reflection: str) -> None:
    with Session.begin() as session:
        record = session.scalar(select(DailyRecord).where(DailyRecord.user_id == user_id, DailyRecord.day == day))
        if not record:
            record = DailyRecord(user_id=user_id, day=day)
            session.add(record)
        record.checks_json = json.dumps({str(key)[:120]: bool(value) for key, value in checks.items()})
        record.intention = intention[:2000]
        record.reflection = reflection[:4000]
        record.updated_at = datetime.now(timezone.utc)


def delete_account(user_id: int) -> None:
    with Session.begin() as session:
        # Explicit deletes also guarantee privacy cleanup on local SQLite,
        # where foreign-key cascades may not be enabled by the host build.
        session.execute(delete(DailyRecord).where(DailyRecord.user_id == user_id))
        session.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
        session.execute(delete(User).where(User.id == user_id))
