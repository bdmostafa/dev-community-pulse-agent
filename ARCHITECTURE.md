# Dev Community Pulse Agent — Architecture

## Overview

The Dev Community Pulse Agent is a serverless application that automatically curates and delivers a daily digest of developer community content filtered by your interests. It runs entirely on AWS with zero infrastructure to manage.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                     │
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────────────────────┐  │
│  │  EventBridge      │         │  Lambda Function                  │  │
│  │  Scheduler        │────────▶│  (PulseAgentFunction)             │  │
│  │                   │         │                                    │  │
│  │  cron(0 6 * * ? *)│         │  ┌────────────────────────────┐  │  │
│  └──────────────────┘         │  │  Pipeline Steps:            │  │  │
│                                │  │                             │  │  │
│                                │  │  1. Load Config             │  │  │
│                                │  │  2. Fetch Sources ─────────────────┐
│                                │  │  3. Filter & Summarize     │  │  ││
│                                │  │  4. Compose & Send Email   │  │  ││
│                                │  └────────────────────────────┘  │  ││
│                                └───────────┬───────────┬──────────┘  ││
│                                            │           │              ││
│                                            ▼           ▼              ││
│                               ┌────────────────┐ ┌──────────┐       ││
│                               │ Amazon Bedrock  │ │ Amazon   │       ││
│                               │ (Nova Micro)    │ │ SES      │       ││
│                               │                 │ │          │       ││
│                               │ Filters posts   │ │ Sends    │       ││
│                               │ by relevance &  │ │ HTML     │       ││
│                               │ generates       │ │ digest   │       ││
│                               │ summaries       │ │ email    │       ││
│                               └────────────────┘ └──────────┘       ││
└──────────────────────────────────────────────────────────────────────┘│
                                                                        │
┌───────────────────────────────────────────────────────────────────────┘
│  External APIs (Public Internet)
│
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐
│  │  Hacker News   │  │  Dev.to        │  │  Reddit                │
│  │  API           │  │  API           │  │  (r/aws, r/programming)│
│  │  (Top 30)      │  │  (30 articles) │  │  (25 posts each)      │
│  └────────────────┘  └────────────────┘  └────────────────────────┘
```

## Component Flow

```
EventBridge ──▶ Lambda Handler
                    │
                    ├── 1. config.load_config()
                    │       └── Reads interest_config.json (bundled in deployment)
                    │
                    ├── 2. fetchers.fetch_all_sources()
                    │       ├── fetch_hackernews()     → HN API
                    │       ├── fetch_devto()          → Dev.to API
                    │       ├── fetch_reddit_aws()     → Reddit API
                    │       └── fetch_reddit_programming() → Reddit API
                    │       (failures are caught per-source, pipeline continues)
                    │
                    ├── 3. summarizer.filter_and_summarize()
                    │       ├── Groups posts by source
                    │       ├── Sends one Bedrock call per source batch
                    │       └── Returns only relevant posts with AI summaries
                    │
                    └── 4. email_composer.send_digest_email()
                            ├── compose_html() → builds per-source HTML sections
                            └── SES send_email() → delivers to recipient
```

## AWS Services Used

| Service | Purpose | Pricing Model |
|---------|---------|---------------|
| **AWS Lambda** | Runs the agent pipeline | Pay per invocation (~1 per day) |
| **Amazon EventBridge Scheduler** | Triggers daily at 6:00 AM UTC | Free tier covers this |
| **Amazon Bedrock (Nova Micro)** | Filters content by relevance & generates summaries | Pay per input/output token |
| **Amazon SES** | Sends the HTML digest email | $0.10 per 1,000 emails |

## Data Sources

| Source | Endpoint | Posts Fetched |
|--------|----------|---------------|
| Hacker News | `hacker-news.firebaseio.com/v0/topstories.json` | Top 30 stories |
| Dev.to | `dev.to/api/articles?per_page=30` | 30 recent articles |
| Reddit r/aws | `reddit.com/r/aws/hot.json?limit=25` | 25 hot posts |
| Reddit r/programming | `reddit.com/r/programming/hot.json?limit=25` | 25 hot posts |

## Key Design Decisions

1. **No external dependencies for HTTP** — Uses Python stdlib `urllib.request` to avoid dependency bloat
2. **One Bedrock call per source** — Batches posts by source to minimize API calls while keeping prompts focused
3. **Graceful degradation** — If any source fails, the pipeline continues with remaining sources
4. **Bundled config** — `interest_config.json` is packaged with the Lambda, no external config service needed
5. **Arm64 architecture** — 20% cost savings over x86_64 (switch to x86_64 if building on CloudShell)

## Project Structure

```
.
├── interest_config.json          # User interests and email config
├── requirements.txt              # Python dependencies (boto3)
├── template.yaml                 # AWS SAM infrastructure template
├── src/
│   └── pulse_agent/
│       ├── __init__.py
│       ├── config.py             # Config loader & validator
│       ├── fetchers.py           # HTTP fetchers for all sources
│       ├── summarizer.py         # Bedrock AI filtering & summarization
│       ├── email_composer.py     # HTML email builder & SES sender
│       └── handler.py           # Lambda entry point (pipeline orchestrator)
└── tests/
    ├── unit/                     # Unit tests (mocked dependencies)
    └── property/                 # Property-based tests (Hypothesis)
```

## Security

- Lambda has minimal IAM permissions: only `bedrock:InvokeModel` and `ses:SendEmail`
- No secrets stored in code — SES identity verification is done via AWS Console
- All external API calls use HTTPS
- No user data is stored or persisted between invocations
