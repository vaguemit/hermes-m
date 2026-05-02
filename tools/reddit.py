"""
Reddit tool: monitor mentions + post to subreddits.
"""
import praw
from config import cfg
from memory import cache_monitor_item, log_posted, update_status, get_conn

MONITOR_TERMS = ["ghostdesk", "ghost-desk", "cluely", "interviewcoder", "interview coder"]
MONITOR_SUBS = ["developersIndia", "cscareerquestions", "learnprogramming", "artificial", "MachineLearning"]
POST_SUBS = {
    "developersIndia": True,
    "cscareerquestions": True,
    "learnprogramming": True,
    "artificial": True,
}


def _get_reddit():
    return praw.Reddit(
        client_id=cfg.reddit_client_id,
        client_secret=cfg.reddit_client_secret,
        username=cfg.reddit_username,
        password=cfg.reddit_password,
        user_agent=cfg.reddit_user_agent,
    )


def monitor_mentions() -> list[dict]:
    """Search recent Reddit posts/comments for GhostDesk and competitor mentions. Returns new items."""
    reddit = _get_reddit()
    found = []

    for term in MONITOR_TERMS:
        for sub in MONITOR_SUBS:
            try:
                subreddit = reddit.subreddit(sub)
                for post in subreddit.search(term, sort="new", time_filter="week", limit=10):
                    is_new = cache_monitor_item(
                        source="reddit",
                        item_id=f"post_{post.id}",
                        content=f"[{post.subreddit}] {post.title}\n{post.url}",
                    )
                    if is_new:
                        found.append({
                            "type": "post",
                            "id": post.id,
                            "subreddit": str(post.subreddit),
                            "title": post.title,
                            "url": f"https://reddit.com{post.permalink}",
                            "term": term,
                            "score": post.score,
                        })
            except Exception as e:
                print(f"[reddit monitor] {sub}/{term}: {e}")

    return found


def post_to_reddit(queue_item_id: int) -> bool:
    """
    Post an approved queue item to Reddit.
    metadata must have: subreddit, (optional) flair_id
    Content format: first line = title, rest = body (or just title for link posts).
    """
    from memory import get_conn, log_posted
    import json

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (queue_item_id,)).fetchone()

    if not row:
        print(f"[reddit] Queue item {queue_item_id} not found")
        return False

    meta = json.loads(row["metadata"] or "{}")
    subreddit_name = meta.get("subreddit", "developersIndia")
    content = row["content"]
    title = row["title"] or content.split("\n")[0][:300]
    body = content if "\n" in content else ""

    reddit = _get_reddit()
    try:
        sub = reddit.subreddit(subreddit_name)
        submission = sub.submit(title=title, selftext=body)
        log_posted("reddit_post", title, submission.id)
        update_status(queue_item_id, "posted")
        print(f"[reddit] Posted: https://reddit.com{submission.permalink}")
        return True
    except Exception as e:
        print(f"[reddit] Post failed: {e}")
        update_status(queue_item_id, "failed")
        return False
