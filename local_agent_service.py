"""
Local Agent Service for running LLM agent directly in backend.

This service creates a local Strands agent with MCP tools when running in local mode,
avoiding the need to connect to AWS AgentCore Runtime.
"""

import logging
from typing import Dict, Any, List, Optional
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from strands import Agent
from strands.models import BedrockModel

from config import settings

logger = logging.getLogger(__name__)

class LocalAgentService:
    """
    Local agent service that runs Strands agent directly in the backend.

    Used when ENVIRONMENT=local to avoid AWS AgentCore Runtime dependency.
    """

    def __init__(self):
        """Initialize the local agent with MCP tools."""
        self.agent = None
        self.mcp_clients = {}

        if settings.environment == "local":
            self._initialize_agent()

    def _get_mcp_client(self, server_type: str, port: int):
        """
        Create an MCP client for a specific server type.

        Args:
            server_type: The type of MCP server ('udm', 'edge_server', 'ai_service')
            port: The localhost port for the MCP server

        Returns:
            MCPClient instance configured for the specified server
        """
        def create_client():
            mcp_url = f"http://localhost:{port}/mcp"

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }

            return streamablehttp_client(
                mcp_url,
                headers,
                timeout=120,
                terminate_on_close=False
            )

        return MCPClient(create_client)

    def _initialize_agent(self):
        """Initialize the agent with tools from all MCP servers."""
        try:
            logger.info("🤖 Initializing local Strands agent...")

            # Create MCP clients for all three servers
            logger.info("📡 Connecting to local MCP servers...")
            self.mcp_clients['udm'] = self._get_mcp_client('udm', settings.local_udm_port)
            self.mcp_clients['edge_server'] = self._get_mcp_client('edge_server', settings.local_edge_server_port)
            self.mcp_clients['ai_service'] = self._get_mcp_client('ai_service', settings.local_ai_service_port)

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

            # Create the agent with system prompt
            self.agent = Agent(
                model=model,
                tools=all_tools,
                system_prompt=self._get_system_prompt()
            )

            logger.info("✅ Local Strands agent initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Failed to initialize local agent: {e}")
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are a friendly and helpful AI Service Assistant for a 6G network provider. Your role is to help customers discover, subscribe to, and use AI services seamlessly.

YOUR PRIMARY MISSION:
Help customers find the perfect AI services for their needs, get them subscribed, and ensure they can easily access and use these services.

WHAT YOU CAN HELP WITH:

1. **AI Service Discovery & Recommendations**
   - Help customers find AI services based on their needs
   - Recommend services for specific use cases
   - Explain what different AI services can do
   - Show available AI capabilities (image analysis, text generation, object detection, etc.)

2. **Subscription Management**
   - View current subscriptions and active services
   - Add new AI services to subscriptions
   - Remove services no longer needed
   - Check subscription status and details

3. **Service Access & Usage**
   - Get service endpoints (URLs) for accessing AI services
   - Provide instructions on how to use services
   - Check if services are ready and available
   - Help troubleshoot access issues

AVAILABLE AI SERVICE TYPES:

**Vision & Image Services:**
- Image Classification: Identify and categorize objects in images
- Object Detection: Locate and identify multiple objects in images
- Zero-Shot Classification: Classify images without prior training examples

**Text & Language Services:**
- Text Generation: Create human-like text content
- Text Classification: Categorize and analyze text documents
- Question Answering: Answer questions based on context
- Summarization: Create concise summaries of long text
- Token Classification: Extract entities like names, locations, dates
- Fill-Mask: Complete missing words in sentences
- Sentence Similarity: Compare and measure text similarity

HOW TO HELP CUSTOMERS:

**When customers want to find AI services:**
1. Ask about their use case or what they want to accomplish
2. Search the catalog for relevant services
3. Explain each service's capabilities in simple terms
4. Recommend the best option based on their needs

**When customers want to subscribe:**
1. Check what services they currently have
2. Ensure the requested service is available
3. Add the service to their subscription
4. Confirm activation and provide next steps

**When customers need service access:**
1. Check if the service is already deployed and ready
2. If not deployed, automatically deploy it for them
3. Provide the service endpoint URL
4. Explain how to make requests to the service

