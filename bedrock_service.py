import boto3
import json
import requests
import urllib.parse
import logging
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)


class BedrockAgentCoreService:
    """Service for interacting with AWS Bedrock AgentCore Runtime API."""

    def __init__(self):
        """Initialize AWS clients and configuration."""
        self.region = settings.aws_region
        self.agent_name = settings.agent_name
        self.timeout = settings.request_timeout_seconds

        # Initialize AWS clients for SSM and Secrets Manager
        self.ssm_client = boto3.client('ssm', region_name=self.region)
        self.secrets_client = boto3.client('secretsmanager', region_name=self.region)
        self.cognito_client = boto3.client('cognito-idp', region_name=self.region)

        # NO CACHING - everything fetched fresh per request

    def _get_agent_arn(self) -> str:
        """
        Get agent ARN from SSM Parameter Store (fetched fresh each time).

        Returns:
            Agent ARN string
        """
        try:
            param_name = f'/agent/{self.agent_name}/runtime/agent_arn'
            logger.debug(f"Fetching agent ARN from SSM: {param_name}")
            response = self.ssm_client.get_parameter(
                Name=param_name
            )
            agent_arn = response["Parameter"]["Value"]
            logger.debug(f"Agent ARN retrieved: {agent_arn}")
            return agent_arn
        except Exception as e:
            logger.error(f"Failed to get agent ARN from SSM: {e}")
            raise

    def _get_cognito_credentials(self) -> Dict[str, str]:
        """
        Get Cognito credentials from Secrets Manager (fetched fresh each time).

        Returns:
            Dict with client_id, username, and password for Cognito authentication
        """
        try:
            secret_name = f'/agent/{self.agent_name}/cognito/credentials'
            logger.debug(f"Fetching Cognito credentials from Secrets Manager: {secret_name}")
            secret = self.secrets_client.get_secret_value(
                SecretId=secret_name
            )
            cognito_creds = json.loads(secret['SecretString'])

            return {
                'client_id': cognito_creds['client_id'],
                'username': cognito_creds.get('username', 'testuser'),
                'password': cognito_creds.get('password', 'MyPassword123!'),
                'pool_id': cognito_creds.get('pool_id'),
                'discovery_url': cognito_creds.get('discovery_url')
            }

        except Exception as e:
            logger.error(f"Failed to get Cognito credentials from Secrets Manager: {e}")
            raise

    def _get_fresh_token(self) -> str:
        """
        Authenticate with Cognito to get a FRESH token on each request.

        This matches the approach in test_agent.py which authenticates
        with username/password to get a fresh token every time.

        Returns:
            Fresh access token string from Cognito
        """
        try:
            credentials = self._get_cognito_credentials()

            logger.debug("Authenticating with Cognito to get fresh token...")

            # Authenticate with Cognito using username/password
            # This matches test_agent.py approach
            auth_response = self.cognito_client.initiate_auth(
                ClientId=credentials['client_id'],
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': credentials.get('username', 'testuser'),
                    'PASSWORD': credentials.get("password", 'MyPassword123!')
                }
            )

            access_token = auth_response['AuthenticationResult']['AccessToken']
            logger.debug("✓ Fresh token obtained from Cognito")
            return access_token

        except Exception as e:
            logger.error(f"Cognito authentication failed: {e}")
            raise

    async def invoke_agent(
        self,
        user_message: str = None,
        messages: list = None,
        session_id: str = None,
        enable_trace: bool = False
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock AgentCore with a user message or conversation history.

        All AWS resources (ARN, credentials, token) are fetched fresh on each request.

        Args:
            user_message: The user's input message (legacy format)
            messages: Full conversation history in format [{"role": "user|assistant", "content": [{"text": "..."}]}]
            session_id: Optional session ID for conversation continuity (not used in current API)
            enable_trace: Whether to enable trace information (not used in current API)

        Returns:
            Dict containing the agent's response and metadata
        """
        try:
            # Generate session ID for consistency
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())

            logger.info("Fetching all AWS resources fresh for this request...")

            # Fetch agent ARN from SSM (fresh each request)
            agent_arn = self._get_agent_arn()

            # Fetch Cognito credentials from Secrets Manager (fresh each request)
            # This also gets the fresh bearer token
            access_token = self._get_fresh_token()

            logger.info("✓ All AWS resources fetched successfully")

            # Construct API URL
            encoded_arn = urllib.parse.quote(agent_arn, safe='')
            url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations"

            # Prepare request
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Construct payload based on input format
            if messages:
                # New format: full conversation history
                payload = {"messages": messages}
                logger.info(f"Invoking agent at: {url}")
                logger.info(f"Sending conversation with {len(messages)} messages")
                logger.info(f"Latest message: {messages[-1]['content'][0]['text'][:100]}...")
            elif user_message:
                # Legacy format: single prompt
                payload = {"prompt": user_message}
                logger.info(f"Invoking agent at: {url}")
                logger.info(f"User prompt: {user_message[:100]}...")
            else:
                raise ValueError("Either user_message or messages must be provided")

            logger.debug(f"Request headers: {headers}")
            logger.debug(f"Request payload: {payload}")

            # Make request
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            logger.info(f"Response status: {response.status_code}")

            # Check for errors before raising
            if response.status_code != 200:
                logger.error(f"Error response body: {response.text}")
                response.raise_for_status()

            # Parse response
            if response.status_code == 200:
                response_data = response.json()

                # Extract text from various response formats
                response_text = None

                if isinstance(response_data, str):
                    response_text = response_data
                elif isinstance(response_data, dict):
                    # Format 1: AgentCore response with content array
                    # {"role": "assistant", "content": [{"text": "..."}]}
                    if 'content' in response_data and isinstance(response_data['content'], list):
                        if len(response_data['content']) > 0 and isinstance(response_data['content'][0], dict):
                            response_text = response_data['content'][0].get('text', '')

                    # Format 2: Direct text fields
                    if not response_text:
                        response_text = (
                            response_data.get('response') or
                            response_data.get('output') or
                            response_data.get('text') or
                            json.dumps(response_data)
                        )
                else:
                    response_text = str(response_data)

                logger.info(f"Extracted response text (first 100 chars): {response_text[:100]}...")

                return {
                    "response": response_text,
                    "session_id": session_id,
                    "trace": None,
                    "success": True
                }
            else:
                raise Exception(f"Unexpected status code: {response.status_code}")

        except requests.exceptions.HTTPError as e:
            # HTTP error with response body
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.json()
                    error_detail = f"{str(e)} - Response: {json.dumps(error_body)}"
                except:
                    error_detail = f"{str(e)} - Response: {e.response.text}"

            logger.error(f"HTTP error: {error_detail}")
            return {
                "response": f"Error invoking agent: {error_detail}",
                "session_id": session_id,
                "trace": None,
                "success": False,
                "error": error_detail
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "response": f"Error invoking agent: {str(e)}",
                "session_id": session_id,
                "trace": None,
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
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
        Invoke Bedrock agent with streaming response.

        Note: Streaming may not be supported by AgentCore Runtime API.
        This method falls back to regular invocation.

        Args:
            user_message: The user's input message
            session_id: Optional session ID for conversation continuity

        Yields:
            Response chunks
        """
        # AgentCore API may not support streaming, so we invoke and return the full response
        result = await self.invoke_agent(user_message, session_id)

        if result["success"]:
            yield json.dumps({"content": result["response"], "session_id": result["session_id"]})
        else:
            yield json.dumps({"error": result.get("error", "Unknown error"), "session_id": result["session_id"]})


# Global service instance
bedrock_service = BedrockAgentCoreService()
