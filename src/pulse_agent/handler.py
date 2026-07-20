import logging

from src.pulse_agent.config import load_config
from src.pulse_agent.fetchers import fetch_all_sources
from src.pulse_agent.summarizer import filter_and_summarize
from src.pulse_agent.email_composer import send_digest_email

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Lambda entry point - orchestrates the Dev Community Pulse pipeline.

    Pipeline: load config → fetch sources → filter/summarize → send email
    """
    config = load_config()

    posts = fetch_all_sources()
    if not posts:
        logger.info("All sources failed or returned no posts, skipping digest")
        return {"statusCode": 200, "body": "No posts fetched"}

    relevant_posts = filter_and_summarize(posts, config["interests"])
    if not relevant_posts:
        logger.info("No relevant content found, skipping email")
        return {"statusCode": 200, "body": "No relevant posts"}

    send_digest_email(relevant_posts, config)
    return {"statusCode": 200, "body": f"Digest sent with {len(relevant_posts)} posts"}
