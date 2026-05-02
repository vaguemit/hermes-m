"""
Core agent: Ollama (gemma3:4b) → draft → OpenAI / DeepSeek → quality review → queue
Switch REVIEW_PROVIDER in .env to toggle between 'openai' and 'deepseek'.
"""
import json
import ollama
from openai import OpenAI
from config import cfg, GHOSTDESK_CONTEXT
from memory import enqueue, add_chat_message, get_chat_history


# ---------------------------------------------------------------------------
# Review client — built once at import time based on REVIEW_PROVIDER setting
# ---------------------------------------------------------------------------
def _build_review_client() -> OpenAI:
    """
    Both OpenAI and DeepSeek expose an OpenAI-compatible API, so we use the
    same openai.OpenAI client for both — just swap the base_url + api_key.
    """
    if cfg.review_provider == "deepseek":
        if not cfg.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set in .env")
        return OpenAI(
            api_key=cfg.deepseek_api_key,
            base_url="https://api.deepseek.com/v1",
        )
    else:  # openai
        if not cfg.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        return OpenAI(api_key=cfg.openai_api_key)


_review_client = _build_review_client()


def _review_model() -> str:
    """Returns the correct model name for the active review provider."""
    return cfg.deepseek_model if cfg.review_provider == "deepseek" else cfg.openai_model


# ---------------------------------------------------------------------------
# Draft step — local Ollama (gemma3:4b / gemma4:e4b)
# ---------------------------------------------------------------------------
def _ollama_draft(prompt: str) -> str:
    """Local Gemma draft — fast, free, private."""
    resp = ollama.chat(
        model=cfg.ollama_model,
        messages=[
            {
                "role": "system",
                "content": (
                    GHOSTDESK_CONTEXT
                    + "\n\nDraft the requested marketing content. "
                    "Be raw and direct — it will be refined next."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return resp["message"]["content"]


# ---------------------------------------------------------------------------
# Review step — OpenAI or DeepSeek (pluggable)
# ---------------------------------------------------------------------------
def _llm_review(draft: str, task_type: str, requirements: str = "") -> str:
    """Quality-review the Ollama draft using the configured provider."""
    system = (
        f"{GHOSTDESK_CONTEXT}\n\n"
        "You are reviewing and refining a marketing draft. "
        "Improve clarity, tone, and effectiveness.\n"
        f"Task type: {task_type}\n"
        + (f"Additional requirements: {requirements}\n" if requirements else "")
        + "\nReturn ONLY the refined content, no commentary."
    )

    resp = _review_client.chat.completions.create(
        model=_review_model(),
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Refine this draft:\n\n{draft}"},
        ],
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_and_queue(
    task_type: str,
    prompt: str,
    title: str = "",
    metadata: dict = None,
    requirements: str = "",
    skip_review: bool = False,
) -> dict:
    """
    Full pipeline: Gemma draft → (optional) review → enqueue for approval.
    Returns the queued item info.
    """
    print(f"[agent] Drafting with {cfg.ollama_model}...")
    draft = _ollama_draft(prompt)

    if skip_review:
        final = draft
    else:
        print(f"[agent] Sending to {cfg.review_provider} ({_review_model()}) for review...")
        final = _llm_review(draft, task_type, requirements)

    item_id = enqueue(task_type, final, title=title, metadata=metadata or {})
    print(f"[agent] Queued as #{item_id} (status: pending approval)")

    return {"id": item_id, "task_type": task_type, "title": title, "content": final}


def chat(user_message: str) -> str:
    """
    On-demand chat — handles free-form marketing requests.
    Uses the review LLM with full context + conversation history.
    """
    add_chat_message("user", user_message)
    history = get_chat_history(limit=20)

    system = f"""{GHOSTDESK_CONTEXT}

You are the GhostDesk marketing agent. You can:
- Draft Reddit posts (task_type: reddit_post) for subreddits like r/developersIndia
- Draft LinkedIn posts (task_type: linkedin_draft)
- Draft email campaigns (task_type: email)
- Generate analytics reports (task_type: analytics)
- Monitor competitor mentions (task_type: monitor)

When the user asks you to create content, respond with the content AND a JSON block at the end like:
<queue>
{{"task_type": "reddit_post", "title": "post title", "metadata": {{"subreddit": "developersIndia"}}}}
</queue>

Otherwise just respond conversationally."""

    messages = [{"role": "system", "content": system}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]

    resp = _review_client.chat.completions.create(
        model=_review_model(),
        max_tokens=1024,
        messages=messages,
    )
    reply = resp.choices[0].message.content

    # Parse and queue if agent returned a <queue> block
    if "<queue>" in reply and "</queue>" in reply:
        content_part = reply[: reply.index("<queue>")].strip()
        json_part = reply[reply.index("<queue>") + 7 : reply.index("</queue>")].strip()
        try:
            meta = json.loads(json_part)
            item_id = enqueue(
                task_type=meta.get("task_type", "generic"),
                content=content_part,
                title=meta.get("title", ""),
                metadata=meta.get("metadata", {}),
            )
            reply = content_part + f"\n\n✅ Queued as **#{item_id}** — approve with `/approve {item_id}`"
        except json.JSONDecodeError:
            pass

    add_chat_message("assistant", reply)
    return reply
