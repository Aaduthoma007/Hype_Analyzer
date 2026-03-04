"""
DB Commit Tool — LangChain tool for writing structured data to SQLite.
Validates data schema before writing. Supports HITL checkpoint.
"""
import json
from langchain_core.tools import tool

from database import db


@tool
def db_commit_tool(payload_json: str) -> str:
    """
    Write the final structured analysis data to the SQLite database.
    
    IMPORTANT: Before calling this tool, the agent MUST present a data summary
    to the user and receive explicit approval (Human-in-the-Loop checkpoint).
    
    Input: A JSON string with the following structure:
    {
        "movie_title": "Movie Name",
        "trailer_url": "https://youtube.com/watch?v=...",
        "comments": [
            {
                "author": "...",
                "raw_text": "...",
                "cleaned_text": "...",
                "sentiment_score": 1|2|3,
                "sentiment_label": "High Hype|Neutral/Curious|Negative/Dead",
                "source": "youtube",
                "like_count": 0,
                "published_at": "..."
            }
        ],
        "buzz_score": {
            "score": 0-100,
            "sentiment_avg": ...,
            "mention_volume": ...,
            "growth_rate": ...,
            "engagement": ...,
            "total_comments": ...,
            "high_hype_pct": ...,
            "neutral_pct": ...,
            "negative_pct": ...
        }
    }
    
    Returns confirmation with movie_id and row counts.
    """
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return json.dumps({"error": True, "message": "Invalid JSON payload"})

    # Validate required fields
    required = ["movie_title", "comments", "buzz_score"]
    for field in required:
        if field not in payload:
            return json.dumps({"error": True, "message": f"Missing required field: {field}"})

    buzz = payload["buzz_score"]
    if not isinstance(buzz.get("score"), (int, float)):
        return json.dumps({"error": True, "message": "buzz_score.score must be a number"})

    try:
        # Initialize DB if needed
        db.init_db()

        # Insert movie
        movie_id = db.insert_movie(
            title=payload["movie_title"],
            trailer_url=payload.get("trailer_url", ""),
        )

        # Insert comments
        db.insert_comments(movie_id, payload["comments"])

        # Insert buzz score
        db.insert_buzz_score(movie_id, buzz)

        return json.dumps({
            "error": False,
            "message": "Data committed successfully",
            "movie_id": movie_id,
            "comments_written": len(payload["comments"]),
            "buzz_score": buzz["score"],
        })

    except Exception as e:
        return json.dumps({
            "error": True,
            "message": f"Database write failed: {str(e)}",
        })
