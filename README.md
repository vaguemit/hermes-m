# Hermes-M — GhostDesk Marketing Agent

> **Local-first AI marketing agent** for GhostDesk.  
> Fast local drafts via **NousResearch Hermes Agent** (or Ollama) → quality review via **DeepSeek or OpenAI** → human approval queue → auto-post.

---

## ⚠️ Two Different Things Named "Hermes" — Read This First

There are two separate things in this stack with "Hermes" in the name. Don't confuse them:

| | What it is | How you installed it |
|---|---|---|
| **NousResearch Hermes Agent** | A full autonomous agent CLI framework (the `hermes` command) | `curl -fsSL .../install.sh \| bash` |
| **nous-hermes2** | An LLM model weight (runs inside Ollama) | `ollama pull nous-hermes2` |

**What you installed** (the curl script) is the **NousResearch Hermes Agent framework** — a standalone CLI agent with its own memory, skills, and model selector.  
This project (`hermes-m`) uses **Ollama** as the local LLM server and calls model weights directly from Python. The Hermes Agent CLI is a separate tool you can run independently.

---

## Architecture

```
User prompt / Scheduler
        │
        ▼
┌──────────────────────────────┐
│  Ollama  (local, free)       │  ← serves any model: gemma3:4b, nous-hermes2, etc.
│  Python client calls it      │    via HTTP at localhost:11434
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Review LLM  (cloud)         │  ← DeepSeek Chat  (default, cheapest)
│  Quality polish              │     or OpenAI GPT-4o-mini / GPT-4o
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Approval Queue (SQLite)     │  ← you approve/reject via Web UI or CLI
└──────────┬───────────────────┘
           │
           ▼
    Reddit / LinkedIn / Gmail
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.11 | Runtime |
| [Ollama](https://ollama.com) | latest | Local LLM server (separate from Hermes Agent CLI) |
| WSL2 (Windows only) | latest | Required only for the Hermes Agent CLI — **not** required for this project |
| DeepSeek or OpenAI account | — | Cloud review LLM |
| Reddit App | — | Posting to subreddits |
| Gmail App Password | — | Email campaigns |
| Razorpay account | — | Analytics (optional) |

---

## Step 1 — Install Ollama & pull a model

> **Important:** This project uses **Ollama**, not the Hermes Agent CLI you installed.
> Ollama is a separate, lightweight local model server that runs in the background.

### Install Ollama on Windows
Download from **https://ollama.com/download/windows** and install it.  
After install, Ollama runs automatically at `http://localhost:11434`.

### Pull your model

```bash
# Option A — gemma3 4B (recommended — lightweight, fast)
ollama pull gemma3:4b-it-qf4_K_M

# Option B — gemma4 e4b (newest)
ollama pull gemma4:e4b

# Option C — nous-hermes2 (the model weight, if you want to use it)
ollama pull nous-hermes2
```

### Verify Ollama is running

```bash
ollama list           # shows all pulled models
ollama run gemma3:4b-it-qf4_K_M "hello"   # quick sanity check
```

---

## Step 2 — What about the Hermes Agent CLI you installed?

The `hermes` CLI (from `curl -fsSL .../install.sh | bash`) is a **separate autonomous agent framework** by NousResearch. It's a powerful general-purpose AI agent — think of it like a local version of Claude with terminal access, memory, skills, and multi-platform messaging (Telegram, Discord, etc.).

**You can use it in parallel with this project** — they don't conflict. Here's the difference:

| | hermes-m (this project) | NousResearch Hermes Agent |
|---|---|---|
| Purpose | GhostDesk marketing automation | General-purpose autonomous agent |
| LLM backend | Ollama (via Python) | Any provider (OpenRouter, Nous Portal, etc.) |
| Entry point | `python main.py` | `hermes` CLI command |
| Interface | Web UI + CLI commands | Terminal TUI / Telegram / Discord |
| Memory | SQLite queue + chat history | Built-in persistent skills + memory |

> **Note:** The Hermes Agent CLI requires WSL2 on Windows. This project (`hermes-m`) runs natively on Windows with Python.

### Using Hermes Agent CLI (for general tasks)
```bash
# In WSL2 terminal:
hermes                    # Start interactive TUI
hermes model              # Switch LLM provider/model
hermes setup              # Full setup wizard
hermes gateway start      # Connect to Telegram/Discord
```

---

## Step 3 — Clone & set up Python environment

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
# macOS/Linux/WSL2:
source .venv/bin/activate
```

---

## Step 4 — Install Python dependencies

```bash
pip install -r requirements.txt
```

Installs:
- `ollama` — Python client for local Ollama API
- `openai` — used for **both** OpenAI and DeepSeek (DeepSeek uses OpenAI-compatible API)
- `fastapi` + `uvicorn` — Web UI server
- `praw` — Reddit API
- `apscheduler` — Scheduled jobs
- `rich` + `typer` — CLI
- `pydantic-settings` — Config loader

---

## Step 5 — Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```env
# ── Local LLM (Ollama) ────────────────────────────────────────────────────────
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma3:4b-it-qf4_K_M    # or: nous-hermes2, gemma4:e4b, llama3.1

# ── Review LLM ────────────────────────────────────────────────────────────────
REVIEW_PROVIDER=deepseek              # or: openai

# DeepSeek → https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat          # or: deepseek-reasoner (chain-of-thought)

# OpenAI → https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini              # or: gpt-4o

# ── Reddit OAuth ───────────────────────────────────────────────────────────────
# Create app at: https://www.reddit.com/prefs/apps  (type: "script")
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=GhostDeskAgent/1.0 by /u/your_username

