#!/bin/bash

# Quick deployment script for AWS App Runner
# This script helps you deploy the backend to AWS App Runner

set -e

echo "========================================="
echo "AWS App Runner Deployment Helper"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${GREEN}AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}AWS Region: $AWS_REGION${NC}"
echo ""

# Step 1: Create IAM policy and role
echo "========================================="
echo "Step 1: Creating IAM Role for App Runner"
echo "========================================="
echo ""

# Check if role already exists
if aws iam get-role --role-name AppRunnerMCPInstanceRole &> /dev/null; then
    echo -e "${YELLOW}IAM role 'AppRunnerMCPInstanceRole' already exists, skipping creation${NC}"
else
    echo "Creating IAM policy..."

    # Create policy document
    cat > /tmp/apprunner-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameter"],
      "Resource": "arn:aws:ssm:*:*:parameter/mcp_server/*/runtime/*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:/mcp_server/*/cognito/credentials*"
    },
    {
      "Effect": "Allow",
      "Action": ["cognito-idp:InitiateAuth"],
      "Resource": "*"
    }
  ]
}
EOF

    # Create the policy
    POLICY_ARN=$(aws iam create-policy \
        --policy-name AppRunnerMCPAccessPolicy \
        --policy-document file:///tmp/apprunner-policy.json \
        --query 'Policy.Arn' \
        --output text 2>/dev/null || aws iam list-policies --query "Policies[?PolicyName=='AppRunnerMCPAccessPolicy'].Arn" --output text)

    echo -e "${GREEN}Policy ARN: $POLICY_ARN${NC}"

    # Create trust policy for App Runner
    cat > /tmp/apprunner-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

    # Create the role
    aws iam create-role \
        --role-name AppRunnerMCPInstanceRole \
        --assume-role-policy-document file:///tmp/apprunner-trust-policy.json \
        > /dev/null

    # Attach the policy to the role
    aws iam attach-role-policy \
        --role-name AppRunnerMCPInstanceRole \
        --policy-arn $POLICY_ARN

    echo -e "${GREEN}✓ IAM role created successfully${NC}"
fi

echo ""

# Step 2: Get deployment preference
echo "========================================="
echo "Step 2: Choose Deployment Method"
echo "========================================="
echo ""
echo "1. Deploy from GitHub (Recommended - auto-deploys on push)"
echo "2. Deploy from ECR (Manual - you build and push Docker images)"
echo ""
read -p "Enter your choice (1 or 2): " DEPLOY_METHOD

if [ "$DEPLOY_METHOD" == "1" ]; then
    echo ""
    echo -e "${YELLOW}GitHub Deployment Steps:${NC}"
    echo ""
    echo "1. Push your code to GitHub if you haven't already:"
    echo "   git add ."
    echo "   git commit -m 'Deploy to App Runner'"
    echo "   git push origin main"
    echo ""
    echo "2. Go to AWS App Runner Console:"
    echo "   https://console.aws.amazon.com/apprunner"
    echo ""
    echo "3. Click 'Create service'"
    echo ""
    echo "4. Configure:"
    echo "   - Source: GitHub"
    echo "   - Repository: Select your repo"
    echo "   - Branch: main"
    echo "   - Source directory: /backend"
    echo "   - Configuration: Use apprunner.yaml"
    echo ""
    echo "5. Service settings:"
    echo "   - Service name: ai-service-assistant-backend"
    echo "   - Instance role: AppRunnerMCPInstanceRole"
    echo ""
    echo "6. Environment variables (add in Console):"
    echo "   CORS_ORIGINS=https://your-frontend-domain.com"
    echo ""
    echo "7. Click 'Create & Deploy'"
    echo ""
    echo -e "${GREEN}✓ Follow the steps above to complete deployment${NC}"

elif [ "$DEPLOY_METHOD" == "2" ]; then
    # ECR deployment
    echo ""
    echo "========================================="
    echo "Step 3: Building and Pushing to ECR"
    echo "========================================="
    echo ""

    # Create ECR repository if it doesn't exist
    if ! aws ecr describe-repositories --repository-names ai-service-assistant-backend --region $AWS_REGION &> /dev/null; then
        echo "Creating ECR repository..."
        aws ecr create-repository \
            --repository-name ai-service-assistant-backend \
            --region $AWS_REGION \
            > /dev/null
        echo -e "${GREEN}✓ ECR repository created${NC}"
    else
        echo -e "${YELLOW}ECR repository already exists${NC}"
    fi

    # Login to ECR
    echo "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    # Build Docker image
    echo "Building Docker image..."
    docker build -t ai-service-assistant-backend .

    # Tag image
    echo "Tagging image..."
    docker tag ai-service-assistant-backend:latest \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest

    # Push to ECR
    echo "Pushing to ECR..."
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest

    echo -e "${GREEN}✓ Image pushed to ECR successfully${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo ""
    echo "Go to AWS App Runner Console and create a service with:"
    echo "  - Source: Container registry"
    echo "  - Image URI: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-service-assistant-backend:latest"
    echo "  - Port: 8000"
    echo "  - Instance role: AppRunnerMCPInstanceRole"
    echo ""
fi

echo ""
echo "========================================="
echo "Important: Configure These After Deploy"
echo "========================================="
echo ""
echo "1. Environment Variables (in App Runner Console):"
echo "   - CORS_ORIGINS=https://your-frontend-domain.com"
echo ""
echo "2. Make sure your MCP servers are deployed with:"
echo "   - SSM Parameters: /mcp_server/{udm,edge_server,ai_service}/runtime/*"
echo "   - Secrets: /mcp_server/{udm,edge_server,ai_service}/cognito/credentials"
echo ""
echo "3. Test your deployment:"
echo "   curl https://your-app.us-east-1.awsapprunner.com/health"
echo ""
echo -e "${GREEN}Deployment preparation complete!${NC}"
