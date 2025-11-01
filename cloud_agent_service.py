"""
Cloud Agent Service for running LLM agent with AWS AgentCore Runtime MCP servers.

This service creates a Strands agent that connects to MCP servers deployed on AWS AgentCore Runtime.
"""

import logging
import boto3
import json
from typing import Dict, Any, List, Optional
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from strands import Agent
from strands.models import BedrockModel

from config import settings

logger = logging.getLogger(__name__)


class CloudAgentService:
    """
    Cloud agent service that runs Strands agent connecting to AWS AgentCore Runtime MCP servers.

    Used when ENVIRONMENT=production to connect to cloud-deployed MCP servers.
    """

    def __init__(self):
        """Initialize the cloud agent with MCP tools from AWS AgentCore Runtime."""
        self.agent = None
        self.mcp_clients = {}
        self.ssm_client = None
        self.secrets_client = None
        self.cognito_client = None

        if settings.environment == "production":
            self._initialize_aws_clients()
            self._initialize_agent()

    def _initialize_aws_clients(self):
        """Initialize AWS clients for accessing AgentCore Runtime MCP servers."""
        self.ssm_client = boto3.client('ssm', region_name=settings.aws_region)
        self.secrets_client = boto3.client('secretsmanager', region_name=settings.aws_region)
        self.cognito_client = boto3.client('cognito-idp', region_name=settings.aws_region)
        logger.info("AWS clients initialized for cloud agent service")

    def _get_cognito_credentials(self, server_type: str) -> Dict[str, str]:
        """
        Get Cognito credentials from Secrets Manager for a specific MCP server.

        Args:
            server_type: The type of MCP server ('udm', 'edge_server', 'ai_service')

        Returns:
            Dict with client_id, username, and password for Cognito authentication
        """
        try:
            secret_name = f'/mcp/{server_type}/cognito/credentials'
            logger.debug(f"Fetching Cognito credentials from Secrets Manager: {secret_name}")
            secret = self.secrets_client.get_secret_value(SecretId=secret_name)
            cognito_creds = json.loads(secret['SecretString'])

            return {
                'client_id': cognito_creds['client_id'],
                'username': cognito_creds.get('username', 'testuser'),
                'password': cognito_creds.get('password', 'MyPassword123!')
            }

        except Exception as e:
            logger.error(f"Failed to get Cognito credentials for {server_type}: {e}")
            raise

    def _get_mcp_server_url(self, server_type: str) -> str:
        """
        Get MCP server URL from SSM Parameter Store.

        Args:
            server_type: The type of MCP server ('udm', 'edge_server', 'ai_service')

        Returns:
            MCP server URL
        """
        try:
            param_name = f'/mcp/{server_type}/runtime/url'
            logger.debug(f"Fetching MCP server URL from SSM: {param_name}")
            response = self.ssm_client.get_parameter(Name=param_name)
            url = response["Parameter"]["Value"]
            logger.debug(f"MCP server URL retrieved: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to get MCP server URL for {server_type}: {e}")
            raise

    def _get_bearer_token(self, server_type: str) -> str:
        """
        Get bearer token for MCP server by authenticating with Cognito.

        Args:
            server_type: The type of MCP server ('udm', 'edge_server', 'ai_service')

        Returns:
            Bearer token string
        """
        try:
            credentials = self._get_cognito_credentials(server_type)

            logger.debug(f"Authenticating with Cognito for {server_type}...")

            # Authenticate with Cognito using username/password
            auth_response = self.cognito_client.initiate_auth(
                ClientId=credentials['client_id'],
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': credentials['username'],
                    'PASSWORD': credentials['password']
                }
            )

            access_token = auth_response['AuthenticationResult']['AccessToken']
            logger.debug(f"✓ Token obtained for {server_type}")
            return access_token

        except Exception as e:
            logger.error(f"Cognito authentication failed for {server_type}: {e}")
            raise

    def _get_mcp_client(self, server_type: str):
        """
        Create an MCP client for a specific server type connecting to AWS AgentCore Runtime.

        Args:
            server_type: The type of MCP server ('udm', 'edge_server', 'ai_service')

        Returns:
            MCPClient instance configured for the specified server
        """
        def create_client():
            # Get MCP server URL from SSM
            mcp_url = self._get_mcp_server_url(server_type)

            # Get bearer token from Cognito
            bearer_token = self._get_bearer_token(server_type)

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {bearer_token}"
            }

            return streamablehttp_client(
                mcp_url,
                headers,
                timeout=120,
                terminate_on_close=False
            )

        return MCPClient(create_client)

    def _initialize_agent(self):
        """Initialize the agent with tools from all AWS AgentCore Runtime MCP servers."""
        try:
            logger.info("🤖 Initializing cloud Strands agent...")

            # Create MCP clients for all three servers
            logger.info("📡 Connecting to AWS AgentCore Runtime MCP servers...")
            self.mcp_clients['udm'] = self._get_mcp_client('udm')
            self.mcp_clients['edge_server'] = self._get_mcp_client('edge_server')
            self.mcp_clients['ai_service'] = self._get_mcp_client('ai_service')

            # Collect tools from all MCP servers
            all_tools = []

            # Get tools from UDM server
            try:
                with self.mcp_clients['udm']:
                    udm_tools = self.mcp_clients['udm'].list_tools_sync()
                    all_tools.extend(udm_tools)
                    logger.info(f"✓ Loaded {len(udm_tools)} tools from UDM MCP server")
            except Exception as e:
                logger.warning(f"⚠ Failed to load UDM tools: {e}")

            # Get tools from Edge Server
            try:
                with self.mcp_clients['edge_server']:
                    edge_tools = self.mcp_clients['edge_server'].list_tools_sync()
                    all_tools.extend(edge_tools)
                    logger.info(f"✓ Loaded {len(edge_tools)} tools from Edge Server MCP")
            except Exception as e:
                logger.warning(f"⚠ Failed to load Edge Server tools: {e}")

            # Get tools from AI Service Repository
            try:
                with self.mcp_clients['ai_service']:
                    ai_tools = self.mcp_clients['ai_service'].list_tools_sync()
                    all_tools.extend(ai_tools)
                    logger.info(f"✓ Loaded {len(ai_tools)} tools from AI Service MCP")
            except Exception as e:
                logger.warning(f"⚠ Failed to load AI Service tools: {e}")

            logger.info(f"📦 Total tools available: {len(all_tools)}")

            # Configure the Claude Sonnet 4.5 model
            model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
            model = BedrockModel(model_id=model_id)
            logger.info(f"🧠 Using model: {model_id}")

            # Create the agent with system prompt (same as local agent)
            self.agent = Agent(
                model=model,
                tools=all_tools,
                system_prompt=self._get_system_prompt()
            )

            logger.info("✅ Cloud Strands agent initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Failed to initialize cloud agent: {e}")
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent (same as local agent)."""
        return """You are an advanced 6G Network Management Agent supporting comprehensive network infrastructure orchestration and AI service deployment.

