from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # DATABASE_URL 직접 주입 또는 개별 변수로 조합 (ECS 환경)
    database_url: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: Optional[str] = None
    db_port: str = "5432"
    db_name: Optional[str] = None

    aws_region: str = "ap-northeast-2"

    cognito_user_pool_id: str = ""
    cognito_region: str = "ap-northeast-2"
    cognito_client_id: str = ""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # AgentCore Runtime ARN (기존 analysis_lambda_arn 대체)
    agentcore_runtime_arn: str = "arn:aws:bedrock-agentcore:ap-northeast-2:620758375333:runtime/cdci_prd_analysis_agent-wCS0IP7dHa"

    # user 서비스 URL (JWT 전달 방식 서비스간 호출)
    user_service_url: str = "http://localhost:8003"

    class Config:
        env_file = ".env"

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if all([self.db_user, self.db_password, self.db_host, self.db_name]):
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        raise ValueError(
            "DB 연결 정보 없음: DATABASE_URL 또는 DB_USER/DB_PASSWORD/DB_HOST/DB_NAME 환경변수를 설정하세요."
        )


settings = Settings()
