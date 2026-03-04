"""
Movie Buzz Analyzer — LangChain Agent Orchestrator
Coordinates the full pipeline: data collection → preprocessing → sentiment → scoring → HITL → DB commit.
"""
import sys
import json
import argparse
from datetime import datetime

import config
from engine.preprocessor import preprocess_batch
from engine.buzz_calculator import calculate_buzz_score
from tools.youtube_tool import youtube_data_tool, youtube_search_tool
from tools.social_mention_tool import social_mention_tool
from tools.sentiment_tool import sentiment_evaluator_tool
from tools.db_tool import db_commit_tool
from database import db


def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 60)
    print("   🎬  MOVIE BUZZ ANALYZER  🎬")
    print("   Autonomous Sentiment & Hype Analysis Agent")
    print("=" * 60)
    if config.DEMO_MODE:
        print("   ⚡ Running in DEMO MODE (synthetic data)")
    else:
        print("   🔑 API Keys detected — LIVE MODE")
    print("=" * 60 + "\n")


def step_0_find_trailer(movie_title, video_id=None):
    """Step 0: Search for trailer if no video_id or if video_id is 'auto'."""
    if video_id and video_id.lower() not in ("auto", "search", ""):
        print(f"\n🔍 Using provided video ID: {video_id}")
        return video_id

    print(f"\n🔍 [Step 0] Searching YouTube for '{movie_title}' trailer...")
    result_json = youtube_search_tool.invoke(movie_title)
    result = json.loads(result_json)

    if result.get("error") or not result.get("results"):
        print("   ❌ Could not find trailer via search.")
        return video_id  # Fall back to whatever was provided

    found = result["results"][0]
    print(f"   ✅ Found: {found.get('title', 'Unknown')}")
    print(f"   🔗 Video ID: {found['video_id']}")
    return found["video_id"]


def step_1_collect_youtube(video_id):
    """Step 1: Retrieve YouTube comments."""
    print("\n📥 [Step 1/6] Fetching YouTube comments...")
    result_json = youtube_data_tool.invoke(video_id)
    result = json.loads(result_json)

    if result.get("error"):
        print(f"   ❌ Error: {result['message']}")
        if result.get("error_type") == "RATE_LIMIT":
            print("   🛑 Rate limit hit. Agent is pausing execution.")
            sys.exit(1)
        return None

    print(f"   ✅ Collected {result['comments_collected']} comments")
    return result["data"]


def step_2_collect_social(movie_title):
    """Step 2: Retrieve social mention metrics."""
    print("\n📊 [Step 2/6] Fetching social mention metrics...")
    result_json = social_mention_tool.invoke(movie_title)
    result = json.loads(result_json)

    if result.get("error"):
        print(f"   ❌ Error: {result['message']}")
        return None

    data = result["data"]
    print(f"   ✅ Mention count: {data['mention_count']:,}")
    print(f"   📈 Growth rate: {data['growth_rate_pct']}%")
    print(f"   📱 Platforms: {', '.join(data['platforms'].keys())}")
    return data


def step_3_preprocess(comments):
    """Step 3: Clean and filter comments."""
    print("\n🧹 [Step 3/6] Preprocessing comments...")
    processed = preprocess_batch(comments)
    dropped = len(comments) - len(processed)
    print(f"   ✅ Valid comments: {len(processed)} (dropped {dropped} as spam/invalid)")
    return processed


def step_4_evaluate_sentiment(comments):
    """Step 4: Classify sentiment using the LLM evaluator."""
    print("\n🤖 [Step 4/6] Running sentiment analysis...")
    cleaned_texts = [c["cleaned_text"] for c in comments]
    result_json = sentiment_evaluator_tool.invoke(json.dumps(cleaned_texts))
    result = json.loads(result_json)

    if result.get("error"):
        print(f"   ❌ Error: {result['message']}")
        return None

    # Merge sentiment results back into comments
    for i, comment in enumerate(comments):
        if i < len(result["results"]):
            sr = result["results"][i]
            comment["sentiment_score"] = sr["score"]
            comment["sentiment_label"] = sr["label"]

    scores = [r["score"] for r in result["results"]]
    high = scores.count(3)
    neutral = scores.count(2)
    negative = scores.count(1)
    print(f"   ✅ Classified {len(scores)} comments")
    print(f"   🔥 High Hype: {high} ({high/len(scores)*100:.1f}%)")
    print(f"   🤔 Neutral:   {neutral} ({neutral/len(scores)*100:.1f}%)")
    print(f"   💀 Negative:  {negative} ({negative/len(scores)*100:.1f}%)")

    return comments, scores


def step_5_calculate_buzz(scores, mention_data):
    """Step 5: Compute the Buzz Score."""
    print("\n📐 [Step 5/6] Calculating Buzz Score...")
    result = calculate_buzz_score(scores, mention_data)

    print(f"\n   {'─' * 40}")
    print(f"   🏆 BUZZ SCORE: {result['score']:.1f} / 100")
    print(f"   {'─' * 40}")
    print(f"   Sentiment (×0.35): {result['breakdown']['sentiment_weighted']:.2f}")
    print(f"   Volume    (×0.25): {result['breakdown']['volume_weighted']:.2f}")
    print(f"   Growth    (×0.20): {result['breakdown']['growth_weighted']:.2f}")
    print(f"   Engagement(×0.20): {result['breakdown']['engagement_weighted']:.2f}")
    print(f"   {'─' * 40}")
    return result


