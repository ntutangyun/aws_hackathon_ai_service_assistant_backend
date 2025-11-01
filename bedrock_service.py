import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

# Import agent services based on environment
if settings.environment == "local":
    try:
        from local_agent_service import local_agent_service
        if local_agent_service is not None:
            logger.info("✅ Local agent service imported and initialized successfully")
        else:
            logger.error("❌ Local agent service imported but is None - initialization may have failed")
        cloud_agent_service = None
    except Exception as e:
        logger.error(f"❌ Failed to import local agent service: {e}")
        import traceback
        traceback.print_exc()
        local_agent_service = None
        cloud_agent_service = None
else:
    local_agent_service = None
    try:
        from cloud_agent_service import cloud_agent_service
        if cloud_agent_service is not None:
            logger.info("✅ Cloud agent service imported and initialized successfully")
        else:
            logger.error("❌ Cloud agent service imported but is None - initialization may have failed")
    except Exception as e:
        logger.error(f"❌ Failed to import cloud agent service: {e}")
        import traceback
        traceback.print_exc()
        cloud_agent_service = None


class BedrockAgentCoreService:
    """
    Service for routing agent invocations to local or cloud agent services.

    This is now a lightweight router that delegates to:
    - local_agent_service (when ENVIRONMENT=local)
    - cloud_agent_service (when ENVIRONMENT=production)
    """

    def __init__(self):
        """Initialize the service router."""
        logger.info("BedrockAgentCoreService initialized as agent router")

    async def invoke_agent(
        self,
        user_message: str = None,
        messages: list = None,
        session_id: str = None,
        enable_trace: bool = False
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock AgentCore with a user message or conversation history.

        Routes to local agent (ENVIRONMENT=local) or AWS AgentCore Runtime (ENVIRONMENT=production).

        Args:
            user_message: The user's input message (legacy format)
            messages: Full conversation history in format [{"role": "user|assistant", "content": [{"text": "..."}]}]
            session_id: Optional session ID for conversation continuity (not used in current API)
            enable_trace: Whether to enable trace information (not used in current API)

        Returns:
            Dict containing the agent's response and metadata
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())

            # Route to local agent if in local mode
            if settings.environment == "local":
                if local_agent_service is None:
                    raise Exception("Local agent service not available. Check if strands is installed and MCP servers are running.")

                logger.info("🏠 Using local agent service")
                return await local_agent_service.invoke_agent(
                    user_message=user_message,
                    messages=messages,
                    session_id=session_id
                )

            # Otherwise use cloud agent service (production mode)
            logger.info("☁️ Using cloud agent service with AWS AgentCore Runtime MCP servers")
            if cloud_agent_service is None:
                raise Exception("Cloud agent service not available. Check AWS credentials and MCP server deployment.")

            return await cloud_agent_service.invoke_agent(
                user_message=user_message,
                messages=messages,
                session_id=session_id
            )

            # Legacy HTTP API code path (no longer used)
            # Now using cloud_agent_service which connects to MCP servers directly

        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            return {
                "response": f"Error invoking agent: {str(e)}",
                "session_id": session_id,
                "trace": None,
                "success": False,
                "error": str(e)
            }

    async def invoke_agent_stream(
        self,
        user_message: str,
        session_id: str = None
    ):
        """
        Invoke agent with streaming response (falls back to regular invocation).

        Args:
            user_message: The user's input message
            session_id: Optional session ID for conversation continuity

        Yields:
            Response chunks
        """
        import json

        # Invoke and return the full response as a stream
        result = await self.invoke_agent(user_message, session_id)

        if result["success"]:
            yield json.dumps({"content": result["response"], "session_id": result["session_id"]})
        else:
            yield json.dumps({"error": result.get("error", "Unknown error"), "session_id": result["session_id"]})


# Global service instance
bedrock_service = BedrockAgentCoreService()
