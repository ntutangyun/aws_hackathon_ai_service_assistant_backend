"""
MCP-aware endpoints for 6G Edge AI Network Management.

These endpoints leverage the three MCP servers deployed on AgentCore Runtime:
1. UDM_mcp_server (port 9003) - User subscription management
2. edge_server_mcp_server (port 9001) - Edge server infrastructure management
3. edge_ai_service_repository_mcp_server (port 9002) - AI service catalog

When the agent is deployed on AgentCore with these MCP servers,
it can invoke their tools to manage the 6G edge network.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json

from mcp_client_service import mcp_client_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/6g", tags=["6G Edge AI Network"])


# ============= Request/Response Models =============

class MCPRequest(BaseModel):
    """Base request for MCP-powered operations."""
    query: str
    session_id: Optional[str] = None


class SubscriptionQuery(BaseModel):
    """Query for subscription operations."""
    query: str
    subscriber_id: Optional[str] = None
    session_id: Optional[str] = None


class EdgeServerQuery(BaseModel):
    """Query for edge server operations."""
    query: str
    server_id: Optional[str] = None
    session_id: Optional[str] = None


class ServiceCatalogQuery(BaseModel):
    """Query for AI service catalog operations."""
    query: str
    service_id: Optional[str] = None
    category: Optional[str] = None
    session_id: Optional[str] = None


class DeploymentRequest(BaseModel):
    """Request to deploy an AI service."""
    service_id: str
    server_id: Optional[str] = None  # If not specified, agent will find best server
    instances: int = 1
    session_id: Optional[str] = None


class SubscriptionCreateRequest(BaseModel):
    """Request to create a new subscription."""
    imsi: str
    msisdn: str
    subscriber_name: str
    plan_type: str = "LIMITED"
    data_limit: int = 50
    session_id: Optional[str] = None


# ============= Subscription Management Endpoints =============

@router.post("/subscriptions/query")
async def query_subscriptions(request: SubscriptionQuery):
    """
    Query user subscriptions using direct MCP tool invocation.

    The endpoint will use UDM MCP server tools to answer questions like:
    - "Show me all active subscriptions"
    - "Get subscription details for sub-001"
    - "What is the data usage for subscriber sub-002?"
    - "List all users with Edge AI subscriptions"

    Example request:
    {
      "query": "Show me all active subscriptions with their data usage",
      "subscriber_id": "sub-001"  // optional, for specific subscriber
    }
    """
    try:
        logger.info(f"Processing subscription query: {request.query}")

        # If specific subscriber requested, get that subscription
        if request.subscriber_id:
            logger.info(f"Fetching subscription for subscriber: {request.subscriber_id}")
            result = await mcp_client_service.get_subscription(request.subscriber_id)
        else:
            # Otherwise get all subscriptions
            logger.info("Fetching all subscriptions")
            result = await mcp_client_service.get_all_subscriptions()

        # Parse the result (it comes as JSON string from MCP)
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "query": request.query,
            "mcp_server": "UDM_mcp_server",
            "tool_used": "get_subscription" if request.subscriber_id else "get_all_subscriptions",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error querying subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/create")
async def create_subscription(request: SubscriptionCreateRequest):
    """
    Create a new user subscription using direct MCP tool invocation.

    Example request:
    {
      "imsi": "310150999888777",
      "msisdn": "+1555000999",
      "subscriber_name": "John Doe",
      "plan_type": "UNLIMITED",
      "data_limit": 100
    }
    """
    try:
        logger.info(f"Creating subscription for {request.subscriber_name}")

        result = await mcp_client_service.create_subscription(
            imsi=request.imsi,
            msisdn=request.msisdn,
            subscriber_name=request.subscriber_name,
            plan_type=request.plan_type,
            data_limit=request.data_limit
        )

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "mcp_server": "UDM_mcp_server",
            "tool_used": "create_subscription",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscriber_id}/edge-ai")
async def manage_edge_ai_subscription(subscriber_id: str, request: MCPRequest):
    """
    Manage Edge AI service subscriptions for a user.

    Examples:
    - "Add video analytics service with high priority"
    - "Show all my Edge AI subscriptions"
    - "Remove service ai-gaming-001"
    - "Update usage for service ai-video-001"
    """
    return {
        "endpoint": f"/6g/subscriptions/{subscriber_id}/edge-ai",
        "description": "Manage Edge AI services for subscriber",
        "subscriber_id": subscriber_id,
        "query": request.query,
        "mcp_tools": [
            "get_edge_ai_subscriptions",
            "add_edge_ai_subscription",
            "update_edge_ai_service_status",
            "remove_edge_ai_subscription",
            "update_edge_ai_usage"
        ]
    }


@router.get("/subscriptions/analytics")
async def subscription_analytics():
    """
    Get subscription analytics and summary using direct MCP tool invocation.
    """
    try:
        logger.info("Fetching subscription analytics")

        result = await mcp_client_service.get_subscription_summary()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "mcp_server": "UDM_mcp_server",
            "tool_used": "get_subscription_summary",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error fetching subscription analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Edge Server Management Endpoints =============

@router.post("/edge-servers/query")
async def query_edge_servers(request: EdgeServerQuery):
    """
    Query edge servers using direct MCP tool invocation.

    Examples:
    - "Show all online edge servers"
    - "Which servers have available GPU capacity?"
    - "Get details for edge-001"
    - "Find servers with at least 32GB available memory"
    - "Show servers with WARNING health status"
    """
    try:
        logger.info(f"Processing edge server query: {request.query}")

        # If specific server requested, get that server
        if request.server_id:
            logger.info(f"Fetching edge server: {request.server_id}")
            result = await mcp_client_service.get_edge_server(request.server_id)
        else:
            # Otherwise get all servers
            logger.info("Fetching all edge servers")
            result = await mcp_client_service.get_all_edge_servers()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "query": request.query,
            "mcp_server": "edge_server_mcp_server",
            "tool_used": "get_edge_server" if request.server_id else "get_all_edge_servers",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error querying edge servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edge-servers/find-capacity")
async def find_server_capacity(request: MCPRequest):
    """
    Find edge servers with available capacity for specific requirements.

    Examples:
    - "Find servers with 16 CPU cores and 64GB RAM available"
    - "Which servers can handle a GPU workload with 40GB GPU memory?"
    - "Show me servers with at least 2 GPUs available"
    """
    return {
        "endpoint": "/6g/edge-servers/find-capacity",
        "description": "Find servers matching resource requirements",
        "query": request.query,
        "mcp_tool": "find_servers_with_capacity"
    }


@router.get("/edge-servers/network-summary")
async def edge_network_summary():
    """
    Get summary of the entire edge network using direct MCP tool invocation.

    Returns overall statistics about servers, resources, and deployments.
    """
    try:
        logger.info("Fetching edge network summary")

        result = await mcp_client_service.get_network_summary()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "mcp_server": "edge_server_mcp_server",
            "tool_used": "get_network_summary",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error fetching network summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge-servers/health")
async def edge_servers_health():
    """
    Get health status of all edge servers using direct MCP tool invocation.

    Returns health information and resource utilization for all servers.
    """
    try:
        logger.info("Fetching edge servers health status")

        result = await mcp_client_service.get_server_health_status()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "mcp_server": "edge_server_mcp_server",
            "tool_used": "get_server_health_status",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error fetching server health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edge-servers/{server_id}/deployments")
async def manage_deployments(server_id: str, request: MCPRequest):
    """
    Manage service deployments on a specific edge server.

    Examples:
    - "Show all deployed services"
    - "Deploy video analytics service with 3 instances"
    - "Undeploy service dep-001"
    - "Update metrics for deployment dep-002"
    """
    return {
        "endpoint": f"/6g/edge-servers/{server_id}/deployments",
        "description": "Manage deployments on edge server",
        "server_id": server_id,
        "query": request.query,
        "mcp_tools": [
            "get_deployed_services",
            "deploy_service",
            "undeploy_service",
            "update_service_metrics"
        ]
    }


# ============= AI Service Catalog Endpoints =============

@router.post("/services/query")
async def query_services(request: ServiceCatalogQuery):
    """
    Query AI service catalog using direct MCP tool invocation.

    Examples:
    - "Show all available AI services"
    - "Find video analytics services"
    - "What GPU-accelerated services are available?"
    - "Search for gaming services"
    - "Show services in COMPUTER_VISION category"
    """
    try:
        logger.info(f"Processing service catalog query: {request.query}")

        # If specific service requested, get that service
        if request.service_id:
            logger.info(f"Fetching service: {request.service_id}")
            result = await mcp_client_service.get_service(request.service_id)
        # If search query provided, search services
        elif "search" in request.query.lower() or "find" in request.query.lower():
            # Extract keyword from query (simple approach)
            keywords = request.query.lower().replace("search", "").replace("find", "").replace("for", "").strip()
            logger.info(f"Searching services with keyword: {keywords}")
            result = await mcp_client_service.search_services(keywords)
        else:
            # Otherwise get all services
            logger.info("Fetching all services")
            result = await mcp_client_service.get_all_services()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "query": request.query,
            "mcp_server": "edge_ai_service_repository_mcp_server",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error querying services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/categories")
async def service_categories():
    """
    Get all service categories with counts using direct MCP tool invocation.

    Returns categories like COMPUTER_VISION, GAMING, NLP, etc.
    """
    try:
        logger.info("Fetching service categories")

        result = await mcp_client_service.get_categories()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "mcp_server": "edge_ai_service_repository_mcp_server",
            "tool_used": "get_categories",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/catalog-summary")
async def catalog_summary():
    """
    Get summary statistics of the service catalog using direct MCP tool invocation.
    """
    try:
        logger.info("Fetching catalog summary")

        result = await mcp_client_service.get_catalog_summary()

        # Parse the result
        try:
            parsed_result = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed_result = {"raw_result": result}

        return {
            "success": True,
            "mcp_server": "edge_ai_service_repository_mcp_server",
            "tool_used": "get_catalog_summary",
            "data": parsed_result
        }

    except Exception as e:
        logger.error(f"Error fetching catalog summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/{service_id}/requirements")
async def service_requirements(service_id: str):
    """
    Get resource requirements for a specific service.
    """
    return {
        "endpoint": f"/6g/services/{service_id}/requirements",
        "description": "Get service resource requirements",
        "service_id": service_id,
        "mcp_tool": "get_service_requirements"
    }


@router.get("/services/{service_id}/deployment-info")
async def service_deployment_info(service_id: str):
    """
    Get deployment information for a service.
    """
    return {
        "endpoint": f"/6g/services/{service_id}/deployment-info",
        "description": "Get service deployment configuration",
        "service_id": service_id,
        "mcp_tool": "get_deployment_info"
    }


# ============= Intelligent Deployment Endpoints =============

@router.post("/deploy/smart")
async def smart_deploy(request: DeploymentRequest):
    """
    Intelligently deploy an AI service to the best edge server.

    The agent will:
    1. Get service requirements using get_service_requirements
    2. Find suitable servers using find_servers_with_capacity
    3. Deploy to the best server using deploy_service

    Example request:
    {
      "service_id": "svc-video-analytics-v1",
      "instances": 2,
      "server_id": "edge-001"  // optional, agent will find best if not provided
    }
    """
    return {
        "endpoint": "/6g/deploy/smart",
        "description": "Intelligent service deployment across MCP servers",
        "service_id": request.service_id,
        "instances": request.instances,
        "target_server": request.server_id or "Auto-select best server",
        "workflow": [
            "1. Get service requirements from AI Service Catalog MCP",
            "2. Find servers with capacity from Edge Server MCP",
            "3. Select optimal server based on utilization and location",
            "4. Deploy service using Edge Server MCP",
            "5. Return deployment confirmation"
        ]
    }


@router.post("/workflows/new-subscriber-onboarding")
async def new_subscriber_workflow(request: SubscriptionCreateRequest):
    """
    Complete workflow for onboarding a new subscriber with Edge AI services.

    The agent will orchestrate across multiple MCP servers:
    1. Create subscription (UDM MCP)
    2. Show recommended AI services (Service Catalog MCP)
    3. Find nearby edge servers (Edge Server MCP)
    4. Set up initial Edge AI subscriptions (UDM MCP)
    """
    return {
        "endpoint": "/6g/workflows/new-subscriber-onboarding",
        "description": "Complete subscriber onboarding workflow",
        "workflow": "Multi-MCP orchestration for new subscriber setup",
        "mcp_servers_involved": [
            "UDM_mcp_server",
            "edge_ai_service_repository_mcp_server",
            "edge_server_mcp_server"
        ]
    }


@router.post("/analytics/comprehensive")
async def comprehensive_analytics(request: MCPRequest):
    """
    Get comprehensive analytics across all systems.

    The agent will gather data from all three MCP servers:
    - Subscription statistics (UDM)
    - Network resource utilization (Edge Servers)
    - Service catalog status (AI Services)

    Examples:
    - "Give me a complete overview of the 6G network"
    - "Show me all analytics dashboards"
    - "What's the current utilization across all systems?"
    """
    return {
        "endpoint": "/6g/analytics/comprehensive",
        "description": "Comprehensive analytics from all MCP servers",
        "query": request.query,
        "data_sources": [
            "Subscription summary (UDM)",
            "Network summary (Edge Servers)",
            "Catalog summary (AI Services)"
        ]
    }


# ============= Search and Discovery =============

@router.post("/search/global")
async def global_search(request: MCPRequest):
    """
    Search across all MCP servers.

    The agent will intelligently search:
    - Subscriptions by IMSI/MSISDN/name
    - Edge servers by name/location
    - AI services by name/description/capabilities

    Example: "Find anything related to video analytics"
    """
    return {
        "endpoint": "/6g/search/global",
        "description": "Global search across all MCP servers",
        "query": request.query,
        "search_scope": [
            "User subscriptions",
            "Edge servers",
            "AI services"
        ]
    }


# ============= Recommendations =============

@router.get("/recommendations/services/{subscriber_id}")
async def recommend_services(subscriber_id: str):
    """
    Recommend AI services for a subscriber based on their usage patterns.

    The agent will:
    1. Get subscriber info and current subscriptions (UDM)
    2. Analyze usage patterns
    3. Find complementary services (Service Catalog)
    4. Check nearby edge server capabilities
    """
    return {
        "endpoint": f"/6g/recommendations/services/{subscriber_id}",
        "description": "AI service recommendations for subscriber",
        "subscriber_id": subscriber_id,
        "workflow": "Cross-MCP analysis for personalized recommendations"
    }


@router.get("/recommendations/deployment/{service_id}")
async def recommend_deployment_location(service_id: str, subscriber_id: Optional[str] = None):
    """
    Recommend best edge server for deploying a service.

    Considers:
    - Service resource requirements
    - Server capacity and location
    - Subscriber location (if provided)
    - Current server load
    """
    return {
        "endpoint": f"/6g/recommendations/deployment/{service_id}",
        "description": "Edge server recommendation for service deployment",
        "service_id": service_id,
        "subscriber_id": subscriber_id,
        "factors": [
            "Resource requirements vs availability",
            "Geographic proximity",
            "Current server utilization",
            "QoS requirements"
        ]
    }
