from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging

from config import settings
from bedrock_service import bedrock_service
from mcp_rest_endpoints import router as mcp_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enable debug logging for bedrock_service
logging.getLogger('bedrock_service').setLevel(logging.DEBUG)

# Initialize FastAPI app
app = FastAPI(
    title="AI Service Assistant",
    description="Backend API for chatbot powered by AWS Bedrock",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include MCP REST endpoints
app.include_router(mcp_router)


# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Server startup logging."""
    logger.info("=" * 60)
    logger.info("Starting AI Service Assistant Backend")
    logger.info("=" * 60)
    logger.info("Auth Mode: Fully Dynamic (no caching)")
    logger.info("- Agent ARN: Fetched from SSM per request")
    logger.info("- Cognito Creds: Fetched from Secrets Manager per request")
    logger.info("- Bearer Token: Fetched fresh per request")
    logger.info("=" * 60)
    logger.info("Server ready to accept requests")
    logger.info("=" * 60)


# Request/Response models
class MessageContent(BaseModel):
    """Message content model."""
    text: str

class ConversationMessage(BaseModel):
    """Conversation message model."""
    role: str  # "user" or "assistant"
    content: list[MessageContent]

class ChatRequest(BaseModel):
    """Chat request model."""
    message: Optional[str] = None  # For backward compatibility
    messages: Optional[list[ConversationMessage]] = None  # New conversation history format
    session_id: Optional[str] = None
    enable_trace: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    success: bool
    error: Optional[str] = None


class StreamChatRequest(BaseModel):
    """Streaming chat request model."""
    message: str
    session_id: Optional[str] = None


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-service-assistant",
        "version": "1.0.0",
        "auth_mode": "fully-dynamic",
        "caching": "disabled"
    }


# Test endpoint for oran_agent
@app.get("/test-agent")
async def test_agent():
    """
    Test endpoint to verify oran_agent connectivity.
    Uses a predefined test prompt to check if the agent responds correctly.

    Returns:
        Test result with agent response
    """
    try:
        # Test prompt
        test_prompt = "Using the O2 interface, do I have any O-Cloud resources supplied by Intel?"

        logger.info("Testing oran_agent with predefined prompt...")

        # Invoke the agent (authentication happens per request)
        result = await bedrock_service.invoke_agent(
            user_message=test_prompt,
            session_id="test-session",
            enable_trace=False
        )

        if result["success"]:
            return {
                "status": "success",
                "test_prompt": test_prompt,
                "agent_response": result["response"],
                "session_id": result["session_id"],
                "message": "✓ Agent responded successfully"
            }
        else:
            return {
                "status": "error",
                "test_prompt": test_prompt,
                "error": result.get("error", "Unknown error"),
                "message": "✗ Agent invocation failed"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Custom test endpoint with user-provided prompt
@app.post("/test-agent")
async def test_agent_custom(request: ChatRequest):
    """
    Test endpoint with custom prompt.
    Similar to /chat but designed for testing purposes.

    Args:
        request: ChatRequest containing the test message

    Returns:
        Test result with agent response
    """
    try:
        logger.info(f"Testing oran_agent with custom prompt: {request.message[:50]}...")

        # Invoke the agent (authentication happens per request)
        result = await bedrock_service.invoke_agent(
            user_message=request.message,
            session_id=request.session_id or "test-session",
            enable_trace=request.enable_trace
        )

        return {
            "status": "success" if result["success"] else "error",
            "test_prompt": request.message,
            "agent_response": result["response"],
            "session_id": result["session_id"],
            "success": result["success"],
            "error": result.get("error")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent and receive a response.

    Args:
        request: ChatRequest containing the user message(s) and optional session ID

    Returns:
        ChatResponse with the agent's response and session information
    """
    try:
        # Handle both old format (single message) and new format (messages array)
        if request.messages:
            # New format: full conversation history
            # Convert to dict format for the agent
            messages_dict = [
                {
                    "role": msg.role,
                    "content": [{"text": content.text} for content in msg.content]
                }
                for msg in request.messages
            ]
            logger.info(f"Received chat request with {len(messages_dict)} messages in conversation history")
            logger.info(f"Latest message: {messages_dict[-1]['content'][0]['text'][:50]}...")

            # Invoke the Bedrock agent with full conversation history
            result = await bedrock_service.invoke_agent(
                messages=messages_dict,
                session_id=request.session_id,
                enable_trace=request.enable_trace
            )
        elif request.message:
            # Old format: single message (for backward compatibility)
            logger.info(f"Received chat request (legacy format): {request.message[:50]}...")

            # Invoke the Bedrock agent with single message
            result = await bedrock_service.invoke_agent(
                user_message=request.message,
                session_id=request.session_id,
                enable_trace=request.enable_trace
            )
        else:
            raise HTTPException(status_code=400, detail="Either 'message' or 'messages' must be provided")

        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            success=result["success"],
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Streaming chat endpoint
@app.post("/chat/stream")
async def chat_stream(request: StreamChatRequest):
    """
    Send a message to the AI agent and receive a streaming response.

    Args:
        request: StreamChatRequest containing the user message and optional session ID

    Returns:
        StreamingResponse with the agent's response chunks
    """
    try:
        logger.info(f"Received streaming chat request: {request.message[:50]}...")

        # Return streaming response
        return StreamingResponse(
            bedrock_service.invoke_agent_stream(
                user_message=request.message,
                session_id=request.session_id
            ),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error processing streaming chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Sessions endpoint to manage conversation sessions
@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a conversation session.

    Args:
        session_id: The session ID to delete

    Returns:
        Success status
    """
    # In a production environment, you would delete session data from a database
    # For now, this is a placeholder
    logger.info(f"Delete session requested: {session_id}")
    return {"success": True, "message": f"Session {session_id} deleted"}


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