# ── Gmail SMTP ─────────────────────────────────────────────────────────────────
# Use App Password: https://myaccount.google.com/apppasswords
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# ── Razorpay (optional, for analytics) ────────────────────────────────────────
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...

# ── Agent behavior ─────────────────────────────────────────────────────────────
APPROVAL_REQUIRED=true
CHAT_PORT=8765
LOG_LEVEL=INFO
```

### Getting API keys quickly

**DeepSeek** (~$0.001/review, recommended):
1. https://platform.deepseek.com/api_keys → Create key → paste as `DEEPSEEK_API_KEY`

**OpenAI** (alternative):
1. https://platform.openai.com/api-keys → Create key → set `REVIEW_PROVIDER=openai`

**Reddit App**:
1. https://www.reddit.com/prefs/apps → "create another app" → **script** type
2. Redirect URI: `http://localhost:8080`
3. Copy the client ID (shown below app name) and secret

---

## Step 6 — Run

### Full server (Web UI + scheduler)

```bash
python main.py start
```

Opens the Web UI at **http://localhost:8765**. Includes:
- Chat interface (type marketing requests)
- Approval queue (approve/reject before posting)
- Reports section

### CLI commands

```bash
python main.py chat              # Interactive chat with the agent
python main.py draft reddit      # Draft a Reddit post now
python main.py draft linkedin    # Draft a LinkedIn post now
python main.py draft email       # Draft an email campaign now
python main.py queue             # View pending approval queue
python main.py approve 3         # Approve & post item #3
python main.py reject 3          # Reject item #3
python main.py monitor           # Run a Reddit mention sweep now
python main.py analytics         # Generate Razorpay analytics report
```

---

## How the pipeline works

### Step A — Draft (Ollama, local, free)
- Gemma/Hermes model runs entirely on your machine
- ~2–5 seconds, zero API cost
- Raw first-pass draft

### Step B — Review (DeepSeek / OpenAI, cloud)
- Polishes tone, clarity, effectiveness
- DeepSeek Chat: ~$0.001 per call
- Skip it: `generate_and_queue(..., skip_review=True)`

### Step C — Approval queue (SQLite)
- All content sits at `pending` until you approve
- Nothing posts automatically (unless `APPROVAL_REQUIRED=false`)

### Step D — Posting
- **Reddit** → PRAW via OAuth
- **Email** → Gmail SMTP
- **LinkedIn** → draft saved (manual post — LinkedIn API needs company page)

---

## Switching models

Change `OLLAMA_MODEL` in `.env` — no code changes needed:

```env
OLLAMA_MODEL=nous-hermes2             # hermes model weight via Ollama
OLLAMA_MODEL=gemma3:4b-it-qf4_K_M    # gemma3 4B (default)
OLLAMA_MODEL=gemma4:e4b               # gemma4
OLLAMA_MODEL=llama3.1                 # Meta Llama 3.1
```

---

## Scheduled jobs (automatic when `python main.py start`)

| Job | When | What |
|-----|------|------|
| Monitor sweep | Every 6h | Scans Reddit for GhostDesk / competitor mentions |
| Reddit draft | Tue + Fri 10am | Auto-drafts a Reddit post → pending queue |
| LinkedIn draft | Wed 11am | Auto-drafts a LinkedIn post → pending queue |
| Analytics report | Sun 9am | Weekly Razorpay sales summary |

Nothing posts until you approve it.

---

## Project structure

```
hermes-m/
├── main.py              # CLI entry point (typer)
├── agent.py             # Core pipeline: Ollama draft → LLM review → queue
├── chat_server.py       # FastAPI web server + HTML UI
├── config.py            # Settings loaded from .env (pydantic-settings)
├── memory.py            # SQLite: queue, chat history, monitor cache
├── scheduler_setup.py   # APScheduler cron jobs
├── tools/
│   ├── reddit.py        # PRAW Reddit posting
│   ├── email_tool.py    # Gmail SMTP campaigns
│   ├── linkedin.py      # LinkedIn draft helpers
│   ├── monitor.py       # Reddit mention monitoring
│   └── analytics.py     # Razorpay analytics reports
├── requirements.txt
├── .env.example         # Copy to .env and fill in your keys
└── agent.db             # Auto-created on first run (SQLite)
```

---

## Troubleshooting

### `ollama: connection refused`
Ollama isn't running. Open a new terminal and run:
```bash
ollama serve
```
Or just restart your PC — Ollama auto-starts on login.

### `DEEPSEEK_API_KEY is not set`
Make sure `.env` exists (not just `.env.example`) with the key set.

### PowerShell won't activate venv
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

### `praw.exceptions.OAuthException`
Your Reddit credentials in `.env` are wrong. Check `CLIENT_ID`, `CLIENT_SECRET`, `USERNAME`, `PASSWORD`. App type must be **script**.

### `SMTPAuthenticationError` (Gmail)
Use an **App Password**, not your Gmail password.  
Enable at: https://myaccount.google.com/apppasswords

### `ModuleNotFoundError`
Virtual environment not active, or deps not installed:
```bash
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Cost estimate (per month, typical usage)

| Component | Cost |
|-----------|------|
| Ollama (local drafts) | **$0** |
| DeepSeek Chat (~200 reviews) | **~$0.30** |
| OpenAI GPT-4o-mini (if used) | **~$0.60** |
| Reddit API | **Free** |
| Gmail SMTP | **Free** |

---

## License

MIT
