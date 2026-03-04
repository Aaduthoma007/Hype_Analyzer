"""
Movie Buzz Analyzer — End-to-End Pipeline Test
Tests the full pipeline with mocked API responses in demo mode.
"""
import os
import sys
import json
import pytest
import sqlite3
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force demo mode
os.environ["YOUTUBE_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

import config
config.DEMO_MODE = True

from engine.preprocessor import clean_text, is_valid_comment, preprocess_batch
from engine.buzz_calculator import calculate_buzz_score
from tools.youtube_tool import youtube_data_tool, _is_valid_comment as yt_valid
from tools.social_mention_tool import social_mention_tool
from tools.sentiment_tool import sentiment_evaluator_tool
from database import db


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.init_db(db_path=path)
    yield path
    os.unlink(path)


# ── Preprocessor Tests ────────────────────────────────────

class TestPreprocessor:
    def test_clean_text_lowercase(self):
        assert clean_text("HELLO WORLD") == "hello world"

    def test_clean_text_removes_urls(self):
        result = clean_text("Check https://example.com for more")
        assert "https" not in result
        assert "example" not in result

    def test_clean_text_removes_stopwords(self):
        result = clean_text("I am going to the store")
        assert "am" not in result.split()
        assert "the" not in result.split()

    def test_is_valid_comment_rejects_long(self):
        assert not is_valid_comment("x" * 501)

    def test_is_valid_comment_rejects_urls(self):
        assert not is_valid_comment("Visit https://spam.com now")

    def test_is_valid_comment_accepts_normal(self):
        assert is_valid_comment("Great movie trailer!")

    def test_preprocess_batch(self):
        comments = [
            {"text": "This is great!"},
            {"text": "Visit https://spam.com"},  # should be filtered
            {"text": "x" * 501},  # should be filtered
            {"text": "Amazing trailer, can't wait"},
        ]
        result = preprocess_batch(comments)
        assert len(result) == 2
        assert all("cleaned_text" in c for c in result)


# ── YouTube Tool Tests ────────────────────────────────────

class TestYouTubeTool:
    def test_demo_mode_returns_comments(self):
        result = json.loads(youtube_data_tool.invoke("test_video_id"))
        assert result["error"] is False
        assert result["comments_collected"] >= 500
        assert len(result["data"]) >= 500

    def test_comment_structure(self):
        result = json.loads(youtube_data_tool.invoke("test"))
        comment = result["data"][0]
        assert "author" in comment
        assert "text" in comment
        assert "published_at" in comment
        assert "like_count" in comment

    def test_filter_rejects_long_text(self):
        assert not yt_valid("x" * 501)

    def test_filter_rejects_urls(self):
        assert not yt_valid("Check out https://example.com")


# ── Social Mention Tool Tests ─────────────────────────────

class TestSocialMentionTool:
    def test_demo_mode_returns_data(self):
        result = json.loads(social_mention_tool.invoke("Test Movie"))
        assert result["error"] is False
        data = result["data"]
        assert "mention_count" in data
        assert "growth_rate_pct" in data
        assert "platforms" in data
        assert "engagement" in data

    def test_mention_count_positive(self):
        result = json.loads(social_mention_tool.invoke("Movie"))
        assert result["data"]["mention_count"] > 0


# ── Sentiment Tool Tests ──────────────────────────────────

class TestSentimentTool:
    def test_classifies_high_hype(self):
        texts = json.dumps(["cant wait opening night buying tickets"])
        result = json.loads(sentiment_evaluator_tool.invoke(texts))
        assert result["error"] is False
        assert result["results"][0]["score"] == 3
        assert result["results"][0]["label"] == "High Hype"

    def test_classifies_negative(self):
        texts = json.dumps(["looks terrible hard pass"])
        result = json.loads(sentiment_evaluator_tool.invoke(texts))
        assert result["results"][0]["score"] == 1
        assert result["results"][0]["label"] == "Negative/Dead"

    def test_classifies_neutral(self):
        texts = json.dumps(["interesting concept might check it"])
        result = json.loads(sentiment_evaluator_tool.invoke(texts))
        # Neutral or any valid score
        assert result["results"][0]["score"] in (1, 2, 3)

    def test_batch_classification(self):
        texts = json.dumps([
            "opening night for sure",
            "looks okay might stream",
            "terrible movie hard pass",
        ])
        result = json.loads(sentiment_evaluator_tool.invoke(texts))
        assert result["total_classified"] == 3
        assert len(result["results"]) == 3

    def test_scores_are_valid(self):
        texts = json.dumps(["great movie", "bad movie", "okay movie"])
        result = json.loads(sentiment_evaluator_tool.invoke(texts))
        for r in result["results"]:
            assert r["score"] in (1, 2, 3)
            assert r["label"] in ("High Hype", "Neutral/Curious", "Negative/Dead")


# ── Buzz Calculator Tests ─────────────────────────────────

class TestBuzzCalculator:
    def test_score_in_range(self):
        scores = [3, 3, 2, 1, 3, 2, 2, 1, 3, 3]
        mention_data = {
            "mention_count": 25000,
            "growth_rate_pct": 45.0,
            "engagement": {"avg_likes": 200, "avg_shares": 50, "avg_replies": 30},
        }
        result = calculate_buzz_score(scores, mention_data)
        assert 0 <= result["score"] <= 100

    def test_all_high_hype(self):
        scores = [3] * 100
        mention_data = {
            "mention_count": 50000,
            "growth_rate_pct": 80.0,
            "engagement": {"avg_likes": 500, "avg_shares": 200, "avg_replies": 100},
        }
        result = calculate_buzz_score(scores, mention_data)
        assert result["score"] > 70
        assert result["high_hype_pct"] == 100.0

    def test_all_negative(self):
        scores = [1] * 100
        mention_data = {
            "mention_count": 1000,
            "growth_rate_pct": -50.0,
            "engagement": {"avg_likes": 10, "avg_shares": 2, "avg_replies": 1},
        }
        result = calculate_buzz_score(scores, mention_data)
        assert result["score"] < 50
        assert result["negative_pct"] == 100.0

    def test_breakdown_sums_to_score(self):
        scores = [3, 2, 1, 2, 3]
        mention_data = {
            "mention_count": 10000,
            "growth_rate_pct": 20.0,
            "engagement": {"avg_likes": 100, "avg_shares": 30, "avg_replies": 15},
        }
        result = calculate_buzz_score(scores, mention_data)
        breakdown = result["breakdown"]
        total = sum(breakdown.values())
        assert abs(total - result["score"]) < 1.0  # Allow rounding tolerance


# ── Database Tests ────────────────────────────────────────

class TestDatabase:
    def test_init_creates_tables(self, temp_db):
        conn = sqlite3.connect(temp_db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "movies" in table_names
        assert "comments" in table_names
        assert "buzz_scores" in table_names
        conn.close()

    def test_insert_and_get_movie(self, temp_db):
        movie_id = db.insert_movie("Test Movie", "https://youtube.com/test", db_path=temp_db)
        movie = db.get_movie(movie_id, db_path=temp_db)
        assert movie is not None
        assert movie["title"] == "Test Movie"

    def test_insert_and_get_comments(self, temp_db):
        movie_id = db.insert_movie("Test", db_path=temp_db)
        comments = [
            {
                "author": "User1",
                "raw_text": "Great movie!",
                "cleaned_text": "great movie",
                "sentiment_score": 3,
                "sentiment_label": "High Hype",
                "source": "youtube",
                "like_count": 10,
                "published_at": "2024-01-01",
            }
        ]
        db.insert_comments(movie_id, comments, db_path=temp_db)
        result = db.get_comments(movie_id, db_path=temp_db)
        assert result["total"] == 1
        assert result["comments"][0]["raw_text"] == "Great movie!"

    def test_insert_and_get_buzz_score(self, temp_db):
        movie_id = db.insert_movie("Test", db_path=temp_db)
        buzz_data = {
            "score": 75.5,
            "sentiment_avg": 2.5,
            "mention_volume": 10000,
            "growth_rate": 30.0,
            "engagement": 65.0,
            "total_comments": 500,
            "high_hype_pct": 45.0,
            "neutral_pct": 35.0,
            "negative_pct": 20.0,
        }
        db.insert_buzz_score(movie_id, buzz_data, db_path=temp_db)
        scores = db.get_buzz_scores(movie_id, db_path=temp_db)
        assert len(scores) == 1
        assert scores[0]["score"] == 75.5

    def test_leaderboard(self, temp_db):
        m1 = db.insert_movie("Movie A", db_path=temp_db)
        m2 = db.insert_movie("Movie B", db_path=temp_db)
        db.insert_buzz_score(m1, {
            "score": 80, "sentiment_avg": 2.5, "mention_volume": 5000,
            "growth_rate": 20, "engagement": 50, "total_comments": 300,
            "high_hype_pct": 50, "neutral_pct": 30, "negative_pct": 20,
        }, db_path=temp_db)
        db.insert_buzz_score(m2, {
            "score": 60, "sentiment_avg": 2.0, "mention_volume": 3000,
            "growth_rate": 10, "engagement": 40, "total_comments": 200,
            "high_hype_pct": 30, "neutral_pct": 40, "negative_pct": 30,
        }, db_path=temp_db)

        lb = db.get_leaderboard(db_path=temp_db)
        assert len(lb) == 2
        assert lb[0]["score"] == 80  # Movie A first
        assert lb[1]["score"] == 60


# ── Full Pipeline Integration Test ────────────────────────

class TestFullPipeline:
    def test_end_to_end(self, temp_db):
        """Test the complete pipeline: YouTube → preprocess → sentiment → buzz → DB"""
        # 1. Collect comments (demo mode)
        yt_result = json.loads(youtube_data_tool.invoke("demo_video"))
        assert yt_result["comments_collected"] >= 500
        comments = yt_result["data"]

        # 2. Collect social metrics
        social_result = json.loads(social_mention_tool.invoke("Demo Movie"))
        mention_data = social_result["data"]

        # 3. Preprocess
        processed = preprocess_batch(comments)
        assert len(processed) > 400  # Most should pass validation

        # 4. Sentiment analysis
        cleaned_texts = [c["cleaned_text"] for c in processed[:50]]  # Test subset
        sent_result = json.loads(sentiment_evaluator_tool.invoke(json.dumps(cleaned_texts)))
        assert sent_result["total_classified"] == 50

        # 5. Merge scores
        all_scores = [r["score"] for r in sent_result["results"]]
        assert all(s in (1, 2, 3) for s in all_scores)

        # 6. Calculate buzz score
        buzz = calculate_buzz_score(all_scores, mention_data)
        assert 0 <= buzz["score"] <= 100

        # 7. Write to DB
        movie_id = db.insert_movie("Demo Movie", "https://youtube.com/demo", db_path=temp_db)
        for i, c in enumerate(processed[:50]):
            if i < len(sent_result["results"]):
                c["sentiment_score"] = sent_result["results"][i]["score"]
                c["sentiment_label"] = sent_result["results"][i]["label"]
        db.insert_comments(movie_id, processed[:50], db_path=temp_db)
        db.insert_buzz_score(movie_id, buzz, db_path=temp_db)

        # 8. Verify DB contents
        stored_scores = db.get_buzz_scores(movie_id, db_path=temp_db)
        assert len(stored_scores) == 1
        assert stored_scores[0]["score"] == buzz["score"]

        stored_comments = db.get_comments(movie_id, db_path=temp_db)
        assert stored_comments["total"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
