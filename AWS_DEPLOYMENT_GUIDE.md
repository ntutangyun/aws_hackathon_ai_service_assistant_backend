# AWS Deployment Guide - FastAPI Backend

## Overview

This guide covers the **easiest and best** ways to deploy your FastAPI backend on AWS.

## Recommended: AWS App Runner (Easiest ⭐)

**Why App Runner?**
- ✅ Easiest deployment (5 minutes to deploy)
- ✅ Automatic scaling
- ✅ Managed HTTPS/SSL
- ✅ Pay only for what you use
- ✅ Built-in health checks
- ✅ No infrastructure management

**Cost:** ~$25-50/month for typical usage

### Prerequisites

1. **AWS CLI installed and configured**
```bash
aws --version
aws configure
```

2. **Docker installed** (for local testing)
```bash
docker --version
```

3. **IAM Permissions** - Your AWS user needs:
   - `AWSAppRunnerFullAccess`
   - `IAMFullAccess` (to create service role)
   - `ECRFullAccess` (if using ECR)

### Option 1: Deploy from Source (Recommended)

#### Step 1: Create IAM Role for App Runner

Create `apprunner-instance-role-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/mcp_server/*/runtime/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:/mcp_server/*/cognito/credentials*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:InitiateAuth"
      ],
      "Resource": "*"
    }
  ]
}
```

Create the IAM role:
```bash
# Create the policy
aws iam create-policy \
  --policy-name AppRunnerMCPAccessPolicy \
  --policy-document file://apprunner-instance-role-policy.json

# Create the role
aws iam create-role \
  --role-name AppRunnerMCPInstanceRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach the policy to the role
aws iam attach-role-policy \
  --role-name AppRunnerMCPInstanceRole \
  --policy-arn arn:aws:iam::<YOUR_ACCOUNT_ID>:policy/AppRunnerMCPAccessPolicy
```

#### Step 2: Push Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit"

# Push to GitHub
git remote add origin https://github.com/yourusername/ai-service-assistant.git
git push -u origin main
```

#### Step 3: Create App Runner Service via Console

1. **Go to AWS App Runner Console**: https://console.aws.amazon.com/apprunner
2. **Click "Create service"**
3. **Repository settings:**
   - Source: GitHub
   - Connect to GitHub (authorize AWS)
   - Select repository: `yourusername/ai-service-assistant`
   - Branch: `main`
   - Source directory: `/backend`
4. **Deployment settings:**
   - Deployment trigger: Automatic (deploys on every push)
5. **Build settings:**
   - Configuration: Use configuration file
   - Create `backend/apprunner.yaml` (see below)
6. **Service settings:**
   - Service name: `ai-service-assistant-backend`
   - Port: `8000`
   - Environment variables (see below)
7. **Instance configuration:**
   - Instance role: Select `AppRunnerMCPInstanceRole`
8. **Click "Create & Deploy"**

Create `backend/apprunner.yaml`:
```yaml
version: 1.0
runtime: python3
build:
  commands:
    pre-build:
      - echo "Installing dependencies"
    build:
      - pip install -r requirements.txt
run:
  command: uvicorn main:app --host 0.0.0.0 --port 8000
  network:
    port: 8000
  env:
    - name: AWS_REGION
      value: us-east-1
    - name: AGENT_NAME
      value: oran_agent
    - name: REQUEST_TIMEOUT_SECONDS
      value: "300"
    - name: API_PORT
      value: "8000"
```

#### Step 4: Configure Environment Variables

In App Runner Console → Your service → Configuration → Edit → Environment variables:

```
AWS_REGION=us-east-1
AGENT_NAME=oran_agent
REQUEST_TIMEOUT_SECONDS=300
CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:5174
API_PORT=8000
```

#### Step 5: Access Your Service

After deployment completes (~5 minutes):
- App Runner provides a URL: `https://abc123.us-east-1.awsapprunner.com`
- Test health check: `curl https://abc123.us-east-1.awsapprunner.com/health`

### Option 2: Deploy from Docker (ECR)

If you prefer using Docker:

#### Step 1: Build and Push to ECR

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

# Create ECR repository
aws ecr create-repository --repository-name ai-service-assistant-backend

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
cd backend
docker build -t ai-service-assistant-backend .

# Tag image
docker tag ai-service-assistant-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest
```

#### Step 2: Create App Runner Service from ECR

```bash
aws apprunner create-service \
  --service-name ai-service-assistant-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/ai-service-assistant-backend:latest",
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
    "AutoDeploymentsEnabled": false
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB",
    "InstanceRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/AppRunnerMCPInstanceRole"
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

## Alternative: AWS ECS Fargate (More Control)

**Why ECS Fargate?**
- More control over networking and scaling
- Better for complex microservices
- VPC integration
- Load balancer support

**Cost:** ~$30-70/month

