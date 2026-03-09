import importlib

import pytest


@pytest.fixture
def app_module(monkeypatch):
    app = importlib.import_module("app")

    monkeypatch.setattr(app.db, "init_db", lambda: None)
    monkeypatch.setattr(app.db, "get_comments", lambda movie_id, limit, offset: {
        "comments": [], "total": 0, "movie_id": movie_id, "limit": limit, "offset": offset
    })
    monkeypatch.setattr(app.db, "get_movie", lambda movie_id: {"movie_id": movie_id, "title": "X"})
    monkeypatch.setattr(app.db, "get_buzz_scores", lambda movie_id: [])
    monkeypatch.setattr(app.db, "get_leaderboard", lambda: [])
    monkeypatch.setattr(app.db, "get_all_movies", lambda: [])

    app.app.config["TESTING"] = True
    return app


def test_comments_limit_validation(app_module):
    client = app_module.app.test_client()

    resp = client.get("/api/comments?movie_id=1&limit=1000")
    assert resp.status_code == 400
    assert "limit must be between" in resp.get_json()["error"]


def test_comments_offset_validation(app_module):
    client = app_module.app.test_client()

    resp = client.get("/api/comments?movie_id=1&offset=-1")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "offset must be >= 0"


def test_task_status_endpoint_not_found(app_module):
    client = app_module.app.test_client()

    resp = client.get("/api/status/does-not-exist")
    assert resp.status_code == 404


def test_run_returns_task_id_and_status_endpoint(monkeypatch, app_module):
    client = app_module.app.test_client()

    def fake_run_agent(movie_title, video_id, auto_approve, progress_callback):
        progress_callback(42, "Working")
        return {"score": 77.7}

    class ImmediateThread:
        def __init__(self, target, daemon):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(app_module, "run_agent", fake_run_agent)
    monkeypatch.setattr(app_module.threading, "Thread", ImmediateThread)

    run_resp = client.post("/api/run", json={"movie_title": "Test Movie", "video_id": "abc123"})
    assert run_resp.status_code == 202
    task_id = run_resp.get_json()["task_id"]

    status_resp = client.get(f"/api/status/{task_id}")
    assert status_resp.status_code == 200
    payload = status_resp.get_json()["task"]
    assert payload["status"] == "completed"
    assert payload["progress"] == 100
    assert payload["message"] == "Analysis complete."
