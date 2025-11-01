#!/bin/bash

# Build and deploy backend to AWS App Runner using Docker/ECR
# This script builds the Docker image, pushes to ECR, and deploys to App Runner

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Backend Docker Build & Deploy to App Runner${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
REPO_NAME="ai-service-assistant-backend"
SERVICE_NAME="ai-service-assistant-backend"
IMAGE_TAG=${IMAGE_TAG:-latest}

# Get AWS account ID
echo -e "${YELLOW}Getting AWS account information...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Could not get AWS account ID. Is AWS CLI configured?${NC}"
    exit 1
fi

echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ AWS Region: $AWS_REGION${NC}"
echo ""

# ECR repository URL
ECR_REPO_URL="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"

# Step 1: Create ECR repository if it doesn't exist
echo -e "${BLUE}Step 1: Creating ECR repository (if needed)${NC}"
if aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION &> /dev/null; then
    echo -e "${YELLOW}Repository '$REPO_NAME' already exists${NC}"
else
    echo "Creating ECR repository: $REPO_NAME"
    aws ecr create-repository \
        --repository-name $REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        > /dev/null
    echo -e "${GREEN}✓ Repository created${NC}"
fi
echo ""

# Step 2: Login to ECR
echo -e "${BLUE}Step 2: Logging in to ECR${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REPO_URL
echo -e "${GREEN}✓ Logged in to ECR${NC}"
echo ""

# Step 3: Build Docker image
echo -e "${BLUE}Step 3: Building Docker image${NC}"
echo "Building image: $REPO_NAME:$IMAGE_TAG"
docker build -t $REPO_NAME:$IMAGE_TAG .

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo ""

# Step 4: Tag image for ECR
echo -e "${BLUE}Step 4: Tagging image for ECR${NC}"
docker tag $REPO_NAME:$IMAGE_TAG $ECR_REPO_URL:$IMAGE_TAG
echo -e "${GREEN}✓ Image tagged: $ECR_REPO_URL:$IMAGE_TAG${NC}"
echo ""

# Step 5: Push to ECR
echo -e "${BLUE}Step 5: Pushing image to ECR${NC}"
docker push $ECR_REPO_URL:$IMAGE_TAG

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to push image to ECR${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Image pushed to ECR successfully${NC}"
echo ""

# Step 6: Get image digest
IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name $REPO_NAME \
    --region $AWS_REGION \
    --query 'imageDetails[0].imageDigest' \
    --output text)

echo -e "${GREEN}Image Digest: $IMAGE_DIGEST${NC}"
echo ""

# Step 7: Check if App Runner service exists
echo -e "${BLUE}Step 6: Checking for existing App Runner service${NC}"
SERVICE_ARN=$(aws apprunner list-services \
    --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
    --output text 2>/dev/null || true)

if [ -z "$SERVICE_ARN" ]; then
    echo -e "${YELLOW}No existing service found. Creating new service...${NC}"
    echo ""
    echo -e "${BLUE}Please create the service in App Runner Console with:${NC}"
    echo "  - Source: Container registry → Amazon ECR"
    echo "  - Image URI: $ECR_REPO_URL:$IMAGE_TAG"
    echo "  - Port: 8000"
    echo "  - Service name: $SERVICE_NAME"
    echo "  - Instance role: AppRunnerMCPInstanceRole"
    echo ""
    echo "Environment variables to set:"
    echo "  AWS_REGION=us-east-1"
    echo "  AGENT_NAME=oran_agent"
    echo "  REQUEST_TIMEOUT_SECONDS=300"
    echo "  CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:5174"
    echo "  API_PORT=8000"
    echo ""
    echo -e "${GREEN}Image is ready in ECR: $ECR_REPO_URL:$IMAGE_TAG${NC}"
else
    echo -e "${GREEN}Found existing service: $SERVICE_ARN${NC}"
    echo ""
    read -p "Do you want to trigger a new deployment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Updating service to use new image..."

        # For App Runner, we need to update the service to trigger redeployment
        # This is typically done via console or by updating the service configuration
        echo -e "${YELLOW}Note: App Runner auto-deploys when ECR image is updated${NC}"
        echo -e "${YELLOW}If auto-deploy is enabled, deployment will start automatically${NC}"
        echo ""
        echo "To manually trigger deployment:"
        echo "1. Go to App Runner Console"
        echo "2. Select service: $SERVICE_NAME"
        echo "3. Click 'Deploy' button"
        echo ""
        echo "Or update service via CLI (this will trigger redeployment):"
        echo "aws apprunner start-deployment --service-arn $SERVICE_ARN"
    fi
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}         Deployment Preparation Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "Image pushed to: ${GREEN}$ECR_REPO_URL:$IMAGE_TAG${NC}"
echo ""
echo "Next steps:"
echo "1. If creating new service, use the App Runner Console"
echo "2. If updating existing service, deployment will start automatically"
echo "3. Monitor deployment in App Runner Console"
echo ""
echo "To test locally before deploying:"
echo "  docker run -p 8000:8000 \\"
echo "    -e AWS_REGION=us-east-1 \\"
echo "    -e AGENT_NAME=oran_agent \\"
echo "    -e CORS_ORIGINS='*' \\"
echo "    $REPO_NAME:$IMAGE_TAG"
echo ""