### Step 1: Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name ai-service-assistant-cluster
```

### Step 2: Create Task Definition

Create `backend/ecs-task-definition.json`:
```json
{
  "family": "ai-service-assistant-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/AppRunnerMCPInstanceRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-service-assistant-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "AWS_REGION", "value": "us-east-1"},
        {"name": "AGENT_NAME", "value": "oran_agent"},
        {"name": "REQUEST_TIMEOUT_SECONDS", "value": "300"},
        {"name": "API_PORT", "value": "8000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-service-assistant-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register task definition:
```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

### Step 3: Create Application Load Balancer

```bash
# Create security group for ALB
aws ec2 create-security-group \
  --group-name ai-assistant-alb-sg \
  --description "Security group for AI Assistant ALB" \
  --vpc-id <YOUR_VPC_ID>

# Allow inbound HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id <ALB_SG_ID> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id <ALB_SG_ID> \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Create ALB
aws elbv2 create-load-balancer \
  --name ai-assistant-alb \
  --subnets <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-groups <ALB_SG_ID>

# Create target group
aws elbv2 create-target-group \
  --name ai-assistant-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <YOUR_VPC_ID> \
  --target-type ip \
  --health-check-path /health
```

### Step 4: Create ECS Service

```bash
# Create security group for ECS tasks
aws ec2 create-security-group \
  --group-name ai-assistant-ecs-sg \
  --description "Security group for AI Assistant ECS tasks" \
  --vpc-id <YOUR_VPC_ID>

# Allow inbound from ALB
aws ec2 authorize-security-group-ingress \
  --group-id <ECS_SG_ID> \
  --protocol tcp \
  --port 8000 \
  --source-group <ALB_SG_ID>

# Create service
aws ecs create-service \
  --cluster ai-service-assistant-cluster \
  --service-name backend-service \
  --task-definition ai-service-assistant-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["<SUBNET_ID_1>", "<SUBNET_ID_2>"],
      "securityGroups": ["<ECS_SG_ID>"],
      "assignPublicIp": "ENABLED"
    }
  }' \
  --load-balancers '[
    {
      "targetGroupArn": "<TARGET_GROUP_ARN>",
      "containerName": "backend",
      "containerPort": 8000
    }
  ]'
```

---

## Testing Your Deployment

### 1. Health Check
```bash
# App Runner
curl https://your-app.us-east-1.awsapprunner.com/health

# ECS with ALB
curl https://your-alb-dns.us-east-1.elb.amazonaws.com/health
```

### 2. Test MCP Endpoints
```bash
BASE_URL="https://your-app.us-east-1.awsapprunner.com"

# Test edge servers
curl $BASE_URL/mcp/edge/servers

# Test subscriptions
curl $BASE_URL/mcp/udm/subscriptions

# Test AI services
curl $BASE_URL/mcp/ai-services/categories
```

### 3. Test Chat Endpoint
```bash
curl -X POST $BASE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message"}'
```

---

## Monitoring and Logging

### App Runner
- **Logs**: Automatically streamed to CloudWatch
- **View logs**: App Runner Console → Your service → Logs
- **Metrics**: Automatic CPU, memory, request metrics

### ECS Fargate
```bash
# View logs
aws logs tail /ecs/ai-service-assistant-backend --follow

# View metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=backend-service \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

---

## Scaling

### App Runner Auto-Scaling
App Runner automatically scales based on traffic (10-100 instances by default).

To customize:
```bash
aws apprunner update-service \
  --service-arn <SERVICE_ARN> \
  --auto-scaling-configuration-arn <CONFIG_ARN>
```

### ECS Auto-Scaling
```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/ai-service-assistant-cluster/backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/ai-service-assistant-cluster/backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    }
  }'
```

---

## Custom Domain Setup

### 1. Create Certificate in ACM
```bash
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS
```

### 2. Configure Custom Domain in App Runner
```bash
aws apprunner associate-custom-domain \
  --service-arn <SERVICE_ARN> \
  --domain-name api.yourdomain.com
```

Follow instructions to add CNAME records to your DNS.

---

## Environment-Specific Deployments

### Development
```yaml
# backend/apprunner-dev.yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  env:
    - name: AWS_REGION
      value: us-east-1
    - name: CORS_ORIGINS
      value: http://localhost:5174
```

### Production
```yaml
# backend/apprunner-prod.yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
  env:
    - name: AWS_REGION
      value: us-east-1
    - name: CORS_ORIGINS
      value: https://yourdomain.com
```

---

## Cost Optimization

### App Runner
- **Free Tier**: 100 GB-hours/month compute, 3 GB/month storage
- **Typical Cost**: ~$25-50/month for moderate traffic
- **Optimization**: Set max instances to limit costs

### ECS Fargate
- **Cost**: ~$30-70/month for 2 tasks running 24/7
- **Optimization**:
  - Use Spot instances for non-critical workloads
  - Scale down during off-peak hours
  - Use Fargate Spot (70% savings)

---

## Troubleshooting

### App Runner Deployment Fails
```bash
# Check build logs
aws apprunner list-operations --service-arn <SERVICE_ARN>

# View specific operation
aws apprunner describe-operation --operation-arn <OPERATION_ARN>
```

### Health Check Failing
- Ensure `/health` endpoint returns 200
- Check security groups allow traffic on port 8000
- Verify IAM role has necessary permissions

### Cannot Connect to MCP Servers
- Verify SSM parameters exist: `/mcp_server/*/runtime/agent_arn`
- Verify Secrets Manager secrets exist
- Check IAM role has permissions to access SSM and Secrets Manager

### High Latency
- Enable CloudFront in front of App Runner/ALB
- Increase instance size (App Runner) or task CPU/memory (ECS)
- Check MCP server response times

---

## Recommended: App Runner Quick Start

For the **fastest deployment**:

1. **Create apprunner.yaml** in backend directory (see above)
2. **Push to GitHub**
3. **Create IAM role** with MCP permissions
4. **Deploy via Console**:
   - Go to App Runner → Create service
   - Connect GitHub → Select repo
   - Configure environment variables
   - Select IAM role
   - Deploy!

Total time: **~10 minutes** ⚡

Your backend will be live at: `https://xyz.us-east-1.awsapprunner.com`

Update your frontend's API URL and you're done! 🎉