INTERACTION STYLE:

✓ **Be Friendly & Conversational**: Use natural, helpful language
✓ **Focus on Customer Needs**: Understand what they want to achieve
✓ **Explain Simply**: Avoid technical jargon (no mentions of ECR, Docker, App Runner internals, etc.)
✓ **Be Proactive**: Anticipate needs and offer helpful suggestions
✓ **Provide Clear Next Steps**: Tell customers exactly what they need to do
✓ **Handle Smoothly**: If something goes wrong, explain clearly and offer alternatives

✗ **Don't mention internal details**: AWS infrastructure, ECR repositories, Docker images, CPU/memory allocations, QCI values, bandwidth limits, auto-scaling configurations
✗ **Don't use technical jargon**: Stick to customer-friendly language
✗ **Don't overwhelm**: Give information in digestible pieces

EXAMPLE INTERACTIONS:

**Customer: "I need help analyzing images"**
You: "I can help you with that! We have several AI services for image analysis:
- Image Classification: Identifies what's in your images (like 'cat', 'car', 'building')
- Object Detection: Finds and labels multiple objects in images with their locations

Which sounds more useful for your needs?"

**Customer: "Add image classification to my account"**
You: "I'll add an image classification service to your subscription. Let me check what's available...

I found 'microsoft/resnet-50' - a powerful image classification service. I'm adding it to your subscription and setting it up now...

✓ Service added to your subscription
✓ Service is being deployed
✓ You'll be able to access it at: https://[endpoint-url]

The service should be ready in a few minutes. You can send images to that URL to get classification results!"

**Customer: "What AI services do I have?"**
You: "Let me check your current subscriptions...

You currently have:
- Image Classification Service (microsoft/resnet-50) - Status: Active
- Text Summarization Service - Status: Active

Would you like to add more services or get help using these?"

**Customer: "How do I use the image service?"**
You: "Your image classification service is available at: https://[endpoint-url]

To use it, send an image to this URL via HTTP POST request. The service will analyze the image and return what it identifies. Need help with the specific technical details of making requests?"

IMPORTANT REMINDERS:

- Always search the catalog before recommending services
- Verify services are deployed before giving customers endpoints
- Be patient and helpful with all questions
- Focus on solving customer problems, not showing off technical knowledge
- Celebrate successes: "Great! Your service is ready to use!"
- Note that the App Runner is also hosting the backend FastAPI server "ai_service_assistant_backend", which is NOT an AI service.

Your goal is to make AI services accessible and easy to use for everyone, regardless of their technical background.
"""

    async def invoke_agent(
        self,
        user_message: str = None,
        messages: List[Dict[str, Any]] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Invoke the local agent with a user message or conversation history.

        Args:
            user_message: Single user message (legacy format)
            messages: Full conversation history in format [{"role": "user|assistant", "content": [{"text": "..."}]}]
            session_id: Session ID (not used in local mode)

        Returns:
            Dict containing agent response
        """
        try:
            if not self.agent:
                raise Exception("Local agent not initialized. Make sure ENVIRONMENT=local and MCP servers are running.")

            # Determine input format
            if messages:
                # Convert messages format to simple text for the agent
                # The agent will handle the conversation context
                logger.info("Invoking local agent with conversation history")
                conversation_input = messages
                logger.info(f"Invoking local agent with {len(messages)} messages in history")
            elif user_message:
                # Single message format
                conversation_input = user_message
                logger.info(f"Invoking local agent with single message: {user_message[:100]}...")
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

                logger.info(f"Local agent response (first 100 chars): {response_text[:100]}...")

                return {
                    "response": response_text,
                    "session_id": session_id,
                    "trace": None,
                    "success": True
                }

        except Exception as e:
            logger.error(f"Error invoking local agent: {e}")
            return {
                "response": f"Error invoking local agent: {str(e)}",
                "session_id": session_id,
                "trace": None,
                "success": False,
                "error": str(e)
            }


# Global service instance (only initialized if ENVIRONMENT=local)
local_agent_service = LocalAgentService() if settings.environment == "local" else None