def step_6_hitl_and_commit(movie_title, trailer_url, comments, buzz_data, auto_approve=False):
    """Step 6: HITL checkpoint, then commit to DB."""
    print("\n" + "=" * 60)
    print("   🔒 HUMAN-IN-THE-LOOP CHECKPOINT")
    print("=" * 60)
    print(f"\n   Movie:            {movie_title}")
    print(f"   Total Comments:   {buzz_data['total_comments']}")
    print(f"   Avg Sentiment:    {buzz_data['sentiment_avg']:.2f}")
    print(f"   Buzz Score:       {buzz_data['score']:.1f} / 100")
    print(f"   High Hype:        {buzz_data['high_hype_pct']:.1f}%")
    print(f"   Neutral:          {buzz_data['neutral_pct']:.1f}%")
    print(f"   Negative:         {buzz_data['negative_pct']:.1f}%")
    print(f"   Mention Volume:   {buzz_data['mention_volume']:,}")
    print(f"   Growth Rate:      {buzz_data['growth_rate']:.1f}%")
    print()

    if auto_approve:
        approval = "Y"
        print("   ⚡ Auto-approved (--auto-approve flag)")
    else:
        approval = input("   ➡️  Approve database commit? (Y/N): ").strip().upper()

    if approval != "Y":
        print("\n   ❌ Commit rejected by user. Data NOT saved.")
        return False

    print("\n   💾 Committing to database...")

    # Prepare payload
    payload = {
        "movie_title": movie_title,
        "trailer_url": trailer_url,
        "comments": comments,
        "buzz_score": buzz_data,
    }

    result_json = db_commit_tool.invoke(json.dumps(payload))
    result = json.loads(result_json)

    if result.get("error"):
        print(f"   ❌ DB Error: {result['message']}")
        return False

    print(f"   ✅ Committed! Movie ID: {result['movie_id']}")
    print(f"   📝 Comments written: {result['comments_written']}")
    print(f"   🏆 Buzz Score saved: {result['buzz_score']}")
    return True


def run_agent(movie_title, video_id=None, auto_approve=False, progress_callback=None):
    """
    Main agent execution loop.
    Orchestrates the full pipeline from data collection to DB commit.
    If video_id is None, 'auto', or 'search', the agent will search for the trailer.
    """
    print_banner()
    print(f"🎬 Analyzing: {movie_title}")

    # Initialize database
    db.init_db()

    if progress_callback:
        progress_callback(10, "Searching for trailer...")

    # Step 0: Find trailer video if needed
    video_id = step_0_find_trailer(movie_title, video_id)
    if not video_id:
        print("\n❌ Agent terminated: Could not find a trailer video.")
        return None

    print(f"🔗 Video ID: {video_id}")
    trailer_url = f"https://www.youtube.com/watch?v={video_id}"

    if progress_callback:
        progress_callback(25, "Extracting YouTube comments...")

    # Step 1: Collect YouTube comments
    raw_comments = step_1_collect_youtube(video_id)
    if not raw_comments:
        print("\n❌ Agent terminated: Failed to collect YouTube comments.")
        return None

    if progress_callback:
        progress_callback(40, "Harvesting social metrics...")

    # Step 2: Collect social mention metrics
    mention_data = step_2_collect_social(movie_title)
    if not mention_data:
        print("\n❌ Agent terminated: Failed to collect social metrics.")
        return None

    if progress_callback:
        progress_callback(50, "Cleaning and filtering data...")

    # Step 3: Preprocess comments
    processed = step_3_preprocess(raw_comments)
    if len(processed) < config.MIN_COMMENTS:
        print(f"\n⚠️  Warning: Only {len(processed)} valid comments (minimum: {config.MIN_COMMENTS})")
        print("   Proceeding with available data...")

    if progress_callback:
        progress_callback(60, "Forcing Gemini to analyze sentiment (this takes a minute)...")

    # Step 4: Sentiment analysis
    result = step_4_evaluate_sentiment(processed)
    if not result:
        print("\n❌ Agent terminated: Sentiment analysis failed.")
        return None
    processed, scores = result

    if progress_callback:
        progress_callback(85, "Calculating the final Buzz Score...")

    # Step 5: Calculate Buzz Score
    buzz_data = step_5_calculate_buzz(scores, mention_data)

    if progress_callback:
        progress_callback(95, "Committing verdict to the database...")

    # Step 6: HITL checkpoint and DB commit
    success = step_6_hitl_and_commit(
        movie_title, trailer_url, processed, buzz_data, auto_approve
    )

    if success:
        if progress_callback:
            progress_callback(100, "Analysis complete.")
        print("\n" + "=" * 60)
        print("   ✅ AGENT EXECUTION COMPLETE")
        print(f"   🏆 Final Buzz Score: {buzz_data['score']:.1f} / 100")
        print("   📊 Dashboard: http://localhost:5000")
        print("=" * 60 + "\n")

    return buzz_data


def main():
    parser = argparse.ArgumentParser(description="Movie Buzz Analyzer Agent")
    parser.add_argument("--movie", required=True, help="Movie title to analyze")
    parser.add_argument(
        "--video-id",
        default="auto",
        help="YouTube video ID for the trailer (or 'auto' to search)",
    )
    parser.add_argument("--auto-approve", action="store_true", help="Skip HITL checkpoint")
    args = parser.parse_args()

    run_agent(args.movie, args.video_id, args.auto_approve)


if __name__ == "__main__":
    main()
