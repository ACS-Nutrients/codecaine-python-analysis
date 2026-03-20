"""
user 서비스 HTTP 클라이언트.
JWT 전달 방식으로 /api/users/codef/analysis-data/{cognito_id} 호출.
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_codef_data(cognito_id: str, token: str) -> dict:
    """
    user 서비스에서 CODEF 분석 데이터 조회.

    Returns:
        {
            "codef_health_data": { "혈압": "120/80", "height": "170", ... },
            "medication_info":   [ {"name": "아스피린", "dose": "100mg", "unit": "mg"} ]
        }
    데이터 없거나 실패 시 빈 값 반환 (분석은 계속 진행).
    """
    url = f"{settings.user_service_url}/api/users/codef/internal-call/{cognito_id}"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"[{cognito_id}] user 서비스 CODEF 데이터 조회 실패 (HTTP {e.response.status_code}) — 빈 값으로 진행")
    except Exception as e:
        logger.warning(f"[{cognito_id}] user 서비스 호출 실패: {e} — 빈 값으로 진행")

    return {"codef_health_data": {}, "medication_info": []}
