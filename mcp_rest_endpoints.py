"""
REST-style MCP endpoints for frontend integration.

These endpoints provide traditional REST API patterns for the frontend,
while the /6g/* endpoints provide query-based natural language interfaces.
Both use the same underlying MCP client service.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import json

from mcp_client_service import mcp_client_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP REST API"])


# ============= UDM (Unified Data Management) Endpoints =============

@router.get("/udm/subscriptions")
async def get_all_subscriptions(status: Optional[str] = Query(None)):
    """
    Get all user subscriptions with optional status filter.

    Query Parameters:
        status: Optional filter by status (ACTIVE, SUSPENDED, TERMINATED)
    """
    try:
        logger.info(f"Fetching all subscriptions (status={status})")

        # Call MCP tool
        result = await mcp_client_service.call_tool(
            'udm',
            'get_all_subscriptions',
            {'status': status} if status else {}
        )

        # Parse result
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/udm/subscriptions/{subscriber_id}")
async def get_subscription(subscriber_id: str):
    """Get a specific subscription by subscriber ID."""
    try:
        logger.info(f"Fetching subscription: {subscriber_id}")

        result = await mcp_client_service.get_subscription(subscriber_id)
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching subscription {subscriber_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/udm/summary")
async def get_subscription_summary():
    """Get subscription analytics summary."""
    try:
        logger.info("Fetching subscription summary")

        result = await mcp_client_service.get_subscription_summary()
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching subscription summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/udm/subscriptions/{subscriber_id}/qos")
async def get_qos_profile(subscriber_id: str):
    """Get QoS profile for a subscription."""
    try:
        logger.info(f"Fetching QoS profile for: {subscriber_id}")

        result = await mcp_client_service.call_tool(
            'udm',
            'get_qos_profile',
            {'subscriber_id': subscriber_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching QoS profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/udm/subscriptions/{subscriber_id}/edge-ai")
async def get_edge_ai_subscriptions(subscriber_id: str):
    """Get Edge AI service subscriptions for a user."""
    try:
        logger.info(f"Fetching Edge AI subscriptions for: {subscriber_id}")

        result = await mcp_client_service.call_tool(
            'udm',
            'get_edge_ai_subscriptions',
            {'subscriber_id': subscriber_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching Edge AI subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Edge Server Endpoints =============

@router.get("/edge/servers")
async def get_all_edge_servers(
    status: Optional[str] = Query(None),
    health: Optional[str] = Query(None)
):
    """
    Get all edge servers with optional filters.

    Query Parameters:
        status: Filter by status (ONLINE, OFFLINE, MAINTENANCE)
        health: Filter by health (HEALTHY, WARNING, CRITICAL)
    """
    try:
        logger.info(f"Fetching all edge servers (status={status}, health={health})")

        args = {}
        if status:
            args['status'] = status
        if health:
            args['health'] = health

        result = await mcp_client_service.call_tool(
            'edge_server',
            'get_all_edge_servers',
            args
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching edge servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/servers/{server_id}")
async def get_edge_server(server_id: str):
    """Get detailed information about a specific edge server."""
    try:
        logger.info(f"Fetching edge server: {server_id}")

        result = await mcp_client_service.get_edge_server(server_id)
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching edge server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/servers/{server_id}/resources")
async def get_server_resources(server_id: str):
    """Get resource information (CPU, RAM, storage) for an edge server."""
    try:
        logger.info(f"Fetching resources for server: {server_id}")

        result = await mcp_client_service.call_tool(
            'edge_server',
            'get_server_resources',
            {'server_id': server_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching server resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/servers/{server_id}/gpu")
async def get_gpu_resources(server_id: str):
    """Get GPU resources for an edge server."""
    try:
        logger.info(f"Fetching GPU resources for server: {server_id}")

        result = await mcp_client_service.call_tool(
            'edge_server',
            'get_gpu_resources',
            {'server_id': server_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching GPU resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/servers/{server_id}/services")
async def get_deployed_services(server_id: str):
    """Get deployed services on an edge server."""
    try:
        logger.info(f"Fetching deployed services for server: {server_id}")

        result = await mcp_client_service.call_tool(
            'edge_server',
            'get_deployed_services',
            {'server_id': server_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching deployed services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/network-summary")
async def get_network_summary():
    """Get summary of the entire edge network."""
    try:
        logger.info("Fetching network summary")

        result = await mcp_client_service.get_network_summary()
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching network summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/health-status")
async def get_health_status():
    """Get health status of all edge servers."""
    try:
        logger.info("Fetching health status")

        result = await mcp_client_service.get_server_health_status()
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge/servers/find-capacity")
async def find_servers_with_capacity(
    min_cpu: Optional[int] = Query(None),
    min_ram: Optional[int] = Query(None),
    min_gpus: Optional[int] = Query(None)
):
    """Find edge servers with available capacity matching requirements."""
    try:
        logger.info(f"Finding servers with capacity (cpu={min_cpu}, ram={min_ram}, gpus={min_gpus})")

        args = {}
        if min_cpu is not None:
            args['min_cpu'] = min_cpu
        if min_ram is not None:
            args['min_ram'] = min_ram
        if min_gpus is not None:
            args['min_gpus'] = min_gpus

        result = await mcp_client_service.call_tool(
            'edge_server',
            'find_servers_with_capacity',
            args
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error finding servers with capacity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= AI Service Repository Endpoints =============

@router.get("/ai-services/services")
async def get_all_ai_services(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    gpu_required: Optional[bool] = Query(None)
):
    """
    Get all AI services with optional filters.

    Query Parameters:
        category: Filter by category (COMPUTER_VISION, NLP, etc.)
        status: Filter by status (ACTIVE, DEPRECATED)
        gpu_required: Filter by GPU requirement (true/false)
    """
    try:
        logger.info(f"Fetching all AI services (category={category}, status={status}, gpu={gpu_required})")

        args = {}
        if category:
            args['category'] = category
        if status:
            args['status'] = status
        if gpu_required is not None:
            args['gpu_required'] = gpu_required

        result = await mcp_client_service.call_tool(
            'ai_service',
            'get_all_services',
            args
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching AI services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/services/{service_id}")
async def get_ai_service(service_id: str):
    """Get detailed information about a specific AI service."""
    try:
        logger.info(f"Fetching AI service: {service_id}")

        result = await mcp_client_service.get_service(service_id)
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching AI service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/services/search")
async def search_ai_services(keyword: str = Query(...)):
    """Search AI services by keyword."""
    try:
        logger.info(f"Searching AI services with keyword: {keyword}")

        result = await mcp_client_service.search_services(keyword)
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error searching AI services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/categories")
async def get_service_categories():
    """Get all AI service categories."""
    try:
        logger.info("Fetching service categories")

        result = await mcp_client_service.get_categories()
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/summary")
async def get_catalog_summary():
    """Get summary statistics of the AI service catalog."""
    try:
        logger.info("Fetching catalog summary")

        result = await mcp_client_service.get_catalog_summary()
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching catalog summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/services/{service_id}/requirements")
async def get_service_requirements(service_id: str):
    """Get resource requirements for a specific AI service."""
    try:
        logger.info(f"Fetching requirements for service: {service_id}")

        result = await mcp_client_service.call_tool(
            'ai_service',
            'get_service_requirements',
            {'service_id': service_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching service requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/services/{service_id}/deployment")
async def get_deployment_info(service_id: str):
    """Get deployment configuration for a specific AI service."""
    try:
        logger.info(f"Fetching deployment info for service: {service_id}")

        result = await mcp_client_service.call_tool(
            'ai_service',
            'get_deployment_info',
            {'service_id': service_id}
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error fetching deployment info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-services/services/find-by-resources")
async def find_services_by_resources(
    max_cpu: Optional[int] = Query(None),
    max_ram: Optional[int] = Query(None),
    max_gpu_memory: Optional[int] = Query(None)
):
    """Find AI services matching resource constraints."""
    try:
        logger.info(f"Finding services by resources (cpu={max_cpu}, ram={max_ram}, gpu={max_gpu_memory})")

        args = {}
        if max_cpu is not None:
            args['max_cpu'] = max_cpu
        if max_ram is not None:
            args['max_ram'] = max_ram
        if max_gpu_memory is not None:
            args['max_gpu_memory'] = max_gpu_memory

        result = await mcp_client_service.call_tool(
            'ai_service',
            'find_services_by_resources',
            args
        )
        parsed_result = json.loads(result) if isinstance(result, str) else result
        return parsed_result

    except Exception as e:
        logger.error(f"Error finding services by resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))
