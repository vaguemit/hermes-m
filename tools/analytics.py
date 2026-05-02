"""
Analytics tool: pull Razorpay revenue + Reddit engagement, generate weekly report.
"""
import razorpay
import json
from datetime import datetime, timedelta
from config import cfg, GHOSTDESK_CONTEXT
import anthropic
from memory import get_conn, enqueue

_claude = anthropic.Anthropic(api_key=cfg.anthropic_api_key)


def _razorpay_revenue(days: int = 7) -> dict:
    client = razorpay.Client(auth=(cfg.razorpay_key_id, cfg.razorpay_key_secret))
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    to_ts = int(datetime.now().timestamp())

    try:
        payments = client.payment.all({"from": from_ts, "to": to_ts, "count": 100})
        items = payments.get("items", [])
        captured = [p for p in items if p["status"] == "captured"]
        total = sum(p["amount"] for p in captured) / 100  # paise → rupees
        return {
            "total_inr": total,
            "count": len(captured),
            "avg": total / len(captured) if captured else 0,
        }
    except Exception as e:
        print(f"[analytics] Razorpay error: {e}")
        return {"error": str(e)}


def _reddit_engagement() -> dict:
    with get_conn() as conn:
        posts = conn.execute(
            "SELECT COUNT(*) as cnt FROM posted_log WHERE task_type = 'reddit_post' AND posted_at > datetime('now', '-7 days')"
        ).fetchone()
        mentions = conn.execute(
            "SELECT COUNT(*) as cnt FROM monitor_cache WHERE seen_at > datetime('now', '-7 days')"
        ).fetchone()
    return {
        "posts_this_week": posts["cnt"],
        "mentions_tracked": mentions["cnt"],
    }


def generate_analytics_report(days: int = 7) -> str:
    print("[analytics] Pulling data...")
    revenue = _razorpay_revenue(days)
    reddit = _reddit_engagement()

    raw = f"""
Period: last {days} days
Revenue (INR): ₹{revenue.get('total_inr', 'N/A')}
Payments captured: {revenue.get('count', 'N/A')}
Average payment: ₹{revenue.get('avg', 'N/A'):.0f}
Reddit posts published: {reddit['posts_this_week']}
Mentions/competitor terms tracked: {reddit['mentions_tracked']}
"""

    report = _claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=GHOSTDESK_CONTEXT,
        messages=[{
            "role": "user",
            "content": f"Generate a concise weekly analytics summary for GhostDesk with actionable insights:\n{raw}"
        }]
    ).content[0].text

    timestamp = datetime.now().strftime("%Y-%m-%d")
    full = f"# Analytics Report — {timestamp}\n\n{report}\n\n---\n**Raw data:**\n```\n{raw}\n```"

    enqueue("analytics", full, title=f"Analytics {timestamp}", metadata={"auto": True})
    print("[analytics] Report generated and queued")
    return full
