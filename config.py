from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    # --- Local LLM (fast drafts) ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b-it-qf4_K_M"  # gemma4:e4b also works

    # --- Quality-review LLM (heavy tasks) ---
    # Set REVIEW_PROVIDER=openai or deepseek in your .env
    review_provider: Literal["openai", "deepseek"] = "deepseek"
    openai_api_key: Optional[str] = None          # needed if review_provider=openai
    openai_model: str = "gpt-4o-mini"             # swap to gpt-4o for max quality
    deepseek_api_key: Optional[str] = None        # needed if review_provider=deepseek
    deepseek_model: str = "deepseek-chat"         # deepseek-reasoner for CoT

    # Reddit
    reddit_client_id: str
    reddit_client_secret: str
    reddit_username: str
    reddit_password: str
    reddit_user_agent: str = "GhostDeskAgent/1.0"

    # Gmail
    gmail_address: str
    gmail_app_password: str

    # Razorpay
    razorpay_key_id: str
    razorpay_key_secret: str

    # Agent
    approval_required: bool = True
    chat_port: int = 8765
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


cfg = Settings()

# GhostDesk context injected into every prompt
GHOSTDESK_CONTEXT = """
You are the marketing agent for GhostDesk (ghost-desk.app).

Product: GhostDesk is a Windows AI overlay that's completely invisible during screen sharing 
and recordings via Win32 SetWindowDisplayAffinity. It uses DeepSeek V3, DeepSeek R1, 
Deepgram Nova-3 voice, and Llama Scout. Built for developers, students, and professionals 
who want an AI assistant that can't be caught on screen.

Pricing (India): ₹799/mo, ₹1,799/3mo, ₹2,999/6mo via Razorpay
Pricing (International): $9.99/mo, $21.99/3mo, $34.99/6mo via Stripe

Target audience: Developers, CS students, job seekers (coding interviews), 
competitive programmers, anyone who needs a discreet AI assistant.

Competitors: Cluely, InterviewCoder
Key differentiator: True OS-level invisibility, not just browser-based. 
Native Windows app, voice input, multiple LLM backends.

Tone: Direct, slightly edgy, dev-community native. Not corporate. 
Use r/developersIndia style language for Indian audience.
Subreddits we post to: r/developersIndia, r/InterviewCoder, r/cscareerquestions, 
r/learnprogramming, r/artificial
"""
