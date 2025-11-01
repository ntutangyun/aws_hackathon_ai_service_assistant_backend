"""
MCP Client Service for direct MCP tool invocation.

This service connects directly to MCP servers deployed on AgentCore Runtime
and invokes their tools, following the pattern shown in tutorial scripts.
"""

import asyncio
import boto3
import json
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config import settings

logger = logging.getLogger(__name__)


class MCPClientService:
    """
    Service for connecting to MCP servers on AgentCore Runtime.

    Supports three MCP servers:
    1. UDM MCP Server - User subscription management
    2. Edge Server MCP Server - Edge infrastructure management
    3. Edge AI Service Repository MCP Server - AI service catalog
    """

    def __init__(self):
        self.region = settings.aws_region
        self.ssm_client = boto3.client('ssm', region_name=self.region)
        self.secrets_client = boto3.client('secretsmanager', region_name=self.region)
        self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
        self.timeout = 120

        # MCP server configurations
        self.mcp_servers = {
            'udm': {
                'name': 'UDM_mcp_server',
                'description': 'User subscription and data management',
                'ssm_prefix': '/mcp_server/udm'
            },
            'edge_server': {
                'name': 'edge_server_mcp_server',
                'description': 'Edge infrastructure management',
                'ssm_prefix': '/mcp_server/edge_server'
            },
            'ai_service': {
                'name': 'edge_ai_service_repository_mcp_server',
                'description': 'AI service catalog',
                'ssm_prefix': '/mcp_server/ai_service'
            }
        }

    def _get_mcp_credentials(self, server_key: str) -> Dict[str, str]:
        """
        Get MCP server credentials from AWS.

        Args:
            server_key: Key identifying the MCP server ('udm', 'edge_server', 'ai_service')

        Returns:
            Dictionary with agent_arn and bearer_token
        """
        server_config = self.mcp_servers.get(server_key)
        if not server_config:
            raise ValueError(f"Unknown MCP server: {server_key}")

        ssm_prefix = server_config['ssm_prefix']

        try:
            # Get agent ARN from SSM
            agent_arn_response = self.ssm_client.get_parameter(
                Name=f'{ssm_prefix}/runtime/agent_arn'
            )
            agent_arn = agent_arn_response['Parameter']['Value']
            logger.info(f"Retrieved Agent ARN for {server_config['name']}: {agent_arn}")

            # Get Cognito credentials from Secrets Manager
            secret_response = self.secrets_client.get_secret_value(
                SecretId=f'{ssm_prefix[1:]}/cognito/credentials'
            )
            cognito_creds = json.loads(secret_response['SecretString'])

            # Get client ID from SSM
            client_id_response = self.ssm_client.get_parameter(
                Name=f'{ssm_prefix}/runtime/client_id'
            )
            client_id = client_id_response['Parameter']['Value']

            # Authenticate with Cognito to get fresh token
            auth_response = self.cognito_client.initiate_auth(
                ClientId=client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': cognito_creds.get('username', 'testuser'),
                    'PASSWORD': cognito_creds.get("password", 'MyPassword123!')
                }
            )
            bearer_token = auth_response['AuthenticationResult']['AccessToken']
            logger.info(f"✓ Retrieved fresh bearer token for {server_config['name']}")

            return {
                'agent_arn': agent_arn,
                'bearer_token': bearer_token
            }

        except Exception as e:
            logger.error(f"Error retrieving credentials for {server_key}: {e}")
            raise

    @asynccontextmanager
    async def connect_to_mcp(self, server_key: str):
        """
        Create an async context manager for MCP session.

        Args:
            server_key: Key identifying the MCP server

        Yields:
            ClientSession connected to the MCP server

        Example:
            async with mcp_service.connect_to_mcp('udm') as session:
                result = await session.call_tool('get_all_subscriptions', {})
        """
        credentials = self._get_mcp_credentials(server_key)
        agent_arn = credentials['agent_arn']
        bearer_token = credentials['bearer_token']

        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        mcp_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

        headers = {
            "authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Connecting to MCP server: {self.mcp_servers[server_key]['name']}")
        logger.debug(f"MCP URL: {mcp_url}")

        async with streamablehttp_client(
            mcp_url,
            headers,
            timeout=self.timeout,
            terminate_on_close=False
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                logger.info("🔄 Initializing MCP session...")
                await session.initialize()
                logger.info("✓ MCP session initialized")
                yield session

    async def call_tool(
        self,
        server_key: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Call a specific MCP tool.

        Args:
            server_key: Key identifying the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments (optional)

        Returns:
            Tool result

        Example:
            result = await mcp_service.call_tool(
                'udm',
                'get_all_subscriptions',
                {}
            )
        """
        if arguments is None:
            arguments = {}

        try:
            async with self.connect_to_mcp(server_key) as session:
                logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
                result = await session.call_tool(name=tool_name, arguments=arguments)

                # Extract text content from result
                if hasattr(result, 'content') and len(result.content) > 0:
                    return result.content[0].text
                else:
                    return str(result)

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    async def list_tools(self, server_key: str) -> List[Dict[str, Any]]:
        """
        List available tools for an MCP server.

        Args:
            server_key: Key identifying the MCP server

        Returns:
            List of tool descriptions
        """
        try:
            async with self.connect_to_mcp(server_key) as session:
                tool_result = await session.list_tools()

                tools = []
                for tool in tool_result.tools:
                    tool_info = {
                        'name': tool.name,
                        'description': tool.description
                    }

                    # Add input schema if available
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        properties = tool.inputSchema.get('properties', {})
                        if properties:
                            tool_info['parameters'] = list(properties.keys())

                    tools.append(tool_info)

                return tools

        except Exception as e:
            logger.error(f"Error listing tools for {server_key}: {e}")
            raise

    # ============= UDM MCP Server Tools =============

    async def get_all_subscriptions(self) -> Any:
        """Get all user subscriptions from UDM MCP server."""
        return await self.call_tool('udm', 'get_all_subscriptions', {})

    async def get_subscription(self, subscriber_id: str) -> Any:
        """Get specific subscription details."""
        return await self.call_tool('udm', 'get_subscription', {'subscriber_id': subscriber_id})

    async def create_subscription(
        self,
        imsi: str,
        msisdn: str,
        subscriber_name: str,
        plan_type: str = "LIMITED",
        data_limit: int = 50
    ) -> Any:
        """Create a new subscription."""
        return await self.call_tool('udm', 'create_subscription', {
            'imsi': imsi,
            'msisdn': msisdn,
            'subscriber_name': subscriber_name,
            'plan_type': plan_type,
            'data_limit': data_limit
        })

    async def get_subscription_summary(self) -> Any:
        """Get subscription analytics."""
        return await self.call_tool('udm', 'get_subscription_summary', {})

    # ============= Edge Server MCP Server Tools =============

    async def get_all_edge_servers(self) -> Any:
        """Get all edge servers from Edge Server MCP."""
        return await self.call_tool('edge_server', 'get_all_edge_servers', {})

    async def get_edge_server(self, server_id: str) -> Any:
        """Get specific edge server details."""
        return await self.call_tool('edge_server', 'get_edge_server', {'server_id': server_id})

    async def get_server_health_status(self) -> Any:
        """Get health status of all edge servers."""
        return await self.call_tool('edge_server', 'get_server_health_status', {})

    async def get_network_summary(self) -> Any:
        """Get network-wide statistics."""
        return await self.call_tool('edge_server', 'get_network_summary', {})

    async def find_servers_with_capacity(
        self,
        min_cpu: Optional[int] = None,
        min_ram: Optional[int] = None,
        min_gpus: Optional[int] = None
    ) -> Any:
        """Find servers matching resource requirements."""
        args = {}
        if min_cpu is not None:
            args['min_cpu'] = min_cpu
        if min_ram is not None:
            args['min_ram'] = min_ram
        if min_gpus is not None:
            args['min_gpus'] = min_gpus

        return await self.call_tool('edge_server', 'find_servers_with_capacity', args)

    # ============= AI Service Repository MCP Server Tools =============

    async def get_all_services(self) -> Any:
        """Get all AI services from Service Repository MCP."""
        return await self.call_tool('ai_service', 'get_all_services', {})

    async def get_service(self, service_id: str) -> Any:
        """Get specific service details."""
        return await self.call_tool('ai_service', 'get_service', {'service_id': service_id})

    async def search_services(self, keyword: str) -> Any:
        """Search services by keyword."""
        return await self.call_tool('ai_service', 'search_services', {'keyword': keyword})

    async def get_categories(self) -> Any:
        """Get all service categories."""
        return await self.call_tool('ai_service', 'get_categories', {})

    async def get_catalog_summary(self) -> Any:
        """Get catalog statistics."""
        return await self.call_tool('ai_service', 'get_catalog_summary', {})


# Global MCP client service instance
mcp_client_service = MCPClientService()
