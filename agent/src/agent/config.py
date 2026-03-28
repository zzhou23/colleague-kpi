from pydantic_settings import BaseSettings


class AgentConfig(BaseSettings):
    server_url: str = "http://localhost:8000"
    api_key: str = ""
    claude_dir: str = "~/.claude"
    schedule_hour: int = 0
    schedule_minute: int = 0

    model_config = {"env_prefix": "APR_AGENT_"}
