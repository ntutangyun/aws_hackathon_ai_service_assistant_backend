from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment detection
    environment: str = "local"  # "local" or "production"

    # AWS Configuration
    aws_region: str = "us-east-1"

    # Bedrock AgentCore Configuration
    # Agent name is used to construct SSM/Secrets Manager paths
    agent_name: str = "ai_assistant_agent"

    # Request timeout
    request_timeout_seconds: int = 300

    # API Configuration
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    api_port: int = 8000

    # ============= MCP Server Configuration =============

    # Local MCP server configuration (for local development)
    # When ENVIRONMENT=local, the backend connects to these local MCP servers
    local_udm_port: int = 9001
    local_edge_server_port: int = 9002
    local_ai_service_port: int = 9003

    # AWS AgentCore Runtime MCP server configuration (for production)
    # When ENVIRONMENT=production, the backend connects to MCP servers deployed on AWS AgentCore Runtime
    # URLs and authentication credentials are fetched from:
    # - SSM Parameter Store: /mcp/{server_type}/runtime/url
    # - Secrets Manager: /mcp/{server_type}/cognito/credentials
    # where server_type is 'udm', 'edge_server', or 'ai_service'

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
