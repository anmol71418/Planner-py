"""Study Planner with Exam Countdown  (Streamlit)
Run:  pip install streamlit pandas
      streamlit run planner.py
"""
import json
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

DATA_FILE = "subjects.json"


# ---------- 1. Data model ----------
class Subject:
    def __init__(self, name, exam_date, difficulty, topics=None, done=None):
        self.name = name
        self.exam_date = exam_date          # datetime.date
        self.difficulty = difficulty        # 1-5
        self.topics = topics or []          # list of topic names
        self.done = done or []              # list of completed topics

    def days_left(self):
        return (self.exam_date - date.today()).days

    def progress(self):
        if not self.topics:
            return 0.0
        return len(self.done) / len(self.topics)

    def priority(self):
        """Higher = needs more time. Harder, closer, less-finished subjects rank higher."""
        days = max(self.days_left(), 1)
        remaining = 1 - self.progress()
        return (self.difficulty / days) * (0.5 + remaining)

    def to_dict(self):
        return {
            "name": self.name,
            "exam_date": self.exam_date.isoformat(),
            "difficulty": self.difficulty,
            "topics": self.topics,
            "done": self.done,
        }

    @staticmethod
    def from_dict(d):
        return Subject(
            d["name"],
            datetime.strptime(d["exam_date"], "%Y-%m-%d").date(),
            d["difficulty"],
            d["topics"],
            d["done"],
        )


# ---------- 2. Save / load ----------
def load_subjects():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE) as f:
            return [Subject.from_dict(d) for d in json.load(f)]
    except (json.JSONDecodeError, KeyError):
        return []


def save_subjects(subjects):
    with open(DATA_FILE, "w") as f:
        json.dump([s.to_dict() for s in subjects], f, indent=2)


# ---------- 3. Timetable algorithm ----------
def make_timetable(subjects, hours_per_day):
    upcoming = [s for s in subjects if s.days_left() >= 0]
    total = sum(s.priority() for s in upcoming)
    if total == 0:
        return []
    rows = []
    for s in sorted(upcoming, key=lambda x: x.priority(), reverse=True):
        hours = round(hours_per_day * s.priority() / total, 1)
        next_topic = next((t for t in s.topics if t not in s.done), "Revise")
        rows.append({"Subject": s.name, "Hours today": hours, "Focus on": next_topic})
    return rows


# ---------- 4. UI ----------
st.set_page_config(page_title="Study Planner", page_icon="📚")
st.title("📚 Study Planner")

if "subjects" not in st.session_state:
    st.session_state.subjects = load_subjects()
subjects = st.session_state.subjects

# Sidebar: add a subject
with st.sidebar:
    st.header("Add subject")
    name = st.text_input("Subject name")
    exam = st.date_input("Exam date", min_value=date.today())
    diff = st.slider("Difficulty", 1, 5, 3)
    topics_text = st.text_area("Topics (one per line)")
    if st.button("Add"):
        if not name.strip():
            st.error("Please enter a subject name.")
        else:
            topics = [t.strip() for t in topics_text.splitlines() if t.strip()]
            subjects.append(Subject(name.strip(), exam, diff, topics))
            save_subjects(subjects)
            st.rerun()

if not subjects:
    st.info("Add your first subject from the sidebar.")
    st.stop()

# Countdown
st.subheader("⏳ Exam countdown")
for s in sorted(subjects, key=lambda x: x.exam_date):
    c1, c2 = st.columns([3, 1])
    c1.write(f"**{s.name}**  ·  {s.exam_date:%d %b %Y}")
    c2.metric("Days left", s.days_left())

# Today's timetable
st.subheader("🗓️ Today's plan")
hours = st.slider("Study hours available today", 1, 10, 4)
table = make_timetable(subjects, hours)
if table:
    st.table(pd.DataFrame(table))
else:
    st.write("No upcoming exams.")

# Progress tracking
st.subheader("✅ Progress")
for s in subjects:
    with st.expander(f"{s.name}  ({s.progress():.0%} done)"):
        st.progress(s.progress())
        for t in s.topics:
            checked = st.checkbox(t, value=t in s.done, key=f"{s.name}-{t}")
            if checked and t not in s.done:
                s.done.append(t)
                save_subjects(subjects)
                st.rerun()
            elif not checked and t in s.done:
                s.done.remove(t)
                save_subjects(subjects)
                st.rerun()
        if st.button("Delete subject", key=f"del-{s.name}"):
            subjects.remove(s)
            save_subjects(subjects)
            st.rerun()

# Chart
st.subheader("📊 Progress chart")
st.bar_chart(pd.DataFrame({"Progress %": [s.progress() * 100 for s in subjects]},
                          index=[s.name for s in subjects]))
