"""
Monitor tool: track GhostDesk mentions, competitor activity, generate reports.
"""
import httpx
from datetime import datetime
from config import cfg, GHOSTDESK_CONTEXT
import anthropic
from tools.reddit import monitor_mentions
from memory import get_conn

_claude = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

COMPETITOR_SUBREDDITS = ["developersIndia", "cscareerquestions"]
COMPETITORS = ["cluely", "interviewcoder"]


def run_monitor() -> str:
    """Full monitoring sweep. Returns a markdown report string."""
    print("[monitor] Running sweep...")

    # Reddit mentions
    reddit_mentions = monitor_mentions()

    # Pull recent cache for report context
    with get_conn() as conn:
        recent = conn.execute(
            "SELECT * FROM monitor_cache ORDER BY seen_at DESC LIMIT 30"
        ).fetchall()
    recent_data = [dict(r) for r in recent]

    # Generate report via Claude
    context = f"""
New mentions found this sweep: {len(reddit_mentions)}
New items:
{chr(10).join([f"- [{m['subreddit']}] {m['title']} ({m['url']})" for m in reddit_mentions]) or "None"}

Recent 30 cached mentions summary:
{chr(10).join([f"- [{r['source']}] {r['content'][:100]}" for r in recent_data[:10]])}
"""

    report = _claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=GHOSTDESK_CONTEXT + "\n\nYou are generating a monitoring report for the GhostDesk marketing agent.",
        messages=[{
            "role": "user",
            "content": f"Generate a concise marketing intelligence report based on this data:\n{context}\n\nInclude: competitor activity, relevant threads we should engage with, sentiment summary, recommended actions."
        }]
    ).content[0].text

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    full_report = f"# Monitor Report — {timestamp}\n\n{report}"

    # Save report to queue as FYI (no approval needed)
    from memory import enqueue
    enqueue("monitor_report", full_report, title=f"Monitor Report {timestamp}", metadata={"auto": True})

    print(f"[monitor] Done. {len(reddit_mentions)} new mentions.")
    return full_report
