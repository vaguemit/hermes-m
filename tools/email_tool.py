"""
Email tool: send campaigns via Gmail SMTP.
metadata: { recipients: [...], subject: "..." }
"""
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import cfg
from memory import get_conn, log_posted, update_status


def send_campaign(queue_item_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (queue_item_id,)).fetchone()

    if not row:
        return False

    meta = json.loads(row["metadata"] or "{}")
    recipients = meta.get("recipients", [])
    subject = meta.get("subject", row["title"] or "GhostDesk Update")
    body_html = row["content"]

    if not recipients:
        print("[email] No recipients in metadata")
        return False

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(cfg.gmail_address, cfg.gmail_app_password)

            sent_count = 0
            for recipient in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"GhostDesk <{cfg.gmail_address}>"
                msg["To"] = recipient
                msg.attach(MIMEText(body_html, "html"))
                smtp.sendmail(cfg.gmail_address, recipient, msg.as_string())
                sent_count += 1

        log_posted("email", subject, f"sent_to_{sent_count}")
        update_status(queue_item_id, "posted")
        print(f"[email] Sent to {sent_count} recipients")
        return True

    except Exception as e:
        print(f"[email] Failed: {e}")
        update_status(queue_item_id, "failed")
        return False


def draft_campaign_prompt(goal: str, recipients_desc: str = "GhostDesk waitlist/users") -> str:
    """Returns prompt for agent to draft an email campaign."""
    return f"""
Write an HTML email campaign for GhostDesk.
Goal: {goal}
Recipients: {recipients_desc}

Format:
- Subject line on first line (prefixed with "Subject: ")
- Then the full HTML email body
- Keep it under 300 words
- Include a clear CTA button linking to https://ghost-desk.app
- Mobile-friendly, minimal design
- Mention current promo code GHOST25 if relevant
"""
