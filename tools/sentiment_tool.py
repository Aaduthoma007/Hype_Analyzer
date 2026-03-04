"""
LLM Sentiment Evaluator — LangChain tool using Google Gemini.
Classifies movie comments using the strict 3-tier hype rubric.
"""
import json
import re
import random
from langchain_core.tools import tool

import config

# ── Rubric Prompt ─────────────────────────────────────────

SENTIMENT_SYSTEM_PROMPT = """You are a movie hype sentiment classifier. You MUST classify each comment using ONLY this rubric:

**High Hype (Score 3):** The text contains strong intent to watch the movie. Look for phrases like "opening night", "can't wait", "buying tickets", "day one", "must-see", "pre-ordered", extreme excitement, or strong positive anticipation.

**Neutral/Curious (Score 2):** The text discusses the movie but lacks immediate intent to watch. Look for phrases like "looks okay", "might wait for streaming", "interesting", "not sure", "wait for reviews", or mixed/moderate opinions.

**Negative/Dead (Score 1):** The text expresses active disinterest, disappointment, or hate. Look for phrases like "looks terrible", "hard pass", "cash grab", "boring", "waste", or strong negative sentiment.

IMPORTANT RULES:
- You MUST return ONLY valid JSON. No markdown, no explanation.
- Each comment gets exactly ONE score: 1, 2, or 3.
- Do NOT invent new categories.
- If uncertain, lean toward Neutral/Curious (2).

Input format: A JSON array of comment strings.
Output format: A JSON array of objects, each with "text", "score", and "label" fields.

Example output:
[
  {"text": "cant wait opening night", "score": 3, "label": "High Hype"},
  {"text": "looks okay might stream", "score": 2, "label": "Neutral/Curious"},
  {"text": "hard pass terrible", "score": 1, "label": "Negative/Dead"}
]"""


# ── Demo Classifier ──────────────────────────────────────

HIGH_HYPE_KEYWORDS = [
    "opening night", "can't wait", "cant wait", "buying tickets", "day one",
    "must-see", "must see", "pre-ordered", "preordered", "epic", "incredible",
    "phenomenal", "mind-blowing", "mindblowing", "goosebumps", "chills",
    "take my money", "insane", "amazing", "love", "hyped", "best",
    "imax", "tickets", "🔥", "😍", "💯", "booked", "clearing schedule",
]

NEGATIVE_KEYWORDS = [
    "terrible", "hard pass", "cash grab", "boring", "disaster", "waste",
    "terrible", "bomb", "sleep", "asleep", "died", "dead", "worst",
    "generic", "nobody asked", "paint dry", "no taste", "bad", "awful",
    "yikes", "👎", "💀", "dvd", "let it die",
]


def _demo_classify(text):
    """Simple keyword-based classification for demo mode."""
    lower = text.lower()
    for kw in HIGH_HYPE_KEYWORDS:
        if kw in lower:
            return {"text": text, "score": 3, "label": "High Hype"}
    for kw in NEGATIVE_KEYWORDS:
        if kw in lower:
            return {"text": text, "score": 1, "label": "Negative/Dead"}
    return {"text": text, "score": 2, "label": "Neutral/Curious"}


def _classify_batch_with_llm(texts):
    """Classify a batch of texts using Google Gemini via LangChain."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GEMINI_API_KEY,
        temperature=0.1,
    )

    prompt_texts = json.dumps(texts)
    messages = [
        SystemMessage(content=SENTIMENT_SYSTEM_PROMPT),
        HumanMessage(content=f"Classify these comments:\n{prompt_texts}"),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # Try to extract JSON from response (handle markdown code blocks)
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        content = json_match.group()

    try:
        results = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: classify each text individually with demo classifier
        results = [_demo_classify(t) for t in texts]

    # Validate and ensure correct structure
    validated = []
    for i, item in enumerate(results):
        score = item.get("score", 2)
        if score not in (1, 2, 3):
            score = 2
        label = {1: "Negative/Dead", 2: "Neutral/Curious", 3: "High Hype"}.get(score)
        validated.append({
            "text": texts[i] if i < len(texts) else item.get("text", ""),
            "score": score,
            "label": label,
        })

    return validated


@tool
def sentiment_evaluator_tool(comments_json: str) -> str:
    """
    Classify cleaned movie comment texts using the strict 3-tier hype rubric.
    
    Input: A JSON string containing an array of cleaned comment strings.
    Output: A JSON string with an array of {text, score, label} objects.
    
    Rubric:
    - High Hype (Score 3): Strong intent to watch
    - Neutral/Curious (Score 2): Discusses movie, no strong intent
    - Negative/Dead (Score 1): Active disinterest or hate
    
    IMPORTANT: Pass text through the preprocessing pipeline BEFORE using this tool.
    """
    try:
        texts = json.loads(comments_json)
    except json.JSONDecodeError:
        return json.dumps({"error": True, "message": "Invalid JSON input"})

    if not isinstance(texts, list):
        return json.dumps({"error": True, "message": "Input must be a JSON array of strings"})

    all_results = []
    batch_size = config.SENTIMENT_BATCH_SIZE

    if config.DEMO_MODE:
        # Use keyword-based classification
        all_results = [_demo_classify(t) for t in texts]
    else:
        # Process in batches to respect LLM context limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                batch_results = _classify_batch_with_llm(batch)
                all_results.extend(batch_results)
            except Exception as e:
                # Fallback to demo classification on error
                fallback = [_demo_classify(t) for t in batch]
                all_results.extend(fallback)

    return json.dumps({
        "error": False,
        "total_classified": len(all_results),
        "results": all_results,
    })
