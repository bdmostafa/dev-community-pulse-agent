# Dev Community Pulse Agent

An AI-powered serverless agent that runs autonomously every morning, scans 110+ posts from developer communities, filters them by your interests using Amazon Bedrock, and delivers a curated HTML digest to your inbox — before you even wake up.

Built for the [AWS Builder Center Weekend Agent Challenge](https://builder.aws.com/).

---

## What It Does

- Triggers daily at 6:00 AM UTC via Amazon EventBridge Scheduler
- Fetches posts from **Hacker News** (top 30), **Dev.to** (30 articles), **Reddit r/aws** (25 posts), and **Reddit r/programming** (25 posts)
- Uses **Amazon Bedrock (Nova Micro)** to filter relevance and generate 2-3 sentence summaries
- Sends a clean **HTML email digest** via Amazon SES, organized by source with clickable links
- Requires zero manual intervention after deployment

---

## Architecture

```
EventBridge Scheduler (cron: 0 6 * * ? *)
        |
        v
+----------------------------------------------+
|            Lambda: PulseAgent                 |
|                                              |
|  1. Load Config (interest_config.json)       |
|  2. Fetch Sources (HN, Dev.to, Reddit x2)   |
|  3. Filter & Summarize (Bedrock Nova Micro)  |
|  4. Compose & Send Email (SES)              |
+----------------------------------------------+
        |                    |
        v                    v
  Amazon Bedrock       Amazon SES
  (Nova Micro)         (HTML Email)
```

## AWS Services

| Service | Purpose |
|---------|---------|
| AWS Lambda | Runs the agent pipeline (Python 3.12, arm64) |
| Amazon EventBridge Scheduler | Daily cron trigger at 6 AM UTC |
| Amazon Bedrock (Nova Micro) | AI-powered content filtering and summarization |
| Amazon SES | HTML email delivery |

All services operate within **AWS Free Tier** limits for this workload.

---

## Project Structure

```
.
├── template.yaml              # AWS SAM infrastructure template
├── interest_config.json       # Your interests and email config
├── requirements.txt           # Python dependencies
├── src/
│   └── pulse_agent/
│       ├── __init__.py
│       ├── handler.py         # Lambda entry point (pipeline orchestrator)
│       ├── config.py          # Config loader & validator
│       ├── fetchers.py        # Content fetchers (HN, Dev.to, Reddit)
│       ├── summarizer.py      # Bedrock AI filtering & summarization
│       └── email_composer.py  # HTML email builder & SES sender
└── tests/
    ├── unit/                  # Unit tests
    └── property/              # Property-based tests
```

---

## Quick Start

### Prerequisites

- AWS account with [Bedrock model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) enabled for Amazon Nova Micro
- Both sender and recipient email addresses verified in [Amazon SES](https://docs.aws.amazon.com/ses/latest/dg/verify-email-addresses.html)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- Python 3.12

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/dev-community-pulse-agent.git
cd dev-community-pulse-agent
```

### 2. Configure Your Interests

Edit `interest_config.json`:

```json
{
  "interests": ["aws", "serverless", "python", "ai", "llm", "bedrock", "automation"],
  "recipient_email": "your-verified-email@example.com",
  "sender_email": "your-verified-sender@example.com"
}
```

### 3. Build and Deploy

```bash
sam build
sam deploy --guided
```

Follow the prompts. The stack creates the Lambda function, EventBridge schedule, and IAM permissions automatically.

### 4. Done

The agent will run tomorrow at 6:00 AM UTC. To test immediately:

```bash
aws lambda invoke --function-name <YourFunctionName> output.json
```

---

## Configuration

| Field | Description |
|-------|-------------|
| `interests` | List of topic keywords the AI uses to filter relevant posts |
| `recipient_email` | Where the digest email is sent (must be SES-verified) |
| `sender_email` | The "From" address for the email (must be SES-verified) |

---

## How It Works

1. **EventBridge Scheduler** fires the Lambda at 6 AM UTC daily
2. **Fetchers** pull posts from all four sources in parallel-safe fashion (failures in one source don't stop others)
3. **Bedrock Summarizer** groups posts by source, sends one prompt per batch, and returns only relevant posts with AI-generated summaries
4. **Email Composer** builds an HTML email with per-source sections and sends via SES
5. If no posts are fetched or nothing is relevant, the agent skips the email silently

---

## Key Design Decisions

- **No external HTTP libraries** — Uses Python stdlib `urllib.request` to minimize cold start and deployment size
- **Batched Bedrock calls** — One API call per source (4 total), not one per post (110+)
- **Graceful degradation** — Individual source failures are logged and skipped, not fatal
- **Stateless** — No database, no stored state. Every run is independent
- **Arm64 Lambda** — 20% cheaper than x86_64 for the same workload

---

## Customization

**Add more sources:** Add a new fetcher function in `src/pulse_agent/fetchers.py` and register it in the `fetch_all_sources()` list.

**Change the schedule:** Edit the `ScheduleExpression` in `template.yaml`:
```yaml
ScheduleExpression: cron(0 8 * * ? *)  # 8 AM UTC instead
```

**Change the AI model:** Update `BEDROCK_MODEL_ID` in `src/pulse_agent/summarizer.py`:
```python
BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"  # or another supported model
```

---

## Security

- Lambda has minimal IAM permissions: only `bedrock:InvokeModel` and `ses:SendEmail`
- No secrets stored in code — SES identity verification is done via AWS Console
- All external API calls use HTTPS
- No user data is stored or persisted between invocations

---

## License

MIT

---

## Author

**Md. Mostafa Al Mahmud**

Built for the AWS Builder Center Weekend Agent Challenge, July 2026.
