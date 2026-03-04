"""
Movie Buzz Analyzer — Central Configuration
"""
import os

# ── API Keys ──────────────────────────────────────────────
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Auto-enable demo mode when keys are missing
DEMO_MODE = not YOUTUBE_API_KEY or not GEMINI_API_KEY

# ── Gemini Model ──────────────────────────────────────────
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# ── Buzz Score Weights (must sum to 1.0) ──────────────────
W_SENTIMENT = 0.35
W_VOLUME = 0.25
W_GROWTH = 0.20
W_ENGAGEMENT = 0.20

# ── Data Constraints ─────────────────────────────────────
MIN_COMMENTS = 500
MAX_COMMENT_LENGTH = 500
SENTIMENT_BATCH_SIZE = 25  # comments per LLM call

# ── Database ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "buzz_analyzer.db")

# ── Flask ─────────────────────────────────────────────────
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
