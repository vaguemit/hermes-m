"""
LinkedIn tool: draft-only. LinkedIn's API requires app review for posting.
Drafts are queued for your manual review + post.
"""
from memory import enqueue


def queue_linkedin_draft(content: str, title: str = "") -> int:
    """Queue a LinkedIn post draft for manual review and posting."""
    return enqueue(
        task_type="linkedin_draft",
        content=content,
        title=title or "LinkedIn Post",
        metadata={"note": "Manual post required — copy content to LinkedIn"},
    )


LINKEDIN_PROMPT_TEMPLATE = """
Write a LinkedIn post for GhostDesk.
Topic: {topic}
Tone: Professional but direct. Dev-native. Not cringe corporate speak.
Length: 150-250 words
Include: 3-5 relevant hashtags at the end
Hook: Strong first line that stops the scroll
CTA: Visit ghost-desk.app or comment for more info
"""


def draft_prompt(topic: str) -> str:
    return LINKEDIN_PROMPT_TEMPLATE.format(topic=topic)
