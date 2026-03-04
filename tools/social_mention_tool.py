"""
Social Mention Tool — LangChain tool for keyword volume metrics.
Retrieves mention counts, growth rates, and platform breakdowns.
"""
import json
import random
import math
from datetime import datetime, timedelta
from langchain_core.tools import tool

import config


# ── Demo Data ─────────────────────────────────────────────

PLATFORMS = ["twitter", "reddit", "tiktok", "instagram", "facebook", "youtube"]

def _generate_demo_mentions(keyword):
    """Generate synthetic social mention data for demo mode."""
    base_volume = random.randint(5000, 50000)
    growth = round(random.uniform(-15.0, 85.0), 2)

    platform_breakdown = {}
    remaining = base_volume
    for i, platform in enumerate(PLATFORMS):
        if i == len(PLATFORMS) - 1:
            platform_breakdown[platform] = remaining
        else:
            share = random.randint(int(remaining * 0.05), int(remaining * 0.4))
            platform_breakdown[platform] = share
            remaining -= share

    # Generate time-series data (last 7 days)
    daily_mentions = []
    current = base_volume // 7
    for day in range(7):
        date = (datetime.now() - timedelta(days=6 - day)).strftime("%Y-%m-%d")
        variation = random.uniform(0.6, 1.5)
        count = int(current * variation)
        daily_mentions.append({"date": date, "count": count})
        current = count

    # Engagement metrics
    avg_likes = random.randint(50, 500)
    avg_shares = random.randint(10, 200)
    avg_replies = random.randint(5, 100)

    return {
        "keyword": keyword,
        "mention_count": base_volume,
        "growth_rate_pct": growth,
        "platforms": platform_breakdown,
        "daily_trend": daily_mentions,
        "engagement": {
            "avg_likes": avg_likes,
            "avg_shares": avg_shares,
            "avg_replies": avg_replies,
            "engagement_rate": round((avg_likes + avg_shares + avg_replies) / max(base_volume, 1) * 100, 4),
        },
        "period": "7d",
        "collected_at": datetime.now().isoformat(),
    }


def _fetch_social_mentions(keyword):
    """
    Fetch real social mention data.
    In production, this would query social listening APIs 
    (e.g., Brandwatch, Mention, or custom scrapers).
    """
    # Placeholder for real API integration
    # You would integrate with a real social listening platform here
    return _generate_demo_mentions(keyword)


@tool
def social_mention_tool(keyword: str) -> str:
    """
    Retrieve keyword volume metrics across social platforms for a movie title.
    Returns mention count, growth rate percentage, platform breakdown,
    daily trend data, and engagement metrics.

    Pass the movie title or relevant keyword as input.
    """
    if config.DEMO_MODE:
        result = {
            "error": False,
            "demo_mode": True,
            "data": _generate_demo_mentions(keyword),
        }
        return json.dumps(result)

    try:
        data = _fetch_social_mentions(keyword)
        return json.dumps({"error": False, "data": data})
    except Exception as e:
        return json.dumps({
            "error": True,
            "message": f"Social mention retrieval failed: {str(e)}",
            "data": None,
        })
