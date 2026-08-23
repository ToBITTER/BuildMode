"""BuildMode: Streamlit UI for CV creation and a personal discipline tracker."""

from __future__ import annotations

import calendar
import os
import re
from datetime import date
from typing import Any

import streamlit as st

# Streamlit Community Cloud supplies secrets through st.secrets rather than the
# process environment used by other hosts.
if "DATABASE_URL" not in os.environ:
    try:
        if "DATABASE_URL" in st.secrets:
            os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
    except FileNotFoundError:
        pass

from data_store import (authenticate, create_user, delete_account, initialise_database, load_day,
                        load_habits, save_day, save_habits)
from docx_builder import build_docx
from pdf_builder import build_pdf


st.set_page_config(page_title="BuildMode", page_icon="◼", layout="wide")


@st.cache_resource
def _database_ready() -> bool:
    initialise_database()
    return True


try:
    _database_ready()
except Exception:
    st.error("BuildMode could not connect to its database. Check DATABASE_URL and restart the service.")
    st.stop()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');
    html, body, [class*="css"] {font-family: 'DM Sans', sans-serif;}
    .stApp {background: radial-gradient(circle at 90% 5%, #fff6df 0, #f8f2e7 35%, #f3ede2 100%); color: #17202a;}
    [data-testid="stSidebar"] {background: linear-gradient(165deg, #132d27, #091c18);}
    [data-testid="stSidebar"] * {color: #fff;}
    .hero {position:relative; overflow:hidden; padding: 2rem 2.1rem; border-radius: 24px;
      background: linear-gradient(135deg, #123c32, #1e5948); color: white; margin-bottom: 1.3rem;
      box-shadow: 0 18px 50px #123c3230;}
    .hero:after {content:''; position:absolute; width:220px; height:220px; border-radius:50%;
      background:#e8bd6122; right:-55px; top:-100px; border:1px solid #fff2;}
    .hero h1 {font-family:'Playfair Display',serif; margin:0; font-size:2.55rem; letter-spacing:-.03em;}
    .hero p {margin:.5rem 0 0; color:#e4eee9; max-width:620px; font-size:1.05rem;}
    .card {border: 1px solid #d9d1c1; border-radius: 14px; padding: .8rem 1rem;
      background: #fffdf8; margin: .4rem 0 .8rem;}
    [data-testid="stVerticalBlockBorderWrapper"] {background:#fffdf9; border-color:#ded5c4!important;
      border-radius:18px!important; box-shadow:0 6px 24px #554b3e0a;}
    div.stButton > button, div.stDownloadButton > button {border-radius:12px; min-height:2.8rem;
      font-weight:700; transition:all .18s ease;}
    div.stButton > button:hover, div.stDownloadButton > button:hover {transform:translateY(-1px); box-shadow:0 7px 18px #123c3220;}
    h2, h3 {color:#123c32; letter-spacing:-.02em;}
    [data-testid="stMetric"] {background:#fffdf8; border:1px solid #ded5c4; border-radius:16px; padding:1rem;}
    .eyebrow {color:#a67519; font-weight:700; text-transform:uppercase; font-size:.73rem; letter-spacing:.14em;}
    .tour-card {padding:1.4rem; background:linear-gradient(145deg,#fffdf8,#f8edda); border:1px solid #decda9;
      border-radius:18px; margin:.5rem 0 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _education() -> dict[str, str]:
    return {"school": "", "location": "", "dates": "", "degree": "", "detail": ""}


def _experience() -> dict[str, Any]:
    return {"organisation": "", "location": "", "role": "", "dates": "", "bullets": [""]}


def _init_state(user_id: int) -> None:
    starter_habits = ["Wake up early", "Workout", "Read 20 pages", "No phone first hour", "Meditate", "Journal"]
    defaults: dict[str, Any] = {
        "education": [_education()], "work_experience": [_experience()],
        "leadership_experience": [_experience()], "certifications": [""],
        "habits": load_habits(user_id, starter_habits),
        "habit_checks": {}, "generated_cv": None, "generated_pdf": None,
        "tour_step": 0, "tour_open": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _add(list_key: str, value: Any) -> None:
    limits = {"education": 10, "work_experience": 15, "leadership_experience": 15, "certifications": 30}
    if len(st.session_state[list_key]) >= limits.get(list_key, 30):
        st.warning("You have reached the limit for this section.")
        return
    st.session_state[list_key].append(value)
    st.rerun()


def _remove(list_key: str, index: int) -> None:
    st.session_state[list_key].pop(index)
    if list_key == "habits" and st.session_state.get("user"):
        save_habits(st.session_state.user["id"], st.session_state.habits)
    st.rerun()


def _auth_page() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">Welcome to BuildMode</div><h1>Build the life behind the résumé.</h1><p>Create exceptional CVs and turn everyday discipline into visible progress.</p></div>', unsafe_allow_html=True)
    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", max_chars=254)
            password = st.text_input("Password", type="password", max_chars=128)
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            user = authenticate(email, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Email or password is incorrect.")
    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Your name", max_chars=100)
            email = st.text_input("Email address", max_chars=254, key="signup_email")
            password = st.text_input("Password", type="password", max_chars=128, help="Use at least 10 characters.")
            consent = st.checkbox("I agree to BuildMode storing my account and discipline data.")
            submitted = st.form_submit_button("Create my account", type="primary", use_container_width=True)
        if submitted:
            if not consent:
                st.warning("Please confirm the data-storage notice to continue.")
            else:
                user_id, message = create_user(email, name, password)
                if user_id:
                    st.session_state.user = {"id": user_id, "email": email.strip().lower(), "display_name": name.strip()}
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    st.caption("Your CV form is processed in memory and is not saved to your account. Discipline records are private to your login.")


TOUR = [
    ("Welcome to BuildMode", "You have two focused tools: create a professional CV and build a daily discipline system."),
    ("Create your CV", "Open CV Studio, fill only the sections you need, and add or remove entries and achievement bullets freely."),
    ("Export anywhere", "Generate once, then download the same CV as an editable Word file or a ready-to-send PDF."),
    ("Build consistency", "Use Discipline System for daily habits, intentions, reflections, and month-by-month completion checks."),
]


@st.dialog("Quick tour")
def _tour() -> None:
    step = min(st.session_state.tour_step, len(TOUR) - 1)
    title, body = TOUR[step]
    st.markdown(f'<div class="eyebrow">Step {step + 1} of {len(TOUR)}</div><div class="tour-card"><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)
    st.progress((step + 1) / len(TOUR))
    back, next_col = st.columns(2)
    if step and back.button("← Back", use_container_width=True):
        st.session_state.tour_step -= 1
        st.rerun()
    label = "Start building →" if step == len(TOUR) - 1 else "Next →"
    if next_col.button(label, type="primary", use_container_width=True):
        if step == len(TOUR) - 1:
            st.session_state.tour_open = False
        else:
            st.session_state.tour_step += 1
        st.rerun()


def _experience_editor(title: str, state_key: str) -> None:
    st.subheader(title)
    for i, entry in enumerate(st.session_state[state_key]):
        with st.container(border=True):
            top, remove = st.columns([8, 1])
            top.markdown(f"**Entry {i + 1}**")
            if remove.button("Remove", key=f"remove_{state_key}_{i}"):
                _remove(state_key, i)
            c1, c2 = st.columns(2)
            entry["organisation"] = c1.text_input("Organisation", entry["organisation"], key=f"org_{state_key}_{i}")
            entry["location"] = c2.text_input("Location", entry["location"], key=f"loc_{state_key}_{i}")
            entry["role"] = c1.text_input("Role / title", entry["role"], key=f"role_{state_key}_{i}")
            entry["dates"] = c2.text_input("Dates", entry["dates"], key=f"dates_{state_key}_{i}")
            st.markdown("**Achievement bullets**")
            for j, bullet in enumerate(entry["bullets"]):
                text_col, button_col = st.columns([9, 1])
                entry["bullets"][j] = text_col.text_input("Bullet", bullet, key=f"bullet_{state_key}_{i}_{j}", label_visibility="collapsed")
                if button_col.button("×", key=f"del_bullet_{state_key}_{i}_{j}"):
                    entry["bullets"].pop(j)
                    st.rerun()
            if st.button("+ Add bullet", key=f"add_bullet_{state_key}_{i}"):
                if len(entry["bullets"]) < 12:
                    entry["bullets"].append("")
                else:
                    st.warning("Each role can contain up to 12 bullets.")
                st.rerun()
    if st.button(f"+ Add {title.lower()} entry", key=f"add_{state_key}"):
        _add(state_key, _experience())


def _cv_page() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">Career Studio</div><h1>Your story, professionally told.</h1><p>Build an elegant CV that matches the supplied reference and export it as Word or PDF.</p></div>', unsafe_allow_html=True)
    st.subheader("Personal information")
    c1, c2 = st.columns(2)
    full_name = c1.text_input("Full name", key="full_name")
    phone = c2.text_input("Phone", key="phone")
    email = c1.text_input("Email", key="email")
    linkedin = c2.text_input("LinkedIn URL", key="linkedin")

    st.subheader("Education")
    for i, entry in enumerate(st.session_state.education):
        with st.container(border=True):
            top, remove = st.columns([8, 1])
            top.markdown(f"**Education {i + 1}**")
            if remove.button("Remove", key=f"remove_education_{i}"):
                _remove("education", i)
            a, b = st.columns(2)
            entry["school"] = a.text_input("School", entry["school"], key=f"school_{i}")
            entry["location"] = b.text_input("Location", entry["location"], key=f"edu_location_{i}")
            entry["degree"] = a.text_input("Degree / programme", entry["degree"], key=f"degree_{i}")
            entry["dates"] = b.text_input("Dates", entry["dates"], key=f"edu_dates_{i}")
            entry["detail"] = st.text_input("Detail (CGPA, class of degree, etc.)", entry["detail"], key=f"detail_{i}")
    if st.button("+ Add education"):
        _add("education", _education())

    _experience_editor("Work experience", "work_experience")
    _experience_editor("Leadership & volunteer experience", "leadership_experience")

    st.subheader("Certifications & courses")
    for i, certification in enumerate(st.session_state.certifications):
        text_col, remove_col = st.columns([9, 1])
        st.session_state.certifications[i] = text_col.text_input("Certification", certification, key=f"cert_{i}", label_visibility="collapsed")
        if remove_col.button("×", key=f"remove_cert_{i}"):
            _remove("certifications", i)
    if st.button("+ Add certification"):
        _add("certifications", "")

    st.subheader("Skills & interests")
    technical = st.text_area("Technical skills (comma-separated)", key="technical_skills")
    strengths = st.text_area("Strengths (comma-separated)", key="strengths")

    data = {"full_name": full_name, "phone": phone, "email": email, "linkedin": linkedin,
            "education": st.session_state.education, "work_experience": st.session_state.work_experience,
            "leadership_experience": st.session_state.leadership_experience,
            "certifications": st.session_state.certifications, "technical_skills": technical, "strengths": strengths}
    filled = sum(bool(value.strip()) for value in (full_name, phone, email, technical, strengths))
    st.caption(f"Profile completion · {filled}/5 essentials")
    st.progress(filled / 5)
    if st.button("Generate CV", type="primary", use_container_width=True):
        if len(str(data)) > 50_000:
            st.error("This CV contains too much text. Shorten some entries and try again.")
        else:
            st.session_state.generated_cv = build_docx(data).getvalue()
            st.session_state.generated_pdf = build_pdf(data).getvalue()
            st.toast("Your CV is ready in both formats.", icon="✅")
    if st.session_state.generated_cv and st.session_state.generated_pdf:
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", full_name.strip()) or "My"
        word_col, pdf_col = st.columns(2)
        word_col.download_button("Download editable Word", st.session_state.generated_cv, f"{safe_name}_CV.docx",
                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        pdf_col.download_button("Download ready-to-send PDF", st.session_state.generated_pdf, f"{safe_name}_CV.pdf",
                                "application/pdf", use_container_width=True)


def _discipline_page() -> None:
    today = date.today()
    user_id = st.session_state.user["id"]
    today_key = today.isoformat()
    today_record = load_day(user_id, today_key)
    st.markdown('<div class="hero"><div class="eyebrow">Daily Momentum</div><h1>My Discipline System</h1><p>Small promises, kept daily. Discipline today. Freedom tomorrow.</p></div>', unsafe_allow_html=True)
    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Daily non-negotiables")
        completed = 0
        for i, habit in enumerate(st.session_state.habits):
            row, remove = st.columns([8, 1])
            key = f"done_{today_key}_{i}_{abs(hash(habit))}"
            checked = row.checkbox(habit or f"Habit {i + 1}", value=bool(today_record["checks"].get(habit)), key=key)
            completed += int(checked)
            if remove.button("×", key=f"remove_habit_{i}"):
                _remove("habits", i)
        new_habit = st.text_input("New habit", key="new_habit", placeholder="e.g. Drink 3L water")
        if st.button("+ Add habit") and new_habit.strip():
            if len(st.session_state.habits) >= 30:
                st.warning("You can track up to 30 habits.")
            else:
                st.session_state.habits.append(new_habit.strip()[:120])
                save_habits(user_id, st.session_state.habits)
            st.rerun()
    with right:
        total = len(st.session_state.habits)
        score = round(100 * completed / total) if total else 0
        st.subheader("Today")
        st.metric("Overall progress", f"{score}%", f"{completed} of {total} habits")
        st.progress(score / 100 if total else 0)
        intention_key, reflection_key = f"intention_{today_key}", f"reflection_{today_key}"
        intention = st.text_area("Today I will…", value=today_record["intention"], key=intention_key,
                                 max_chars=2000, placeholder="Stay focused\nBlock out distractions")
        reflection = st.text_area("Notes / reflections", value=today_record["reflection"], key=reflection_key,
                                  max_chars=4000, placeholder="What worked? What needs to change?")
        if st.button("Save today's check-in", type="primary", use_container_width=True):
            checks = {habit: bool(st.session_state.get(f"done_{today_key}_{i}_{abs(hash(habit))}", False))
                      for i, habit in enumerate(st.session_state.habits)}
            save_day(user_id, today_key, checks, intention, reflection)
            st.toast("Today's progress is safely saved.", icon="✅")

    st.subheader(f"Habit tracker — {today.strftime('%B %Y')}")
    days = calendar.monthrange(today.year, today.month)[1]
    chosen_day = st.number_input("Day to update", 1, days, today.day)
    selected_date = date(today.year, today.month, int(chosen_day)).isoformat()
    selected_record = load_day(user_id, selected_date)
    with st.container(border=True):
        for i, habit in enumerate(st.session_state.habits):
            key = f"track_{selected_date}_{i}_{abs(hash(habit))}"
            st.checkbox(habit, value=bool(selected_record["checks"].get(habit)), key=key)
        if st.button("Save selected day", use_container_width=True):
            checks = {habit: bool(st.session_state.get(f"track_{selected_date}_{i}_{abs(hash(habit))}", False))
                      for i, habit in enumerate(st.session_state.habits)}
            save_day(user_id, selected_date, checks, selected_record["intention"], selected_record["reflection"])
            st.toast(f"Progress for {selected_date} saved.", icon="✅")
    st.caption("Choose a day and save its completed habits. Records remain available after signing out or restarting the app.")


if "user" not in st.session_state:
    _auth_page()
    st.stop()

_init_state(st.session_state.user["id"])
if st.session_state.tour_open:
    _tour()
page = st.sidebar.radio("BuildMode", ["CV Studio", "Discipline System"])
st.sidebar.caption("Build your career. Build your habits.")
st.sidebar.caption(f"Signed in as {st.session_state.user['display_name']}")
if st.sidebar.button("Take the tour", use_container_width=True):
    st.session_state.tour_step = 0
    st.session_state.tour_open = True
    st.rerun()
if st.sidebar.button("Sign out", use_container_width=True):
    st.session_state.clear()
    st.rerun()
with st.sidebar.expander("Privacy & account"):
    st.caption("CV form data is not stored. You can permanently erase your account and discipline history here.")
    confirm_delete = st.checkbox("I understand this cannot be undone", key="confirm_delete")
    if st.button("Delete my account", disabled=not confirm_delete, use_container_width=True):
        delete_account(st.session_state.user["id"])
        st.session_state.clear()
        st.rerun()
if page == "CV Studio":
    _cv_page()
else:
    _discipline_page()
