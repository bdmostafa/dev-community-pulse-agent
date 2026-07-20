import logging
from datetime import datetime, timezone
import boto3

logger = logging.getLogger(__name__)


def send_digest_email(posts: list[dict], config: dict) -> None:
    """Compose and send the HTML digest email via SES."""
    html_body = compose_html(posts)
    subject = f"Dev Community Pulse - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    ses_client = boto3.client("ses")
    try:
        ses_client.send_email(
            Source=config["sender_email"],
            Destination={"ToAddresses": [config["recipient_email"]]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        logger.info("Digest email sent successfully")
    except Exception as e:
        logger.error(f"SES delivery failed: {e}")


def compose_html(posts: list[dict]) -> str:
    """Compose the HTML body with per-source sections."""
    posts_by_source: dict[str, list[dict]] = {}
    for post in posts:
        source = post["source"]
        posts_by_source.setdefault(source, []).append(post)

    sections = []
    for source, source_posts in posts_by_source.items():
        items_html = "".join(
            f'<li><strong><a href="{p["url"]}">{p["title"]}</a></strong>'
            f'<p>{p["summary"]}</p></li>'
            for p in source_posts
        )
        sections.append(f"<h2>{source}</h2><ul>{items_html}</ul>")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
<h1>Dev Community Pulse</h1>
{"".join(sections)}
</body>
</html>"""
