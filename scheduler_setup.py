"""
Scheduler: APScheduler jobs for automated GhostDesk marketing tasks.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


def job_monitor():
    """Every 6h: scan Reddit for mentions + competitor activity."""
    from tools.monitor import run_monitor
    print("[scheduler] Running monitor sweep...")
    run_monitor()


def job_analytics():
    """Every Sunday 9am: generate weekly analytics report."""
    from tools.analytics import generate_analytics_report
    print("[scheduler] Generating weekly analytics...")
    generate_analytics_report(days=7)


def job_reddit_content():
    """Every Tuesday + Friday: draft a Reddit post for review."""
    from agent import generate_and_queue
    import random

    prompts = [
        "Write a Reddit post for r/developersIndia showing how GhostDesk helps developers stay productive with AI without screen-share concerns. Be conversational, not salesy. Share a relatable scenario.",
        "Write a Reddit post for r/cscareerquestions about using AI tools discreetly during coding interviews. Mention GhostDesk naturally as a solution. Follow community tone — be helpful first.",
        "Write a Reddit post for r/learnprogramming about AI-assisted learning. Mention GhostDesk as a tool students are using. Keep it educational, not promotional.",
        "Write a 'Show HN'-style Reddit post for r/developersIndia introducing GhostDesk 2.0. Include: what it does, how it works technically (SetWindowDisplayAffinity), pricing, and invite feedback.",
    ]

    subreddits = ["developersIndia", "cscareerquestions", "learnprogramming"]
    prompt = random.choice(prompts)
    sub = random.choice(subreddits)

    generate_and_queue(
        task_type="reddit_post",
        prompt=prompt,
        title=f"[Auto-drafted] Reddit post for r/{sub}",
        metadata={"subreddit": sub},
    )


def job_linkedin_content():
    """Every Wednesday: draft a LinkedIn post for review."""
    from agent import generate_and_queue
    from tools.linkedin import draft_prompt
    import random

    topics = [
        "Why developers are choosing invisible AI overlays over browser extensions",
        "GhostDesk 2.0 launch — what we built and why it's different from Cluely",
        "The ethics of AI assistance tools in professional settings",
        "How competitive programmers use AI to level up their problem-solving",
    ]

    topic = random.choice(topics)
    generate_and_queue(
        task_type="linkedin_draft",
        prompt=draft_prompt(topic),
        title=f"[Auto-drafted] LinkedIn: {topic[:60]}...",
        metadata={"topic": topic},
    )


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    # Monitor: every 6 hours
    scheduler.add_job(job_monitor, IntervalTrigger(hours=6), id="monitor", replace_existing=True)

    # Analytics: every Sunday at 9am
    scheduler.add_job(job_analytics, CronTrigger(day_of_week="sun", hour=9), id="analytics", replace_existing=True)

    # Reddit drafts: Tuesday and Friday at 10am
    scheduler.add_job(job_reddit_content, CronTrigger(day_of_week="tue,fri", hour=10), id="reddit_draft", replace_existing=True)

    # LinkedIn drafts: Wednesday at 11am
    scheduler.add_job(job_linkedin_content, CronTrigger(day_of_week="wed", hour=11), id="linkedin_draft", replace_existing=True)

    return scheduler
