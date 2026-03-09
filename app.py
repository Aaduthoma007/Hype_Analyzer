"""
Movie Buzz Analyzer — Flask Backend
Serves the API endpoints and the dashboard frontend.
"""
import threading
from uuid import uuid4
from flask import Flask, render_template, jsonify, request

import config
from database import db
from agent import run_agent

app = Flask(__name__)

# Track running agent tasks
_agent_tasks = {}
_agent_tasks_lock = threading.Lock()
MAX_PAGE_SIZE = 200


# ── Initialize DB on startup ────────────────────────────

@app.before_request
def _init():
    """Ensure DB is initialized before first request."""
    if not hasattr(app, '_db_initialized'):
        db.init_db()
        app._db_initialized = True


# ── Dashboard Route ──────────────────────────────────────

@app.route("/")
def dashboard():
    """Serve the main dashboard page."""
    return render_template("dashboard.html")


# ── API Routes ───────────────────────────────────────────

@app.route("/api/buzz")
def api_buzz():
    """Get Buzz Score breakdown for a specific movie."""
    movie_id = request.args.get("movie_id", type=int)
    if not movie_id:
        return jsonify({"error": "movie_id parameter required"}), 400

    scores = db.get_buzz_scores(movie_id)
    movie = db.get_movie(movie_id)

    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    return jsonify({
        "movie": movie,
        "buzz_scores": scores,
        "latest": scores[0] if scores else None,
    })


@app.route("/api/comments")
def api_comments():
    """Get paginated comments for a movie with sentiment data."""
    movie_id = request.args.get("movie_id", type=int)
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    if not movie_id:
        return jsonify({"error": "movie_id parameter required"}), 400

    if limit < 1 or limit > MAX_PAGE_SIZE:
        return jsonify({"error": f"limit must be between 1 and {MAX_PAGE_SIZE}"}), 400

    if offset < 0:
        return jsonify({"error": "offset must be >= 0"}), 400

    result = db.get_comments(movie_id, limit=limit, offset=offset)
    return jsonify(result)


@app.route("/api/leaderboard")
def api_leaderboard():
    """Get all movies ranked by Buzz Score (highest first)."""
    leaderboard = db.get_leaderboard()
    return jsonify({"leaderboard": leaderboard})


@app.route("/api/movies")
def api_movies():
    """Get all analyzed movies."""
    movies = db.get_all_movies()
    return jsonify({"movies": movies})


@app.route("/api/run", methods=["POST"])
def api_run():
    """
    Trigger an agent run for a new movie.
    Body: {"movie_title": "...", "video_id": "..."}
    Runs the agent in auto-approve mode (for API-triggered runs).
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    movie_title = (data.get("movie_title") or "").strip()
    video_id = data.get("video_id", "auto")

    if not movie_title:
        return jsonify({"error": "movie_title is required"}), 400

    # Run agent in background thread
    task_id = f"{movie_title}_{video_id}"

    if task_id in _agent_tasks and _agent_tasks[task_id].get("status") == "running":
        return jsonify({"error": "Analysis already in progress for this movie"}), 409

    with _agent_tasks_lock:
        _agent_tasks[task_id] = {
            "status": "running",
            "movie_title": movie_title,
            "progress": 0,
            "message": "Initializing Project Mayhem...",
        }

    def _progress_callback(pct, msg):
        with _agent_tasks_lock:
            if task_id in _agent_tasks:
                _agent_tasks[task_id]["progress"] = pct
                _agent_tasks[task_id]["message"] = msg

    def _run():
        try:
            result = run_agent(
                movie_title, 
                video_id, 
                auto_approve=True, 
                progress_callback=_progress_callback
            )
            with _agent_tasks_lock:
                _agent_tasks[task_id] = {
                    "status": "completed",
                    "movie_title": movie_title,
                    "result": result,
                    "progress": 100,
                    "message": "Analysis complete.",
                }
        except Exception as e:
            with _agent_tasks_lock:
                _agent_tasks[task_id] = {
                    "status": "failed",
                    "movie_title": movie_title,
                    "progress": 100,
                    "message": "Analysis failed.",
                    "error": str(e),
                }

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({
        "message": "Agent run started",
        "task_id": task_id,
        "status": "running",
    }), 202


@app.route("/api/status")
def api_status():
    """Get status of running agent tasks."""
    with _agent_tasks_lock:
        return jsonify({"tasks": _agent_tasks})


@app.route("/api/status/<task_id>")
def api_status_task(task_id):
    """Get status for a specific agent task."""
    with _agent_tasks_lock:
        task = _agent_tasks.get(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({"task": task, "task_id": task_id})


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
