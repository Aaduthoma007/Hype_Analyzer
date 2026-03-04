"""
Movie Buzz Analyzer — Database Helper
Handles SQLite initialization, reads, and writes.
"""
import sqlite3
import os
import json
from datetime import datetime

import config


def _get_schema_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection(db_path=None):
    """Get a SQLite connection with row_factory enabled."""
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path=None):
    """Create tables from schema.sql if they don't exist."""
    conn = get_connection(db_path)
    with open(_get_schema_path(), "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


# ── Movies ────────────────────────────────────────────────

def insert_movie(title, trailer_url=None, db_path=None):
    """Insert a movie and return its movie_id."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO movies (title, trailer_url) VALUES (?, ?)",
        (title, trailer_url)
    )
    movie_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return movie_id


def get_movie(movie_id, db_path=None):
    """Get a single movie by ID."""
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM movies WHERE movie_id = ?", (movie_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_movies(db_path=None):
    """Get all movies."""
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM movies ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Comments ──────────────────────────────────────────────

def insert_comments(movie_id, comments, db_path=None):
    """
    Bulk-insert comments.
    Each comment: {author, raw_text, cleaned_text, sentiment_score, sentiment_label, source, like_count, published_at}
    """
    conn = get_connection(db_path)
    conn.executemany(
        """INSERT INTO comments
           (movie_id, author, raw_text, cleaned_text, sentiment_score, sentiment_label, source, like_count, published_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                movie_id,
                c.get("author", ""),
                c["raw_text"],
                c.get("cleaned_text", ""),
                c.get("sentiment_score"),
                c.get("sentiment_label"),
                c.get("source", "youtube"),
                c.get("like_count", 0),
                c.get("published_at", ""),
            )
            for c in comments
        ],
    )
    conn.commit()
    conn.close()


def get_comments(movie_id, limit=100, offset=0, db_path=None):
    """Get paginated comments for a movie."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM comments WHERE movie_id = ? ORDER BY published_at DESC LIMIT ? OFFSET ?",
        (movie_id, limit, offset),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM comments WHERE movie_id = ?", (movie_id,)
    ).fetchone()["cnt"]
    conn.close()
    return {"comments": [dict(r) for r in rows], "total": total}


# ── Buzz Scores ───────────────────────────────────────────

def insert_buzz_score(movie_id, data, db_path=None):
    """
    Insert a buzz score record.
    data: {score, sentiment_avg, mention_volume, growth_rate, engagement,
           total_comments, high_hype_pct, neutral_pct, negative_pct}
    """
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO buzz_scores
           (movie_id, score, sentiment_avg, mention_volume, growth_rate, engagement,
            total_comments, high_hype_pct, neutral_pct, negative_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            movie_id,
            data["score"],
            data.get("sentiment_avg", 0),
            data.get("mention_volume", 0),
            data.get("growth_rate", 0),
            data.get("engagement", 0),
            data.get("total_comments", 0),
            data.get("high_hype_pct", 0),
            data.get("neutral_pct", 0),
            data.get("negative_pct", 0),
        ),
    )
    conn.commit()
    conn.close()


def get_buzz_scores(movie_id, db_path=None):
    """Get all buzz scores for a movie, newest first."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM buzz_scores WHERE movie_id = ? ORDER BY calculated_at DESC",
        (movie_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_leaderboard(db_path=None):
    """Get the latest buzz score for every movie, ranked highest first."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT m.movie_id, m.title, m.trailer_url, b.score, b.sentiment_avg,
                  b.mention_volume, b.growth_rate, b.engagement,
                  b.total_comments, b.high_hype_pct, b.neutral_pct, b.negative_pct,
                  b.calculated_at
           FROM movies m
           JOIN buzz_scores b ON m.movie_id = b.movie_id
           WHERE b.id = (SELECT MAX(id) FROM buzz_scores WHERE movie_id = m.movie_id)
           ORDER BY b.score DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
