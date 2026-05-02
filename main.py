"""
main.py — GhostDesk Marketing Agent entry point.

Usage:
  python main.py start          # start scheduler + web UI
  python main.py queue          # view pending queue (CLI)
  python main.py approve <id>   # approve and post
  python main.py reject <id>    # reject
  python main.py chat           # interactive CLI chat
  python main.py monitor        # run monitor sweep now
  python main.py analytics      # generate analytics report now
  python main.py draft reddit   # draft a Reddit post now
  python main.py draft linkedin # draft a LinkedIn post now
"""
import sys
import time
import uvicorn
import typer
from rich import print as rprint
from rich.table import Table
from rich.console import Console
from memory import get_pending, update_status
from scheduler_setup import create_scheduler
from tools.reddit import post_to_reddit
from tools.email_tool import send_campaign

app_cli = typer.Typer()
console = Console()


@app_cli.command()
def start(port: int = typer.Option(8765, help="Web UI port")):
    """Start scheduler + web UI."""
    scheduler = create_scheduler()
    scheduler.start()
    rprint(f"[bold green]✓ Scheduler started[/bold green] — {len(scheduler.get_jobs())} jobs")
    for job in scheduler.get_jobs():
        rprint(f"  • {job.id} → next run: {job.next_run_time}")

    rprint(f"\n[bold purple]⚡ Web UI:[/bold purple] http://localhost:{port}\n")

    # Run monitor immediately on start
    from tools.monitor import run_monitor
    rprint("[dim]Running initial monitor sweep...[/dim]")
    run_monitor()

    uvicorn.run("chat_server:app", host="0.0.0.0", port=port, log_level="warning")


@app_cli.command()
def queue():
    """View pending approval queue."""
    items = get_pending()
    if not items:
        rprint("[dim]Queue is empty[/dim]")
        return

    table = Table(title="Pending Approvals")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Type", style="magenta", width=16)
    table.add_column("Title", width=40)
    table.add_column("Created", width=16)

    for item in items:
        table.add_row(str(item["id"]), item["task_type"], item["title"][:40], item["created_at"][:16])

    console.print(table)


@app_cli.command()
def approve(item_id: int):
    """Approve and post a queue item."""
    from memory import get_conn
    import json

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (item_id,)).fetchone()

    if not row:
        rprint(f"[red]Item {item_id} not found[/red]")
        raise typer.Exit(1)

    task_type = row["task_type"]
    rprint(f"[yellow]Approving #{item_id} ({task_type})...[/yellow]")

    if task_type == "reddit_post":
        ok = post_to_reddit(item_id)
    elif task_type == "email":
        ok = send_campaign(item_id)
    else:
        update_status(item_id, "approved")
        ok = True

    if ok:
        rprint(f"[green]✓ Done[/green]")
    else:
        rprint(f"[red]✗ Failed — check logs[/red]")


@app_cli.command()
def reject(item_id: int):
    """Reject a queue item."""
    update_status(item_id, "rejected")
    rprint(f"[dim]Rejected #{item_id}[/dim]")


@app_cli.command()
def monitor():
    """Run a monitor sweep now."""
    from tools.monitor import run_monitor
    report = run_monitor()
    rprint(report)


@app_cli.command()
def analytics():
    """Generate analytics report now."""
    from tools.analytics import generate_analytics_report
    report = generate_analytics_report()
    rprint(report)


@app_cli.command()
def draft(content_type: str = typer.Argument(..., help="reddit | linkedin | email")):
    """Draft content now and queue for approval."""
    from agent import generate_and_queue
    from tools.linkedin import draft_prompt

    if content_type == "reddit":
        topic = typer.prompt("Topic/angle for the Reddit post")
        sub = typer.prompt("Subreddit", default="developersIndia")
        generate_and_queue(
            task_type="reddit_post",
            prompt=f"Write a Reddit post for r/{sub} about: {topic}",
            title=f"Reddit: {topic[:50]}",
            metadata={"subreddit": sub},
        )
    elif content_type == "linkedin":
        topic = typer.prompt("Topic for the LinkedIn post")
        generate_and_queue(
            task_type="linkedin_draft",
            prompt=draft_prompt(topic),
            title=f"LinkedIn: {topic[:50]}",
            metadata={},
        )
    elif content_type == "email":
        goal = typer.prompt("Email campaign goal")
        recipients_raw = typer.prompt("Recipients (comma-separated emails)")
        recipients = [r.strip() for r in recipients_raw.split(",")]
        from tools.email_tool import draft_campaign_prompt
        generate_and_queue(
            task_type="email",
            prompt=draft_campaign_prompt(goal),
            title=f"Email: {goal[:50]}",
            metadata={"recipients": recipients, "subject": goal},
        )
    else:
        rprint(f"[red]Unknown type: {content_type}. Use: reddit | linkedin | email[/red]")


@app_cli.command()
def chat():
    """Interactive CLI chat with the agent."""
    from agent import chat as agent_chat
    rprint("[bold purple]GhostDesk Agent[/bold purple] — type 'exit' to quit\n")
    while True:
        try:
            msg = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if msg.lower() in ("exit", "quit"):
            break
        if not msg:
            continue
        reply = agent_chat(msg)
        rprint(f"[purple]Agent:[/purple] {reply}\n")


if __name__ == "__main__":
    app_cli()
