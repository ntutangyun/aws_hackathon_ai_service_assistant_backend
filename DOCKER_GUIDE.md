# Docker Deployment Guide

## Quick Start

### Option 1: Automated Script (Recommended)

```bash
cd backend

# Make script executable
chmod +x build-and-deploy-docker.sh

# Run the script
./build-and-deploy-docker.sh
```

This script will:
1. Create ECR repository (if needed)
2. Build Docker image
3. Push to ECR
4. Provide next steps for App Runner deployment

### Option 2: Manual Steps

Follow the steps below for manual control.

---

## Step-by-Step Manual Deployment

### 1. Build Docker Image Locally

```bash
cd backend

# Build the image
docker build -t ai-service-assistant-backend .
```

### 2. Test Locally (Optional but Recommended)

```bash
# Run the container locally
docker run -p 8000:8000 \
  -e AWS_REGION=us-east-1 \
  -e AGENT_NAME=oran_agent \
  -e CORS_ORIGINS='http://localhost:5174' \
  ai-service-assistant-backend

# In another terminal, test it
curl http://localhost:8000/health
```

**Note:** Local testing won't work with MCP endpoints unless you have:
- AWS credentials mounted (`-v ~/.aws:/home/appuser/.aws:ro`)
- Or AWS credentials as environment variables

### 3. Push to AWS ECR

```bash
# Set variables
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1
REPO_NAME=ai-service-assistant-backend

# Create ECR repository
aws ecr create-repository \
  --repository-name $REPO_NAME \
  --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag image
docker tag ai-service-assistant-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

# Push image
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
```

### 4. Deploy to App Runner

#### Via AWS Console:

1. **Go to App Runner Console**: https://console.aws.amazon.com/apprunner
2. **Click "Create service"**
3. **Repository settings:**
   - Source: **Container registry** → **Amazon ECR**
   - Container image URI: `<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-service-assistant-backend:latest`
   - Deployment trigger: **Automatic** (redeploys when you push new images)

4. **Deployment settings:**
   - Deployment trigger: Automatic

5. **Service settings:**
   - Service name: `ai-service-assistant-backend`
   - Port: `8000`
   - Health check protocol: `HTTP`
   - Health check path: `/health`

6. **Instance configuration:**
   - CPU: 1 vCPU
   - Memory: 2 GB
   - Instance role: **AppRunnerMCPInstanceRole** (create this first with `setup-apprunner-iam.sh`)

7. **Environment variables:**
   ```
   AWS_REGION=us-east-1
   AGENT_NAME=oran_agent
   REQUEST_TIMEOUT_SECONDS=300
   CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:5174
   API_PORT=8000
   ```

8. **Click "Create & Deploy"**

#### Via AWS CLI:

```bash
# First, ensure IAM role exists (run setup-apprunner-iam.sh)

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN=$(aws iam get-role --role-name AppRunnerMCPInstanceRole --query 'Role.Arn' --output text)

# Create App Runner service
aws apprunner create-service \
  --service-name ai-service-assistant-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.us-east-1.amazonaws.com/ai-service-assistant-backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "AWS_REGION": "us-east-1",
          "AGENT_NAME": "oran_agent",
          "REQUEST_TIMEOUT_SECONDS": "300",
          "CORS_ORIGINS": "https://your-frontend-domain.com",
          "API_PORT": "8000"
        }
      }
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB",
    "InstanceRoleArn": "'$ROLE_ARN'"
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }'
```

---

## Dockerfile Improvements

The Dockerfile includes several best practices:

### Security
- ✅ Runs as non-root user (`appuser`)
- ✅ Minimal base image (`python:3.11-slim`)
- ✅ No sensitive data in image

### Performance
- ✅ Layer caching (requirements installed before code copy)
- ✅ Multi-stage build optimization
- ✅ Minimal dependencies

### Reliability
- ✅ Health check configured
- ✅ Proper signal handling
- ✅ Longer start period for health checks (60s)

---

## Testing Your Deployment

### 1. Wait for Deployment

App Runner deployment takes about 3-5 minutes. Monitor in console.

