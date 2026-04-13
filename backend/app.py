from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os, functools

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "edutrack-secret-2024")
DB_PATH = os.environ.get("DB_PATH", "students.db")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "Titli")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                age        INTEGER NOT NULL,
                department TEXT    DEFAULT '',
                major      TEXT    DEFAULT '',
                minor      TEXT    DEFAULT '',
                attendance REAL    DEFAULT 0
            )
        """)
        for col, defn in [
            ("department", "TEXT DEFAULT ''"),
            ("major",      "TEXT DEFAULT ''"),
            ("minor",      "TEXT DEFAULT ''"),
            ("attendance", "REAL DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE students ADD COLUMN {col} {defn}")
            except Exception:
                pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS marks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject    TEXT    NOT NULL,
                score      REAL    NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        conn.commit()


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── AUTH ──────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USER and
                request.form.get("password") == ADMIN_PASS):
            session["admin"] = True
            return redirect(url_for("index"))
        flash("Invalid credentials. Please try again.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── DASHBOARD ─────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    with get_db() as conn:
        students = conn.execute(
            "SELECT id, name, age, department, attendance, major, minor FROM students ORDER BY id"
        ).fetchall()
    return render_template("index.html", students=students)


@app.route("/add", methods=["POST"])
@login_required
def add():
    name       = request.form.get("name",       "").strip()
    age        = request.form.get("age",        "").strip()
    department = request.form.get("department", "").strip()
    major      = request.form.get("major",      "").strip()
    minor      = request.form.get("minor",      "").strip()
    attendance = request.form.get("attendance", "0").strip()

    if not name or not age:
        flash("Name and age are required.", "error")
        return redirect(url_for("index"))
    try:
        age = int(age)
        if not (5 <= age <= 99):
            raise ValueError
    except ValueError:
        flash("Please enter a valid age between 5 and 99.", "error")
        return redirect(url_for("index"))

    try:
        attendance = float(attendance) if attendance else 0.0
        attendance = max(0.0, min(100.0, attendance))
    except ValueError:
        attendance = 0.0

    with get_db() as conn:
        conn.execute(
            "INSERT INTO students (name, age, department, major, minor, attendance) VALUES (?, ?, ?, ?, ?, ?)",
            (name, age, department, major, minor, attendance)
        )
        conn.commit()
    flash(f"✓ {name} enrolled successfully!", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:student_id>", methods=["POST"])
@login_required
def delete(student_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT name FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
            conn.execute("DELETE FROM marks WHERE student_id = ?", (student_id,))
            conn.commit()
            flash(f"✓ {row['name']} removed.", "success")
        else:
            flash("Student not found.", "error")
    return redirect(url_for("index"))


# ── EDIT STUDENT ───────────────────────────────────────────────
@app.route("/student/<int:student_id>")
@login_required
def edit_student(student_id):
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if not student:
            flash("Student not found.", "error")
            return redirect(url_for("index"))
        marks = conn.execute(
            "SELECT * FROM marks WHERE student_id = ? ORDER BY subject",
            (student_id,)
        ).fetchall()
    return render_template("edit.html", student=student, marks=marks)


@app.route("/student/<int:student_id>/update", methods=["POST"])
@login_required
def update_student(student_id):
    name       = request.form.get("name",       "").strip()
    age        = request.form.get("age",        "").strip()
    department = request.form.get("department", "").strip()
    major      = request.form.get("major",      "").strip()
    minor      = request.form.get("minor",      "").strip()
    attendance = request.form.get("attendance", "0").strip()

    if not name or not age:
        flash("Name and age are required.", "error")
        return redirect(url_for("edit_student", student_id=student_id))
    try:
        age        = int(age)
        attendance = float(attendance) if attendance else 0.0
        attendance = max(0.0, min(100.0, attendance))
    except ValueError:
        flash("Invalid age or attendance value.", "error")
        return redirect(url_for("edit_student", student_id=student_id))

    with get_db() as conn:
        conn.execute("""
            UPDATE students
               SET name=?, age=?, department=?, major=?, minor=?, attendance=?
             WHERE id=?
        """, (name, age, department, major, minor, attendance, student_id))
        conn.commit()
    flash("✓ Student updated successfully!", "success")
    return redirect(url_for("edit_student", student_id=student_id))


# ── MARKS ──────────────────────────────────────────────────────
@app.route("/student/<int:student_id>/marks/add", methods=["POST"])
@login_required
def add_mark(student_id):
    subject = request.form.get("subject", "").strip()
    score   = request.form.get("score",   "").strip()
    if not subject or not score:
        flash("Subject and score are required.", "error")
        return redirect(url_for("edit_student", student_id=student_id))
    try:
        score = float(score)
        if not (0 <= score <= 100):
            raise ValueError
    except ValueError:
        flash("Score must be between 0 and 100.", "error")
        return redirect(url_for("edit_student", student_id=student_id))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO marks (student_id, subject, score) VALUES (?, ?, ?)",
            (student_id, subject, score)
        )
        conn.commit()
    flash(f"✓ {subject} mark added.", "success")
    return redirect(url_for("edit_student", student_id=student_id))


@app.route("/student/<int:student_id>/marks/delete/<int:mark_id>", methods=["POST"])
@login_required
def delete_mark(student_id, mark_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM marks WHERE id = ? AND student_id = ?", (mark_id, student_id)
        )
        conn.commit()
    return redirect(url_for("edit_student", student_id=student_id))


# ── STUDENT CARD ───────────────────────────────────────────────
@app.route("/student/<int:student_id>/card")
@login_required
def student_card(student_id):
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if not student:
            return {"error": "Not found"}, 404
        marks = conn.execute(
            "SELECT * FROM marks WHERE student_id = ? ORDER BY subject",
            (student_id,)
        ).fetchall()
    return {
        "id":         student["id"],
        "name":       student["name"],
        "age":        student["age"],
        "department": student["department"] or "",
        "major":      student["major"] or "",
        "minor":      student["minor"] or "",
        "attendance": float(student["attendance"] or 0),
        "marks":      [{"subject": m["subject"], "score": float(m["score"]), "id": m["id"]} for m in marks]
    }


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)