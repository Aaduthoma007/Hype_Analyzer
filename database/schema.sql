-- Movie Buzz Analyzer — SQLite Schema

CREATE TABLE IF NOT EXISTS movies (
    movie_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    trailer_url TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id        INTEGER NOT NULL,
    author          TEXT,
    raw_text        TEXT    NOT NULL,
    cleaned_text    TEXT,
    sentiment_score INTEGER CHECK (sentiment_score IN (1, 2, 3)),
    sentiment_label TEXT    CHECK (sentiment_label IN ('High Hype', 'Neutral/Curious', 'Negative/Dead')),
    source          TEXT    DEFAULT 'youtube',
    like_count      INTEGER DEFAULT 0,
    published_at    TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE IF NOT EXISTS buzz_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id        INTEGER NOT NULL,
    score           REAL    NOT NULL CHECK (score >= 0 AND score <= 100),
    sentiment_avg   REAL,
    mention_volume  INTEGER,
    growth_rate     REAL,
    engagement      REAL,
    total_comments  INTEGER,
    high_hype_pct   REAL,
    neutral_pct     REAL,
    negative_pct    REAL,
    calculated_at   TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE INDEX IF NOT EXISTS idx_comments_movie ON comments(movie_id);
CREATE INDEX IF NOT EXISTS idx_buzz_movie ON buzz_scores(movie_id);
