import json
import logging
import boto3

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = "amazon.nova-micro-v1:0"


def filter_and_summarize(posts: list[dict], interests: list[str]) -> list[dict]:
    """Filter posts by relevance and generate summaries using Bedrock."""
    client = boto3.client("bedrock-runtime")

    # Group posts by source for batched processing
    posts_by_source = {}
    for post in posts:
        source = post["source"]
        posts_by_source.setdefault(source, []).append(post)

    relevant_posts = []
    for source, source_posts in posts_by_source.items():
        prompt = _build_prompt(source_posts, interests)
        response = _invoke_bedrock(client, prompt)
        filtered = _parse_response(response, source_posts)
        relevant_posts.extend(filtered)

    return relevant_posts


def _build_prompt(posts: list[dict], interests: list[str]) -> str:
    """Build the prompt for Bedrock to filter and summarize posts."""
    posts_text = "\n".join(
        f"[{i}] {p['title']} - {p['url']}" for i, p in enumerate(posts)
    )
    interests_text = ", ".join(interests)

    return f"""You are a content curator. Given the following posts and user interests, identify which posts are relevant and provide a 2-3 sentence summary for each relevant post.

User interests: {interests_text}

Posts:
{posts_text}

Respond in JSON format:
[{{"index": 0, "relevant": true, "summary": "..."}}]

Only include posts in the response. Mark irrelevant posts with "relevant": false."""


def _invoke_bedrock(client, prompt: str) -> str:
    """Call Amazon Bedrock with the given prompt."""
    response = client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 4096, "temperature": 0.2},
        }),
    )
    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"]


def _parse_response(response_text: str, source_posts: list[dict]) -> list[dict]:
    """Parse Bedrock response and attach summaries to relevant posts."""
    try:
        # Extract JSON from response (may be wrapped in markdown code block)
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]

        results = json.loads(text)
        relevant = []
        for item in results:
            if item.get("relevant") and item.get("index") is not None:
                idx = item["index"]
                if 0 <= idx < len(source_posts):
                    post = source_posts[idx].copy()
                    post["summary"] = item.get("summary", "")
                    relevant.append(post)
        return relevant
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse Bedrock response: {e}")
        return []
