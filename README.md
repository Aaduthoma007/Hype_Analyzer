# PROJECT MAYHEM: HYPE BUZZ ANALYZER 👊

> *"You are not your movie opinion. You are not your Rotten Tomatoes score. You are the all-singing, all-dancing BUZZ SCORE of the world."*

An autonomous AI agent designed to aggressively strip away the marketing noise and uncover the **raw, unfiltered truth** about upcoming movies. It hooks into the YouTube API, scrapes social mechanic data, and forces a Gemini LLM through a highly rigid, 3-tier grading rubric to synthesize the ultimate metric: **The Buzz Score**.

![Industrial Progress Bar](https://github.com/Aaduthoma007/Hype_Analyzer/assets/placeholder-progress.png) *(Note: Replace with standard repo image)*

## 🔪 The Rules of Buzz Club

1. **You do not fabricate the Buzz Score.**
2. **You DO NOT fabricate the Buzz Score.**
3. If this is a movie's first night in the backend, **it has to be analyzed.**
4. Two APIs to a fight (YouTube Data API v3 + Google Gemini).
5. One target at a time.
6. No shirts, no shoes, pure data.
7. The analysis will go on as long as it has to (tracked by a subliminal flash progress bar).

## ⚙️ Core Operations

*   **Autonomous Intelligence Gathering**: Just provide a movie title. The agent will autonomously hunt down the target's trailer using YouTube's Search API, track down the main video, and extract the raw data (comments, view counts, likes, etc.).
*   **Gemini Sentiment Engine**: The AI evaluates every single comment using a ruthless grading rubric. There are only three buckets: **High Hype** (rabid anticipation), **Neutral/Curious** (the sheep), and **Negative/Dead** (DOA).
*   **The Formula**: 
    `{ Sentiment (35%) + Mention Volume (25%) + Growth Rate (20%) + Engagement (20%) }`
*   **Subliminal Telemetry**: The loading state isn't a spinner; it's an experience. The UI leverages glitch-art aesthetics, a live industrial progress bar, and subliminal quotes flashing at 8-15 second intervals to keep you fully immersed in the operation.

## 🩸 The Stack

*   **Backend**: Python, Flask, SQLite, LangChain, Google GenAI
*   **Frontend**: Vanilla HTML/JS, Chart.js, raw CSS (No bloated frameworks. Just code.)

## 🛠️ Setup & Execution

### 1. Reclaim your environment
Clone this repository to your local machine.
```bash
git clone https://github.com/Aaduthoma007/Hype_Analyzer.git
cd Hype_Analyzer
```

### 2. Procure the supplies (Dependencies)
Install the required tools.
```bash
pip install -r requirements.txt
python -m nltk.downloader stopwords
```

### 3. Arm the system (Environment Variables)
You need keys to the building. Set these in your terminal or a `.env` file:
```bash
# Windows PowerShell
$env:YOUTUBE_API_KEY="your_youtube_v3_api_key_here"
$env:GEMINI_API_KEY="your_google_gemini_api_key_here"

# Mac/Linux
export YOUTUBE_API_KEY="your_youtube_v3_api_key_here"
export GEMINI_API_KEY="your_google_gemini_api_key_here"
```

### 4. Initiate Project Mayhem
Boot up the dashboard.
```bash
python app.py
```
*Target acquired. Open your browser to `http://localhost:5000`.*

---

## ☁️ Deployment (PythonAnywhere)

Since Render requires a credit card for persistent SQLite databases, we highly recommend **PythonAnywhere** for a free and persistent deployment.

1.  Create a free account at [PythonAnywhere](https://www.pythonanywhere.com/).
2.  Open a **Bash Console** from your dashboard.
3.  Clone the repository:
    ```bash
    git clone https://github.com/Aaduthoma007/Hype_Analyzer.git
    cd Hype_Analyzer
    ```
4.  Install dependencies:
    ```bash
    pip3 install --user -r requirements.txt
    python3 -m nltk.downloader stopwords
    ```
5.  Set your API keys permanently by opening `~/.bashrc` (e.g., `nano ~/.bashrc`) and adding:
    ```bash
    export YOUTUBE_API_KEY="your_api_key_here"
    export GEMINI_API_KEY="your_api_key_here"
    ```
    Then run `source ~/.bashrc`.
6.  Go to the **Web** tab in PythonAnywhere and click **Add a new web app**.
    *   Choose **Manual configuration** (not the web framework defaults).
    *   Choose **Python 3.10** (or your preferred version).
7.  In the WSGI configuration file (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`), delete everything and add:
    ```python
    import sys
    import os

    # Add your project directory to the sys.path
    path = '/home/yourusername/Hype_Analyzer'
    if path not in sys.path:
        sys.path.append(path)

    # Load environment variables (since WSGI doesn't automatically load ~/.bashrc)
    os.environ['YOUTUBE_API_KEY'] = 'your_api_key_here'
    os.environ['GEMINI_API_KEY'] = 'your_api_key_here'

    # Import your Flask app
    from app import app as application
    ```
8.  Reload the web app from the Web tab. Your dashboard is now live at `yourusername.pythonanywhere.com`.

---

*“This is your data, and it's ending one comment at a time.”*
