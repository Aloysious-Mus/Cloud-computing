import os
import logging
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

# -----------------------------
# Configuration
# -----------------------------
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

database_url = os.getenv("DATABASE_URL", "sqlite:///timetable.db")

# Railway/Postgres compatibility fix
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# -----------------------------
# Database Model
# -----------------------------
class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"

    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(120), nullable=False)
    lecturer = db.Column(db.String(120), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "course_name": self.course_name,
            "lecturer": self.lecturer,
            "room": self.room,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# Create tables on startup
with app.app_context():
    db.create_all()

# -----------------------------
# Helpers
# -----------------------------
DAY_ORDER = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
    "Sunday": 7
}

def sorted_entries():
    entries = TimetableEntry.query.all()
    return sorted(entries, key=lambda e: (DAY_ORDER.get(e.day_of_week, 99), e.start_time))

# -----------------------------
# HTML Template
# -----------------------------
PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timetable App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #eef2ff, #ecfeff);
            margin: 0;
            padding: 0;
            color: #1e293b;
        }
        .container {
            width: 92%;
            max-width: 1100px;
            margin: 30px auto;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 22px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.10);
            border-top: 5px solid #4f46e5;
        }
        h1, h2 {
            margin-top: 0;
            color: #1e1b4b;
        }
        .subtitle {
            color: #475569;
            margin-bottom: 20px;
        }
        form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }
        input, select, button {
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            font-size: 14px;
        }
        input, select {
            background: #f8fafc;
            color: #0f172a;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
        }
        button {
            background: #4f46e5;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }
        button:hover {
            background: #4338ca;
        }
        .danger {
            background: #ef4444;
        }
        .danger:hover {
            background: #dc2626;
        }
        .edit-link {
            display: inline-block;
            padding: 10px 14px;
            border-radius: 8px;
            background: #14b8a6;
            color: white;
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
        }
        .edit-link:hover {
            background: #0f766e;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            overflow: hidden;
            border-radius: 10px;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            text-align: left;
            font-size: 14px;
        }
        th {
            background: #4f46e5;
            color: white;
        }
        tbody tr:nth-child(even) {
            background: #f8fafc;
        }
        tbody tr:hover {
            background: #e0f2fe;
        }
        .actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }
        .flash {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            background: #dbeafe;
            color: #1d4ed8;
            border-left: 5px solid #2563eb;
        }
        .top-links {
            margin-bottom: 15px;
        }
        .top-links a {
            margin-right: 10px;
            color: #4f46e5;
            text-decoration: none;
            font-weight: 600;
        }
        .top-links a:hover {
            color: #0f766e;
            text-decoration: underline;
        }
        .small {
            color: #64748b;
            font-size: 13px;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h1>University Timetable App</h1>
        <p class="subtitle">A simple Flask + SQLAlchemy timetable manager ready for Railway deployment.</p>

        <div class="top-links">
            <a href="{{ url_for('home') }}">Home</a>
            <a href="{{ url_for('health') }}">Health Check</a>
            <a href="{{ url_for('api_list_entries') }}">API: View JSON</a>
            <a href="{{ url_for('seed_data') }}">Seed Sample Data</a>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    </div>

    <div class="card">
        <h2>{% if edit_entry %}Edit Timetable Entry{% else %}Add Timetable Entry{% endif %}</h2>

        <form method="POST" action="{% if edit_entry %}{{ url_for('update_entry', entry_id=edit_entry.id) }}{% else %}{{ url_for('create_entry') }}{% endif %}">
            <input type="text" name="course_name" placeholder="Course Name" required value="{{ edit_entry.course_name if edit_entry else '' }}">
            <input type="text" name="lecturer" placeholder="Lecturer" required value="{{ edit_entry.lecturer if edit_entry else '' }}">
            <input type="text" name="room" placeholder="Room" required value="{{ edit_entry.room if edit_entry else '' }}">

            <select name="day_of_week" required>
                {% for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'] %}
                    <option value="{{ day }}" {% if edit_entry and edit_entry.day_of_week == day %}selected{% endif %}>{{ day }}</option>
                {% endfor %}
            </select>

            <input type="time" name="start_time" required value="{{ edit_entry.start_time if edit_entry else '' }}">
            <input type="time" name="end_time" required value="{{ edit_entry.end_time if edit_entry else '' }}">

            <button type="submit">{% if edit_entry %}Update Entry{% else %}Add Entry{% endif %}</button>
        </form>
    </div>

    <div class="card">
        <h2>Current Timetable</h2>
        <p class="small">Sorted by day and start time.</p>

        {% if entries %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Course</th>
                    <th>Lecturer</th>
                    <th>Room</th>
                    <th>Day</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for entry in entries %}
                <tr>
                    <td>{{ entry.id }}</td>
                    <td>{{ entry.course_name }}</td>
                    <td>{{ entry.lecturer }}</td>
                    <td>{{ entry.room }}</td>
                    <td>{{ entry.day_of_week }}</td>
                    <td>{{ entry.start_time }}</td>
                    <td>{{ entry.end_time }}</td>
                    <td class="actions">
                        <a href="{{ url_for('edit_entry_page', entry_id=entry.id) }}" class="edit-link">Edit</a>
                        <form method="POST" action="{{ url_for('delete_entry', entry_id=entry.id) }}" style="display:inline;">
                            <button type="submit" class="danger" onclick="return confirm('Delete this entry?')">Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
            <p>No timetable entries yet.</p>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

# -----------------------------
# Web Routes
# -----------------------------
@app.route("/")
def home():
    app.logger.info("Homepage loaded successfully.")
    entries = sorted_entries()
    return render_template_string(PAGE_TEMPLATE, entries=entries, edit_entry=None)

@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/create", methods=["POST"])
def create_entry():
    try:
        entry = TimetableEntry(
            course_name=request.form["course_name"],
            lecturer=request.form["lecturer"],
            room=request.form["room"],
            day_of_week=request.form["day_of_week"],
            start_time=request.form["start_time"],
            end_time=request.form["end_time"]
        )
        db.session.add(entry)
        db.session.commit()
        app.logger.info(f"Created timetable entry: {entry.course_name}")
        flash("Timetable entry added successfully.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating entry: {str(e)}")
        flash(f"Error creating entry: {str(e)}")
    return redirect(url_for("home"))

@app.route("/edit/<int:entry_id>")
def edit_entry_page(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)

    if not entry:
        flash(f"Entry with ID {entry_id} was not found.")
        return redirect(url_for("home"))

    entries = sorted_entries()
    return render_template_string(PAGE_TEMPLATE, entries=entries, edit_entry=entry)

@app.route("/update/<int:entry_id>", methods=["POST"])
def update_entry(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)

    if not entry:
        flash(f"Entry with ID {entry_id} was not found.")
        return redirect(url_for("home"))

    try:
        entry.course_name = request.form["course_name"]
        entry.lecturer = request.form["lecturer"]
        entry.room = request.form["room"]
        entry.day_of_week = request.form["day_of_week"]
        entry.start_time = request.form["start_time"]
        entry.end_time = request.form["end_time"]
        db.session.commit()
        app.logger.info(f"Updated timetable entry ID {entry_id}")
        flash("Timetable entry updated successfully.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating entry: {str(e)}")
        flash(f"Error updating entry: {str(e)}")
    return redirect(url_for("home"))

@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete_entry(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)

    if not entry:
        flash(f"Entry with ID {entry_id} was not found.")
        return redirect(url_for("home"))

    try:
        db.session.delete(entry)
        db.session.commit()
        app.logger.info(f"Deleted timetable entry ID {entry_id}")
        flash("Timetable entry deleted successfully.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting entry: {str(e)}")
        flash(f"Error deleting entry: {str(e)}")
    return redirect(url_for("home"))

@app.route("/seed")
def seed_data():
    if TimetableEntry.query.count() == 0:
        sample_entries = [
            TimetableEntry(course_name="Software Architecture", lecturer="Dr. Kato", room="B201", day_of_week="Monday", start_time="08:00", end_time="10:00"),
            TimetableEntry(course_name="Cloud Computing", lecturer="Ms. Amina", room="Lab 3", day_of_week="Tuesday", start_time="10:00", end_time="12:00"),
            TimetableEntry(course_name="Database Systems", lecturer="Mr. Brian", room="C102", day_of_week="Wednesday", start_time="14:00", end_time="16:00"),
            TimetableEntry(course_name="Web Development", lecturer="Dr. Susan", room="A110", day_of_week="Thursday", start_time="09:00", end_time="11:00")
        ]
        db.session.add_all(sample_entries)
        db.session.commit()
        app.logger.info("Inserted sample timetable data.")
        flash("Sample timetable data inserted.")
    else:
        flash("Sample data already exists.")
    return redirect(url_for("home"))

# -----------------------------
# JSON API Routes
# -----------------------------
@app.route("/api/timetable", methods=["GET"])
def api_list_entries():
    entries = sorted_entries()
    return jsonify([entry.to_dict() for entry in entries]), 200

@app.route("/api/timetable/<int:entry_id>", methods=["GET"])
def api_get_entry(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)
    if not entry:
        return jsonify({"error": "Resource not found"}), 404
    return jsonify(entry.to_dict()), 200

@app.route("/api/timetable", methods=["POST"])
def api_create_entry():
    data = request.get_json() or {}

    required_fields = ["course_name", "lecturer", "room", "day_of_week", "start_time", "end_time"]
    missing = [field for field in required_fields if field not in data]

    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        entry = TimetableEntry(
            course_name=data["course_name"],
            lecturer=data["lecturer"],
            room=data["room"],
            day_of_week=data["day_of_week"],
            start_time=data["start_time"],
            end_time=data["end_time"]
        )
        db.session.add(entry)
        db.session.commit()
        app.logger.info(f"API created entry: {entry.course_name}")
        return jsonify(entry.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"API create error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/timetable/<int:entry_id>", methods=["PUT"])
def api_update_entry(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)

    if not entry:
        return jsonify({"error": "Resource not found"}), 404

    data = request.get_json() or {}

    try:
        entry.course_name = data.get("course_name", entry.course_name)
        entry.lecturer = data.get("lecturer", entry.lecturer)
        entry.room = data.get("room", entry.room)
        entry.day_of_week = data.get("day_of_week", entry.day_of_week)
        entry.start_time = data.get("start_time", entry.start_time)
        entry.end_time = data.get("end_time", entry.end_time)

        db.session.commit()
        app.logger.info(f"API updated entry ID {entry_id}")
        return jsonify(entry.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"API update error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/timetable/<int:entry_id>", methods=["DELETE"])
def api_delete_entry(entry_id):
    entry = db.session.get(TimetableEntry, entry_id)

    if not entry:
        return jsonify({"error": "Resource not found"}), 404

    try:
        db.session.delete(entry)
        db.session.commit()
        app.logger.info(f"API deleted entry ID {entry_id}")
        return jsonify({"message": "Entry deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"API delete error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Error Handlers
# -----------------------------
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found"}), 404

    flash("Page not found.")
    return redirect(url_for("home"))

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500

    flash("An internal server error occurred.")
    return redirect(url_for("home"))

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)