### 2. Get Service URL

```bash
# Get service URL
aws apprunner list-services \
  --query "ServiceSummaryList[?ServiceName=='ai-service-assistant-backend'].ServiceUrl" \
  --output text
```

### 3. Test Endpoints

```bash
# Set your service URL
SERVICE_URL="https://xyz.us-east-1.awsapprunner.com"

# Test health check
curl $SERVICE_URL/health

# Test MCP endpoint
curl $SERVICE_URL/mcp/edge/servers

# Test chat endpoint
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test message"}'
```

---

## Updating Your Deployment

When you make code changes:

```bash
cd backend

# 1. Build new image
docker build -t ai-service-assistant-backend .

# 2. Tag with new version
docker tag ai-service-assistant-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest

# 3. Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest

# 4. App Runner auto-deploys (if enabled) or manually trigger:
aws apprunner start-deployment --service-arn <YOUR_SERVICE_ARN>
```

Or use the automated script:
```bash
./build-and-deploy-docker.sh
```

---

## Troubleshooting

### Build Fails

**Issue:** `ERROR [internal] load metadata for docker.io/library/python:3.11-slim`

**Solution:** Check Docker daemon is running:
```bash
docker ps
```

### Push to ECR Fails

**Issue:** `denied: Your authorization token has expired`

**Solution:** Re-login to ECR:
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### Health Check Failing

**Issue:** App Runner shows "Unhealthy"

**Solutions:**
1. Check `/health` endpoint exists and returns 200
2. Verify port 8000 is exposed
3. Check logs in App Runner Console
4. Increase health check timeout

### Cannot Access AWS Resources

**Issue:** "Unable to locate credentials"

**Solution:** Ensure IAM instance role is attached:
```bash
# Check if role is attached
aws apprunner describe-service \
  --service-arn <YOUR_SERVICE_ARN> \
  --query 'Service.InstanceConfiguration.InstanceRoleArn'

# If null, update service with role
aws apprunner update-service \
  --service-arn <YOUR_SERVICE_ARN> \
  --instance-configuration InstanceRoleArn=<ROLE_ARN>
```

### App Runner Shows Old Code

**Issue:** Deployment succeeds but old code is running

**Solutions:**
1. Check you pushed the latest image
2. Verify image tag in App Runner matches what you pushed
3. Manually trigger deployment:
   ```bash
   aws apprunner start-deployment --service-arn <SERVICE_ARN>
   ```

---

## Environment Variables

Set these in App Runner Console under Configuration → Environment variables:

| Variable | Value | Required |
|----------|-------|----------|
| `AWS_REGION` | `us-east-1` | Yes |
| `AGENT_NAME` | `oran_agent` | Yes |
| `REQUEST_TIMEOUT_SECONDS` | `300` | Yes |
| `API_PORT` | `8000` | Yes |
| `CORS_ORIGINS` | Your frontend URL(s) | Yes |

---

## Cost Optimization

### Development
- Use smaller instance size (0.5 vCPU, 1 GB)
- Pause service when not in use
- Use ECR lifecycle policies to delete old images

### Production
- Enable auto-scaling (default: 1-25 instances)
- Set max instances to control costs
- Monitor with CloudWatch to right-size

---

## Monitoring

### View Logs

```bash
# Get log group
LOG_GROUP=$(aws apprunner describe-service \
  --service-arn <SERVICE_ARN> \
  --query 'Service.ServiceId' \
  --output text)

# View logs
aws logs tail /aws/apprunner/$LOG_GROUP/application --follow
```

### View Metrics

In CloudWatch:
- CPU Utilization
- Memory Utilization
- Request Count
- Response Time
- Active Instances

---

## Next Steps

1. ✅ Build and test Docker image locally
2. ✅ Push to ECR
3. ✅ Create IAM role (`./setup-apprunner-iam.sh`)
4. ✅ Deploy to App Runner
5. ✅ Configure environment variables
6. ✅ Test endpoints
7. ✅ Update frontend with App Runner URL

Your backend is now production-ready! 🚀
