from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    aws_region: str = "ap-northeast-2"
    bedrock_agent_id: str = "placeholder"
    bedrock_agent_alias_id: str = "placeholder"
    codef_client_id: str = ""
    codef_client_secret: str = ""

    # S3 — CODEF 원본 데이터 저장용
    s3_bucket_name: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""


    class Config:
        env_file = ".env"

settings = Settings()
