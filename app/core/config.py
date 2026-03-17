from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    aws_region: str = "ap-northeast-2"
    bedrock_agent_id: str = "placeholder"
    bedrock_agent_alias_id: str = "placeholder"

    class Config:
        env_file = ".env"

settings = Settings()
