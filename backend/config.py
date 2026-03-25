from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    aws_region: str = "us-east-1"
    bedrock_agent_id: str = "placeholder"
    bedrock_agent_alias_id: str = "placeholder"
    
    class Config:
        env_file = ".env"

settings = Settings()
