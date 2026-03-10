"""
YouTube Data Tool — LangChain tool wrapping YouTube Data API v3.
Fetches comments from movie trailer videos.
"""
import re
import json
import random
from datetime import datetime, timedelta
from langchain_core.tools import tool

import config


# ── Demo Data ─────────────────────────────────────────────

DEMO_COMMENTS_POOL = [
    # High Hype
    "I'm buying tickets for opening night, this looks INCREDIBLE!",
    "Can't wait for this movie! Day one for sure!",
    "This trailer gave me chills. Definitely watching opening weekend!",
    "Take my money already! Best trailer I've seen all year!",
    "Opening night squad, who's with me? This looks phenomenal!",
    "I've watched this trailer 50 times already. Can't wait!",
    "This is going to break box office records, I'm calling it now!",
    "Pre-ordered my IMAX tickets. This movie is going to be epic!",
    "Goosebumps every single time. Day one, no question.",
    "I'm clearing my entire schedule for opening weekend!",
    "This looks absolutely mind-blowing. Instant must-watch!",
    "Already booked the whole row for my friends. Opening night baby!",
    "The visuals alone make this a must-see in theaters!",
    "I haven't been this hyped for a movie in years!",
    "Shut up and take my money! This looks insane!",
    # Neutral / Curious
    "Looks interesting, might check it out when it hits streaming.",
    "Not sure about this one. The cast is good though.",
    "The trailer was okay. I'll wait for reviews.",
    "Could go either way. Some parts look cool, others not so much.",
    "Hmm, looks decent. Probably a rental for me.",
    "Interesting concept. Hope they execute it well.",
    "Mixed feelings from this trailer. Curious to see more.",
    "I'll probably wait for word of mouth before deciding.",
    "The premise is intriguing but I'm not fully sold yet.",
    "Looks like it could be fun but nothing groundbreaking.",
    "Might wait for streaming, doesn't seem like a theater must-see.",
    "Some cool moments in the trailer but overall just okay.",
    "I'll check the Rotten Tomatoes score first.",
    "Average looking trailer but the director usually delivers.",
    "Cautiously optimistic about this one.",
    # Negative / Dead
    "This looks absolutely terrible. Hard pass.",
    "Another generic cash grab. Wake me up when Hollywood has new ideas.",
    "Yikes, this looks like a disaster. Saving my money.",
    "The CGI looks terrible and the plot seems predictable. No thanks.",
    "I fell asleep during the trailer. That's how boring this looks.",
    "Hard pass. This looks like straight-to-DVD quality.",
    "Why do they keep making these? Nobody asked for this.",
    "This is going to bomb so hard at the box office.",
    "Terrible casting, terrible effects, terrible story. Triple threat of bad.",
    "I'd rather watch paint dry than sit through this movie.",
    "What a waste of a good cast on such a terrible script.",
    "Not even free tickets would get me to watch this.",
    "This looks like it was made by an AI with no taste.",
    "Dead on arrival. Nobody is going to watch this.",
    "The franchise peaked years ago. Let it die already.",
]


def _generate_demo_comments(video_id, count=550):
    """Generate synthetic comments for demo mode."""
    comments = []
    authors = [f"User_{i}" for i in range(200)]
    for i in range(count):
        text = random.choice(DEMO_COMMENTS_POOL)
        # Add slight variation
        if random.random() > 0.7:
            text = text + " " + random.choice(["🔥", "💯", "👎", "🤔", "😍", "💀", "👀"])
        comments.append({
            "author": random.choice(authors),
            "text": text,
            "published_at": (
                datetime.now() - timedelta(hours=random.randint(1, 720))
            ).isoformat(),
            "like_count": random.randint(0, 500),
            "video_id": video_id,
        })
    return comments


def _is_valid_comment(text):
    """Filter out spam: reject hyperlinks and text > 500 chars."""
    if len(text) > config.MAX_COMMENT_LENGTH:
        return False
    url_pattern = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
    if url_pattern.search(text):
        return False
    return True


def _fetch_youtube_comments(video_id, max_results=200):
    """Fetch comments from YouTube Data API v3."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)

    comments = []
    next_page_token = None

    while len(comments) < max_results:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_results - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance",
            )
            response = request.execute()
        except HttpError as e:
            if e.resp.status == 429:
                return {
                    "error": True,
                    "error_type": "RATE_LIMIT",
                    "message": "YouTube API rate limit hit (429). Agent must pause execution.",
                    "comments_collected": len(comments),
                    "data": comments,
                }
            else:
                return {
                    "error": True,
                    "error_type": "API_ERROR",
                    "message": f"YouTube API error: {e.resp.status} — {str(e)}",
                    "comments_collected": len(comments),
                    "data": comments,
                }

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            text = snippet.get("textDisplay", "")
            if _is_valid_comment(text):
                comments.append({
                    "author": snippet.get("authorDisplayName", "Anonymous"),
                    "text": text,
                    "published_at": snippet.get("publishedAt", ""),
                    "like_count": snippet.get("likeCount", 0),
                    "video_id": video_id,
                })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return {
        "error": False,
        "comments_collected": len(comments),
        "data": comments,
    }


def _search_youtube_trailer(query, max_results=5):
    """Search YouTube for a movie trailer and return video IDs."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)

    try:
        request = youtube.search().list(
            part="snippet",
            q=f"{query} official trailer",
            type="video",
            maxResults=max_results,
            order="relevance",
            videoCategoryId="1",  # Film & Animation
        )
        response = request.execute()
    except HttpError as e:
        return {"error": True, "message": f"YouTube Search error: {str(e)}", "results": []}

    results = []
    for item in response.get("items", []):
        results.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
        })

    return {"error": False, "results": results}


@tool
def youtube_search_tool(movie_title: str) -> str:
    """
    Search YouTube for a movie trailer and return matching video IDs.
    Use this to find the correct trailer video ID for a movie.
    """
    if config.DEMO_MODE:
        return json.dumps({
            "error": False,
            "demo_mode": True,
            "results": [{"video_id": "demo", "title": f"{movie_title} - Official Trailer"}],
        })

    result = _search_youtube_trailer(movie_title)
    return json.dumps(result)


@tool
def youtube_data_tool(video_id: str) -> str:
    """
    Fetch comments from a YouTube video using the YouTube Data API v3.
    Use this EXCLUSIVELY for retrieving comments from specific movie trailer videos.
    Pass a YouTube video ID (e.g., 'dQw4w9WgXcQ').

    Returns a JSON string with the collected comments.
    On rate limit (429), returns an error state — do NOT retry.
    """
    if config.DEMO_MODE:
        result = {
            "error": False,
            "demo_mode": True,
            "comments_collected": 0,
            "data": [],
        }
        demo = _generate_demo_comments(video_id, count=550)
        result["data"] = demo
        result["comments_collected"] = len(demo)
        return json.dumps(result)

    result = _fetch_youtube_comments(video_id)
    return json.dumps(result)
