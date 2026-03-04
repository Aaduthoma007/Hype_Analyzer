"""
Buzz Score Calculation Engine
Computes the final Buzz Score (0-100) using the predefined weighted formula.
"""
import config


def _normalize_sentiment(scores):
    """
    Normalize average sentiment score to 0-100.
    Scores are 1-3, so: normalized = ((avg - 1) / 2) * 100
    """
    if not scores:
        return 0.0
    avg = sum(scores) / len(scores)
    normalized = ((avg - 1) / 2) * 100
    return round(min(max(normalized, 0), 100), 2)


def _normalize_volume(mention_count, max_expected=100000):
    """
    Normalize mention volume to 0-100.
    Uses logarithmic scaling for more balanced distribution.
    """
    import math
    if mention_count <= 0:
        return 0.0
    # Log scale: 0 mentions = 0, max_expected = 100
    normalized = (math.log10(mention_count + 1) / math.log10(max_expected + 1)) * 100
    return round(min(max(normalized, 0), 100), 2)


def _normalize_growth(growth_rate_pct):
    """
    Normalize growth rate percentage to 0-100.
    Maps -100% to 0, 0% to 50, and +100% to 100.
    """
    normalized = (growth_rate_pct + 100) / 2
    return round(min(max(normalized, 0), 100), 2)


def _normalize_engagement(engagement_data):
    """
    Normalize engagement metrics to 0-100.
    Uses a composite of likes, shares, and replies.
    """
    avg_likes = engagement_data.get("avg_likes", 0)
    avg_shares = engagement_data.get("avg_shares", 0)
    avg_replies = engagement_data.get("avg_replies", 0)

    # Weighted composite (likes matter most, then shares, then replies)
    composite = (avg_likes * 0.5) + (avg_shares * 0.3) + (avg_replies * 0.2)

    # Normalize using sigmoid-like curve, capping at ~1000 interactions
    import math
    normalized = (1 - math.exp(-composite / 300)) * 100
    return round(min(max(normalized, 0), 100), 2)


def calculate_buzz_score(sentiment_scores, mention_data, engagement_data=None):
    """
    Calculate the final Buzz Score (0-100) using exact weights:
    Buzz = (0.35 * NormSentiment) + (0.25 * VolumeFactor) + (0.20 * GrowthRate) + (0.20 * EngagementScore)

    Parameters
    ----------
    sentiment_scores : list[int]
        List of sentiment scores (each 1, 2, or 3)
    mention_data : dict
        {mention_count: int, growth_rate_pct: float, engagement: {...}}
    engagement_data : dict, optional
        Override engagement data; if None, uses mention_data["engagement"]

    Returns
    -------
    dict with keys:
        score, sentiment_norm, volume_norm, growth_norm, engagement_norm,
        sentiment_avg, total_comments, high_hype_pct, neutral_pct, negative_pct, breakdown
    """
    if engagement_data is None:
        engagement_data = mention_data.get("engagement", {})

    # Normalize each component
    sentiment_norm = _normalize_sentiment(sentiment_scores)
    volume_norm = _normalize_volume(mention_data.get("mention_count", 0))
    growth_norm = _normalize_growth(mention_data.get("growth_rate_pct", 0))
    engagement_norm = _normalize_engagement(engagement_data)

    # Apply formula weights
    buzz_score = (
        config.W_SENTIMENT * sentiment_norm
        + config.W_VOLUME * volume_norm
        + config.W_GROWTH * growth_norm
        + config.W_ENGAGEMENT * engagement_norm
    )
    buzz_score = round(min(max(buzz_score, 0), 100), 2)

    # Compute sentiment distribution
    total = len(sentiment_scores) if sentiment_scores else 1
    high_hype_count = sentiment_scores.count(3)
    neutral_count = sentiment_scores.count(2)
    negative_count = sentiment_scores.count(1)

    sentiment_avg = round(sum(sentiment_scores) / total, 2) if sentiment_scores else 0

    return {
        "score": buzz_score,
        "sentiment_norm": sentiment_norm,
        "volume_norm": volume_norm,
        "growth_norm": growth_norm,
        "engagement_norm": engagement_norm,
        "sentiment_avg": sentiment_avg,
        "mention_volume": mention_data.get("mention_count", 0),
        "growth_rate": mention_data.get("growth_rate_pct", 0),
        "engagement": engagement_norm,
        "total_comments": total,
        "high_hype_pct": round(high_hype_count / total * 100, 2),
        "neutral_pct": round(neutral_count / total * 100, 2),
        "negative_pct": round(negative_count / total * 100, 2),
        "breakdown": {
            "sentiment_weighted": round(config.W_SENTIMENT * sentiment_norm, 2),
            "volume_weighted": round(config.W_VOLUME * volume_norm, 2),
            "growth_weighted": round(config.W_GROWTH * growth_norm, 2),
            "engagement_weighted": round(config.W_ENGAGEMENT * engagement_norm, 2),
        },
    }
