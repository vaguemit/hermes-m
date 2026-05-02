# Hermes-M — GhostDesk Marketing Agent

> **Local-first AI marketing agent** for GhostDesk.  
> Fast local drafts via **Ollama (gemma3:4b / hermes)** → quality review via **DeepSeek or OpenAI** → human approval queue → auto-post.

---

## Architecture

```
User prompt / Scheduler
        │
        ▼
┌──────────────────────────┐
│  Ollama  (local, free)   │  ← gemma3:4b-it-qf4_K_M  (or any hermes / llama model)
│  Fast first-pass draft   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Review LLM  (cloud)     │  ← DeepSeek Chat  (default, cheapest)
│  Quality polish          │     or OpenAI GPT-4o-mini / GPT-4o
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Approval Queue (SQLite) │  ← you approve/reject via Web UI or CLI
└──────────┬───────────────┘
           │
           ▼
    Reddit / LinkedIn / Gmail
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.11 | Runtime |
| [Ollama](https://ollama.com) | latest | Local LLM server |
| DeepSeek or OpenAI account | — | Cloud review LLM |
| Reddit App | — | Posting to subreddits |
| Gmail App Password | — | Email campaigns |
| Razorpay account | — | Analytics (optional) |

---

## Step 1 — Install Ollama & pull a model

### Install Ollama
Download from **https://ollama.com/download** and install it.  
After install, Ollama runs automatically at `http://localhost:11434`.

### Pull your model

You said you already pulled `nous-hermes2` (hermes) — that works fine!  
Or pull the new recommended model:

```bash
# Option A — hermes (already installed, works great)
ollama pull nous-hermes2

# Option B — gemma3 4B (recommended, lighter, faster)
ollama pull gemma3:4b-it-qf4_K_M

# Option C — gemma4 e4b (newest, if your machine can handle it)
ollama pull gemma4:e4b
```

Then set the model name in your `.env` (see Step 4).

### Verify Ollama is running

```bash
ollama list          # should show your pulled models
ollama run nous-hermes2 "hello"   # quick sanity check
```

---

## Step 2 — Clone & set up Python environment

```bash
git clone https://github.com/vaguemit/hermes-m.git
cd hermes-m

# Create a virtual environment (strongly recommended)
python -m venv .venv

# Activate it
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate
```

---

## Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `ollama` — Python client for local Ollama
- `openai` — used for **both** OpenAI and DeepSeek (DeepSeek is OpenAI-compatible)
- `fastapi` + `uvicorn` — Web UI server
- `praw` — Reddit API
- `apscheduler` — Scheduled jobs (auto-draft every Tue/Fri)
- `rich` + `typer` — CLI
- `pydantic-settings` — Config from `.env`

---

## Step 4 — Configure `.env`

Copy the example and fill in your secrets:

```bash
cp .env.example .env
```

Open `.env` and edit:

```env
# ── Local LLM ─────────────────────────────────────────────────────────────────
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nous-hermes2        # ← change to gemma3:4b-it-qf4_K_M if you pulled that

# ── Review LLM ────────────────────────────────────────────────────────────────
REVIEW_PROVIDER=deepseek         # or: openai

# DeepSeek (cheap, ~$0.0014/1K tokens) → https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat     # or: deepseek-reasoner (chain-of-thought, slower)

# OpenAI (only needed if REVIEW_PROVIDER=openai)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini         # or: gpt-4o

# ── Reddit OAuth ───────────────────────────────────────────────────────────────
# Create app at: https://www.reddit.com/prefs/apps  (choose "script" type)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=GhostDeskAgent/1.0 by /u/your_username

# ── Gmail SMTP ─────────────────────────────────────────────────────────────────
# Use an App Password (NOT your real password)
# Enable at: https://myaccount.google.com/apppasswords
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# ── Razorpay (analytics, optional) ────────────────────────────────────────────
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...

# ── Agent behavior ─────────────────────────────────────────────────────────────
APPROVAL_REQUIRED=true           # false = auto-post without asking (risky!)
CHAT_PORT=8765
LOG_LEVEL=INFO
```

### Getting API keys

**DeepSeek** (recommended — very cheap):
1. Go to https://platform.deepseek.com/api_keys
2. Create a key → paste as `DEEPSEEK_API_KEY`

**OpenAI** (alternative):
1. Go to https://platform.openai.com/api-keys
2. Create a key → paste as `OPENAI_API_KEY`
3. Set `REVIEW_PROVIDER=openai`

**Reddit App**:
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app" → choose **script**
3. Name: `GhostDeskAgent`, redirect: `http://localhost:8080`
4. Copy the client ID (under app name) and secret

---

## Step 5 — Run the agent

### Option A — Full server (Web UI + scheduler)

```bash
python main.py start
```

This will:
- Start the APScheduler (auto-drafts Reddit posts Tue/Fri, LinkedIn Wed, analytics Sunday)
- Run an initial monitor sweep
- Start the Web UI at **http://localhost:8765**

