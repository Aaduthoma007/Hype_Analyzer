"""
Text Preprocessing Pipeline
Cleans and filters comment text before sentiment analysis.
"""
import re
import string

# Simple stopword list to avoid NLTK download dependency
STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her",
    "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs",
    "themselves", "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for", "with",
    "about", "against", "between", "through", "during", "before", "after", "above",
    "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now", "d", "ll", "m", "o", "re",
    "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven",
    "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
    "won", "wouldn",
}


def clean_text(text):
    """
    Clean a single text string:
    1. Lowercase
    2. Remove URLs
    3. Remove punctuation (keep spaces)
    4. Remove stopwords
    5. Strip extra whitespace
    """
    # Lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # Remove emoji (keep alphanumeric and spaces)
    text = re.sub(r'[^\w\s]', ' ', text)

    # Remove extra digits that aren't meaningful
    text = re.sub(r'\b\d{4,}\b', '', text)

    # Remove stopwords
    words = text.split()
    words = [w for w in words if w not in STOPWORDS and len(w) > 1]

    # Rejoin and strip whitespace
    text = ' '.join(words).strip()

    return text


def is_valid_comment(text):
    """
    Validate a comment for data integrity:
    - Must not exceed 500 characters
    - Must not contain hyperlinks
    """
    if not text or len(text.strip()) == 0:
        return False
    if len(text) > 500:
        return False
    url_pattern = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
    if url_pattern.search(text):
        return False
    return True


def preprocess_batch(comments):
    """
    Process a list of comment dicts through validation and cleaning.
    Input:  [{"text": "...", ...}, ...]
    Output: [{"text": "original", "cleaned_text": "cleaned", ...}, ...] (only valid ones)
    """
    processed = []
    for comment in comments:
        raw = comment.get("text", "")
        if not is_valid_comment(raw):
            continue
        cleaned = clean_text(raw)
        if len(cleaned.strip()) < 3:
            continue
        entry = dict(comment)
        entry["raw_text"] = raw
        entry["cleaned_text"] = cleaned
        processed.append(entry)

    return processed
