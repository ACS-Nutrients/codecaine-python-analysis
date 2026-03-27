"""
user 서비스 HTTP 클라이언트.
- get_codef_data_internal: JWT 없이 VPC 내부 호출 (chat-calculate 전용)
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_codef_data_internal(cognito_id: str) -> dict:
    """
    user 서비스에서 CODEF 분석 데이터 조회 — JWT 없이 VPC 내부 서비스 간 호출.
    /chat-calculate 엔드포인트 전용 (Chatbot Super Agent → Analysis Backend 흐름).

    Returns:
        {
            "codef_health_data": { "혈압": "120/80", ... },
            "medication_info":   [ {"name": "아스피린", "dose": "100mg", "usage": "..."} ]
        }
    데이터 없거나 실패 시 빈 값 반환 (분석은 계속 진행).
    """
    url = f"{settings.user_service_url}/api/users/codef/internal-service/{cognito_id}"
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"[{cognito_id}] user 서비스 CODEF 내부 조회 실패 (HTTP {e.response.status_code}) — 빈 값으로 진행")
    except Exception as e:
        logger.warning(f"[{cognito_id}] user 서비스 내부 호출 실패: {e} — 빈 값으로 진행")

    return {"codef_health_data": {}, "medication_info": []}