Open your browser → `http://localhost:8765` to use the chat interface and approval queue.

### Option B — CLI only (no server)

```bash
# Interactive chat with the agent
python main.py chat

# Draft content now
python main.py draft reddit
python main.py draft linkedin
python main.py draft email

# View pending queue
python main.py queue

# Approve item #3 (posts it to Reddit/Gmail/etc.)
python main.py approve 3

# Reject item #3
python main.py reject 3

# Run monitor sweep now (scans Reddit for mentions)
python main.py monitor

# Generate analytics report now
python main.py analytics
```

---

## How the pipeline works

### 1. Draft (Ollama — local, free)
- Runs entirely on your machine
- Uses the hermes / gemma model you pulled
- Fast: ~2–5 seconds
- No API cost

### 2. Review (DeepSeek / OpenAI — cloud)
- Polishes the draft for tone, clarity, and effectiveness
- DeepSeek Chat: ~$0.001 per review (very cheap)
- OpenAI GPT-4o-mini: ~$0.003 per review
- Skippable: `generate_and_queue(..., skip_review=True)`

### 3. Approval queue (SQLite)
- All content sits in `agent.db` with status `pending`
- You approve via Web UI or CLI before anything is posted
- Set `APPROVAL_REQUIRED=false` to auto-post (not recommended)

### 4. Posting
- **Reddit** → PRAW posts directly via Reddit OAuth
- **Email** → Gmail SMTP with App Password
- **LinkedIn** → Draft stored for manual posting (LinkedIn API requires company page access)

---

## Switching between hermes and gemma

Since `OLLAMA_MODEL` is read from `.env`, you can switch anytime without touching code:

```env
# Use hermes (already installed)
OLLAMA_MODEL=nous-hermes2

# Use gemma3 4B (lighter, faster)
OLLAMA_MODEL=gemma3:4b-it-qf4_K_M

# Use gemma4 e4b (newest)
OLLAMA_MODEL=gemma4:e4b
```

---

## Switching review provider

```env
# Cheap + great quality (default)
REVIEW_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-chat

# DeepSeek with chain-of-thought reasoning (slower, better for complex tasks)
REVIEW_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-reasoner

# OpenAI fast
REVIEW_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# OpenAI max quality
REVIEW_PROVIDER=openai
OPENAI_MODEL=gpt-4o
```

---

## Project structure

```
hermes-m/
├── main.py              # CLI entry point (typer)
├── agent.py             # Core pipeline: Ollama draft → LLM review → queue
├── chat_server.py       # FastAPI web server + HTML UI
├── config.py            # Settings loaded from .env (pydantic-settings)
├── memory.py            # SQLite: queue, chat history, monitor cache
├── scheduler_setup.py   # APScheduler jobs (auto content calendar)
├── tools/
│   ├── reddit.py        # PRAW Reddit posting
│   ├── email_tool.py    # Gmail SMTP campaigns
│   ├── linkedin.py      # LinkedIn draft helpers
│   ├── monitor.py       # Reddit mention monitoring
│   └── analytics.py     # Razorpay analytics reports
├── requirements.txt
├── .env.example         # Template — copy to .env
└── agent.db             # Created automatically on first run (SQLite)
```

---

## Scheduled jobs (automatic)

| Job | Schedule | What it does |
|-----|----------|-------------|
| Monitor sweep | Every 6 hours | Scans Reddit for GhostDesk / competitor mentions |
| Reddit draft | Tue + Fri 10am | Drafts a post → queued for your approval |
| LinkedIn draft | Wed 11am | Drafts a post → queued for your approval |
| Analytics report | Sun 9am | Generates weekly Razorpay sales summary |

All scheduled content goes to the approval queue — **nothing posts automatically** unless you set `APPROVAL_REQUIRED=false`.

---

## Troubleshooting

### `ollama: connection refused`
Ollama isn't running. Start it:
```bash
ollama serve
```

### `DEEPSEEK_API_KEY is not set`
Make sure `.env` exists (not just `.env.example`) and has the key filled in.

### `praw.exceptions.OAuthException`
Check your Reddit `CLIENT_ID`, `CLIENT_SECRET`, `USERNAME`, `PASSWORD` in `.env`. Make sure the Reddit app type is **script**.

### `SMTPAuthenticationError` (Gmail)
Use an **App Password**, not your real Gmail password.  
Enable at: https://myaccount.google.com/apppasswords

### `ModuleNotFoundError`
Make sure your virtual environment is activated and you ran `pip install -r requirements.txt`.

---

## Cost estimate (per month, typical usage)

| Component | Cost |
|-----------|------|
| Ollama (local) | **$0** — runs on your machine |
| DeepSeek Chat (review, ~200 reviews/mo) | **~$0.30** |
| OpenAI GPT-4o-mini (if used) | **~$0.60** |
| Reddit API | **Free** |
| Gmail SMTP | **Free** |

---

## License

MIT