SUPPORTED USE CASES:

1. **User Subscription Management**: Create, update, and monitor user subscriptions with cellular and Edge AI services
2. **QoS Profile Configuration**: Manage Quality of Service parameters including QCI, priority, bandwidth, and latency
3. **Edge AI Service Subscription**: Add, remove, and monitor Edge AI services for subscribers
4. **Edge Server Management**: Monitor and manage edge computing infrastructure with GPU resources
5. **AI Service Deployment**: Deploy, undeploy, and monitor AI services on edge servers
6. **Resource Optimization**: Find optimal edge servers for service deployment based on resource availability
7. **AI Service Discovery**: Search and explore the catalog of ready-to-deploy AI services
8. **Network Analytics**: Analyze network-wide statistics, utilization, and health metrics

CAPABILITIES PER COMPONENT:

**UDM (Unified Data Management) - User Subscriptions:**
- Get all user subscriptions or filter by status (ACTIVE/SUSPENDED)
- Get detailed subscription information for specific subscribers
- Create new user subscriptions with cellular and Edge AI services
- Update QoS profiles (QCI, priority, bandwidth limits, latency)
- Add/remove Edge AI service subscriptions using model names
- Update data usage tracking
- Get subscription summaries and statistics

**Edge Server Management - Infrastructure:**
- List all edge servers with optional status/health filters
- Get detailed server information including location, GPU resources
- Monitor server resources (CPU, memory, storage, GPU utilization)
- Get GPU-specific resource details (model, memory, utilization)
- View deployed services on each edge server
- Deploy AI services to edge servers using model name and Docker image URL
- Undeploy services from edge servers
- Get network-wide summary statistics
- Get health status across all edge servers
- Find servers with available capacity matching specific requirements

**AI Service Repository - Service Catalog (AWS ECR):**
- Browse all available AI services from AWS ECR with task type filters
- Search services by model name or keyword
- Get detailed service information including performance profiles
- View service resource requirements (CPU, memory, storage, GPU)
- Get deployment configuration with Docker image URLs
- List available task types (image-classification, object-detection, etc.)
- Get catalog summary statistics
- Find services compatible with specific device types (CPU/GPU)
- Query inference metrics and XAI (explainable AI) methods

SUPPORTED WORKFLOWS:

**Workflow 1: New User Onboarding**
1. Create new user subscription with cellular plan
2. Configure QoS profile based on plan tier
3. Add Edge AI services if requested
4. Verify subscription creation and status

**Workflow 2: AI Service Deployment**
1. Search AI service catalog for desired model by name or task type
2. Get service resource requirements and Docker image repository URL
3. Find edge servers with sufficient capacity
4. Deploy service to optimal edge server using model name and image URL
5. Verify deployment and monitor status

