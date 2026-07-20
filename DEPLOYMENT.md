# Dev Community Pulse Agent — Deployment Guide

## Prerequisites

### 1. AWS Account Setup

- An AWS account with access to:
  - AWS Lambda
  - Amazon Bedrock
  - Amazon SES
  - Amazon EventBridge

### 2. Enable Bedrock Model Access

1. Open the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** in the left sidebar
3. Click **Manage model access**
4. Enable **Amazon Nova Micro** (`amazon.nova-micro-v1:0`)
5. Submit and wait for access to be granted (usually instant)

### 3. Verify SES Email Identities

1. Open the [Amazon SES Console](https://console.aws.amazon.com/ses/)
2. Navigate to **Verified identities**
3. Click **Create identity**
4. Add both your **sender** and **recipient** email addresses
5. Check your inbox and click the verification link for each

> **Note:** New SES accounts are in sandbox mode — both sender and recipient must be verified. Request production access to send to any address.

### 4. Configure Your Interests

Edit `interest_config.json` before deploying:

```json
{
  "interests": ["aws", "serverless", "python", "ai", "llm"],
  "recipient_email": "your-verified-recipient@example.com",
  "sender_email": "your-verified-sender@example.com"
}
```

- **interests**: Keywords the AI uses to filter relevant content
- **recipient_email**: Where the daily digest is delivered
- **sender_email**: The "From" address (must be SES-verified)

---

## Deployment via AWS CloudShell

### Step 1: Upload Project

On your local machine, zip the project:

```bash
cd /path/to/ai-agent-app
zip -r pulse-agent.zip . -x ".venv/*" ".pytest_cache/*" "*__pycache__*" ".hypothesis/*" ".kiro/*"
```

Then in AWS Console:
1. Open **CloudShell**
2. Click **Actions → Upload file**
3. Upload `pulse-agent.zip`

### Step 2: Unzip and Enter Project

```bash
mkdir -p ~/pulse-agent && cd ~/pulse-agent
unzip -o ~/pulse-agent.zip
```

### Step 3: Adjust Runtime for CloudShell

CloudShell uses Python 3.13 and x86_64. Update the template:

```bash
sed -i 's/python3.12/python3.13/' template.yaml
sed -i 's/arm64/x86_64/' template.yaml
```

> **Note:** If deploying from a machine with Python 3.12, skip this step and keep `arm64` for cost savings.

### Step 4: Build

```bash
sam build
```

Expected output: `Build Succeeded`

### Step 5: Deploy

```bash
sam deploy --guided
```

When prompted:

| Prompt | Recommended Value |
|--------|-------------------|
| Stack Name | `dev-community-pulse-agent` |
| AWS Region | `us-east-1` |
| Confirm changes before deploy | `Y` |
| Allow SAM CLI IAM role creation | `Y` |
| Disable rollback | `N` |
| Save arguments to configuration file | `Y` |
| SAM configuration file | *(press Enter for default)* |
| SAM configuration environment | *(press Enter for default)* |

Wait for the CloudFormation stack to complete (1-2 minutes).

### Step 6: Test

```bash
# Get the deployed function name
FUNC_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name dev-community-pulse-agent \
  --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
  --output text)

# Invoke the function
aws lambda invoke --function-name $FUNC_NAME --payload '{}' response.json && cat response.json
```

Expected output:
```json
{"statusCode": 200, "body": "Digest sent with N posts"}
```

Check your recipient inbox for the digest email.

---

## Deployment via Local Machine (SAM CLI)

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configured with credentials
- Python 3.12+ installed
- Docker installed (for `--use-container` builds)

### Deploy

```bash
cd /path/to/ai-agent-app
sam build
sam deploy --guided
```

Or with container build (recommended for matching Lambda runtime exactly):

```bash
sam build --use-container
sam deploy --guided
```

---

## Post-Deployment

### Verify the Schedule

The function runs daily at 6:00 AM UTC. To check:

```bash
aws scheduler list-schedules --query "Schedules[?contains(Name, 'PulseAgent')]"
```

### View Logs

```bash
# Find the log group
aws logs describe-log-groups \
  --query "logGroups[?contains(logGroupName, 'PulseAgent')].logGroupName" \
  --output text

# Tail recent logs
aws logs tail /aws/lambda/FUNCTION_NAME --since 10m
```

### Update Configuration

To change interests or email addresses:

1. Edit `interest_config.json`
2. Rebuild and redeploy:
   ```bash
   sam build && sam deploy
   ```

### Change Schedule

Edit the `ScheduleExpression` in `template.yaml`:

```yaml
# Every weekday at 8 AM UTC:
ScheduleExpression: cron(0 8 ? * MON-FRI *)

# Every 12 hours:
ScheduleExpression: rate(12 hours)
```

Then redeploy: `sam build && sam deploy`

---

## Cleanup

To delete all resources:

```bash
sam delete --stack-name dev-community-pulse-agent
```

This removes the Lambda function, IAM role, EventBridge schedule, and CloudWatch log group.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `No posts fetched` | External APIs may be temporarily down. Check CloudWatch logs. |
| `No relevant posts` | Broaden your interests list in `interest_config.json` |
| SES "Email address not verified" | Verify both sender and recipient in SES Console |
| Bedrock "Access denied" | Enable Nova Micro model access in Bedrock Console |
| `sam build` fails with Python version | Use `--use-container` or match runtime to local Python |
| CloudShell arm64 image error | Switch to `x86_64` architecture in template.yaml |

---

## Cost Estimate (Daily Usage)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Lambda | 1 invocation/day, ~30s, 256MB | ~$0.00 (free tier) |
| EventBridge | 1 schedule | Free |
| Bedrock Nova Micro | ~4 calls × ~2K tokens | ~$0.001/day |
| SES | 1 email/day | ~$0.0001/day |
| **Total** | | **< $0.05/month** |
