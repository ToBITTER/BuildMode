"""TRAQ Flask API and web entry point."""
from __future__ import annotations

import os
import re
import logging
from datetime import timedelta
from io import BytesIO
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from data_store import (authenticate, create_user, delete_account, initialise_database, load_day,
                        load_habits, load_platform_activity, save_day, save_habits)
from docx_builder import build_docx
from pdf_builder import build_pdf

app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", "local-development-only-change-me"),
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")), SESSION_COOKIE_NAME="traq_session",
                  PERMANENT_SESSION_LIFETIME=timedelta(days=14), MAX_CONTENT_LENGTH=256 * 1024)
limiter = Limiter(get_remote_address, app=app, default_limits=["300 per hour"], storage_uri="memory://")
initialise_database()
STARTER_HABITS = ["Wake up early", "Workout", "Read 20 pages", "No phone first hour", "Meditate", "Journal"]
PLATFORM_ADMIN_EMAILS = {"tobiloba.gbenle@gmail.com", *{
    email.strip().lower() for email in os.getenv("PLATFORM_ADMIN_EMAILS", "").split(",") if email.strip()
}}


def _uid() -> int | None:
    return session.get("user_id") if isinstance(session.get("user_id"), int) else None


def _json() -> dict[str, Any]:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _unauthorised() -> tuple[Any, int]:
    return jsonify({"error": "Sign in to continue."}), 401


def _is_platform_admin() -> bool:
    return bool(_uid()) and str(session.get("email", "")).strip().lower() in PLATFORM_ADMIN_EMAILS


@app.errorhandler(429)
def rate_limited(_error: Any) -> tuple[Any, int]:
    return jsonify({"error": "Too many attempts. Wait one minute and try again."}), 429


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/health")
def health() -> tuple[str, int]:
    return "ok", 200


@app.get("/api/me")
def me() -> Any:
    user = None if not _uid() else {"id": _uid(), "email": session.get("email"), "display_name": session.get("display_name")}
    return jsonify({"user": user})


@app.post("/api/signup")
@limiter.limit("5 per minute")
def signup() -> Any:
    data = _json()
    user_id, message = create_user(str(data.get("email", "")), str(data.get("display_name", "")), str(data.get("password", "")))
    if not user_id:
        return jsonify({"error": message}), 400
    session.clear()
    session.permanent = True
    session.update(user_id=user_id, email=str(data.get("email", "")).strip().lower(), display_name=str(data.get("display_name", "")).strip())
    return jsonify({"message": message, "user": {"id": user_id, "email": session["email"], "display_name": session["display_name"]}}), 201


@app.post("/api/login")
@limiter.limit("8 per minute")
def login() -> Any:
    data = _json()
    user = authenticate(str(data.get("email", "")), str(data.get("password", "")))
    if not user:
        return jsonify({"error": "Email or password is incorrect."}), 401
    session.clear()
    session.permanent = True
    session.update(user_id=user["id"], email=user["email"], display_name=user["display_name"])
    return jsonify({"user": user})


@app.post("/api/logout")
def logout() -> Any:
    session.clear()
    return jsonify({"message": "Signed out."})


@app.get("/api/platform/users")
def platform_users() -> Any:
    if not _uid():
        return _unauthorised()
    if not _is_platform_admin():
        return jsonify({"error": "Platform administrator access is required."}), 403
    return jsonify(load_platform_activity())


@app.get("/api/habits")
def get_habits() -> Any:
    return _unauthorised() if not _uid() else jsonify({"habits": load_habits(_uid(), STARTER_HABITS)})


@app.put("/api/habits")
def put_habits() -> Any:
    if not _uid(): return _unauthorised()
    values = _json().get("habits", [])
    if not isinstance(values, list) or len(values) > 30: return jsonify({"error": "Provide no more than 30 habits."}), 400
    save_habits(_uid(), [str(value) for value in values])
    return jsonify({"message": "Habits saved."})


@app.get("/api/days/<day>")
def get_day(day: str) -> Any:
    if not _uid(): return _unauthorised()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day): return jsonify({"error": "Invalid date."}), 400
    return jsonify(load_day(_uid(), day))


@app.put("/api/days/<day>")
def put_day(day: str) -> Any:
    if not _uid(): return _unauthorised()
    data = _json(); checks = data.get("checks", {})
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or not isinstance(checks, dict) or len(checks) > 30:
        return jsonify({"error": "Invalid discipline record."}), 400
    save_day(_uid(), day, checks, str(data.get("intention", "")), str(data.get("reflection", "")))
    return jsonify({"message": "Progress saved."})


def _cv_data() -> dict[str, Any] | None:
    data = _json()
    return data if _uid() and len(str(data)) <= 50_000 else None


def _download(kind: str) -> Any:
    data = _cv_data()
    if data is None: return jsonify({"error": "Sign in or shorten the CV content."}), 400
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(data.get("full_name", "")).strip()) or "My"
    try:
        if kind == "docx":
            output = build_docx(data)
            return send_file(output, as_attachment=True, download_name=f"{name}_CV.docx",
                             mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             max_age=0)
        output = build_pdf(data)
        return send_file(output, as_attachment=True, download_name=f"{name}_CV.pdf",
                         mimetype="application/pdf", max_age=0)
    except Exception:
        logging.exception("TRAQ %s export failed", kind)
        return jsonify({"error": f"The {kind.upper()} could not be generated. Please shorten unusually long entries and try again."}), 500


@app.post("/api/cv/docx")
@limiter.limit("20 per hour")
def cv_docx() -> Any: return _download("docx")


@app.post("/api/cv/pdf")
@limiter.limit("20 per hour")
def cv_pdf() -> Any: return _download("pdf")


@app.delete("/api/account")
def remove_account() -> Any:
    if not _uid(): return _unauthorised()
    delete_account(_uid()); session.clear()
    return jsonify({"message": "Account deleted."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