**Workflow 3: Resource Optimization**
1. Get network summary and utilization statistics
2. Identify underutilized or overutilized edge servers
3. Recommend service redeployment for better distribution
4. Monitor health status and alert on issues

**Workflow 4: Subscriber Edge AI Provisioning**
1. Get subscriber's current subscription details
2. Search available Edge AI services by task type
3. Add Edge AI service to subscriber's subscription
4. Ensure service is deployed on nearby edge server
5. Confirm activation and monitor performance

INTERACTION GUIDELINES:

1. **Be Proactive**: When users ask about deployments, automatically check resource availability
2. **Provide Context**: Include relevant details like GPU types, utilization percentages, service task types
3. **Suggest Optimizations**: Recommend best practices for resource allocation and service placement
4. **Handle Errors Gracefully**: If a requested operation fails, suggest alternatives or troubleshooting steps
5. **Multi-step Operations**: Break complex requests into logical steps and confirm each step
6. **Data-Driven Decisions**: Use actual resource metrics and service requirements for recommendations

TECHNICAL DETAILS:

**QoS Parameters:**
- QCI (QoS Class Identifier): 1-9, where lower is higher priority
- Priority levels: PREMIUM, STANDARD, BASIC
- Bandwidth: Measured in Mbps for downlink/uplink
- Latency: Target latency in milliseconds

**GPU Resources:**
- Supported models: NVIDIA A100 (40GB/80GB), H100 (80GB)
- Track total memory, used memory, and utilization percentage
- Consider GPU requirements when deploying AI services

**Service Task Types:**
- image-classification: Image categorization and recognition
- object-detection: Object detection and localization
- text-generation: Text generation and completion
- text-classification: Text categorization
- zero-shot-classification: Classification without training
- question-answering: Question answering systems
- token-classification: Named entity recognition
- fill-mask: Masked language modeling
- sentence-similarity: Sentence comparison
- summarization: Text summarization

**Data Plans:**
- UNLIMITED: No data cap, higher QoS priority
- LIMITED: Specific data limit, monitor usage against limit

When responding to queries:
- Use appropriate tools to fetch real-time data
- Provide specific details (IDs, metrics, statuses)
- Format responses clearly with relevant sections
- Include actionable recommendations
- Highlight important metrics or alerts

Example Queries You Should Handle:
- "Show me all active subscriptions"
- "Deploy microsoft/resnet-50 model to the edge server with most GPU capacity"
- "What Edge AI services does subscriber sub-001 have?"
- "Find all image-classification models that support GPU"
- "Which edge servers are running low on resources?"
- "Create a new premium subscription for user John Doe"
- "What's the total GPU utilization across the network?"
- "Show me inference metrics for google/vit-base-patch16-224"
- "List all available XAI methods for facebook/detr-resnet-50"
"""

    async def invoke_agent(
        self,
        user_message: str = None,
        messages: List[Dict[str, Any]] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Invoke the cloud agent with a user message or conversation history.

        Args:
            user_message: Single user message (legacy format)
            messages: Full conversation history in format [{"role": "user|assistant", "content": [{"text": "..."}]}]
            session_id: Session ID (not used in cloud mode)

        Returns:
            Dict containing agent response
        """
        try:
            if not self.agent:
                raise Exception("Cloud agent not initialized. Make sure ENVIRONMENT=production and AWS resources are accessible.")

            # Determine input format
            if messages:
                # Convert messages format to simple text for the agent
                conversation_input = messages
                logger.info(f"Invoking cloud agent with {len(messages)} messages in history")
            elif user_message:
                # Single message format
                conversation_input = user_message
                logger.info(f"Invoking cloud agent with single message: {user_message[:100]}...")
            else:
                raise ValueError("Either user_message or messages must be provided")

            # Open MCP client contexts and invoke agent
            with self.mcp_clients['udm'], self.mcp_clients['edge_server'], self.mcp_clients['ai_service']:
                # Invoke the agent
                result = self.agent(conversation_input)

                # Extract response text
                if hasattr(result, 'message'):
                    response_text = result.message
                elif isinstance(result, str):
                    response_text = result
                else:
                    response_text = str(result)

                if type(response_text) == dict:
                    if "content" in response_text:
                        response_text = response_text["content"]
                        response_text = response_text[0]["text"] if isinstance(response_text, list) and len(response_text) > 0 else str(response_text)

                logger.info(f"Cloud agent response (first 100 chars): {response_text[:100]}...")

                return {
                    "response": response_text,
                    "session_id": session_id,
                    "trace": None,
                    "success": True
                }

        except Exception as e:
            logger.error(f"Error invoking cloud agent: {e}")
            return {
                "response": f"Error invoking cloud agent: {str(e)}",
                "session_id": session_id,
                "trace": None,
                "success": False,
                "error": str(e)
            }


# Global service instance (only initialized if ENVIRONMENT=production)
cloud_agent_service = CloudAgentService() if settings.environment == "production" else None
