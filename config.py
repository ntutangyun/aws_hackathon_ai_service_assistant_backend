from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

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

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
