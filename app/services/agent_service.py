import json
import logging
from typing import Dict, List

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def _lambda_client():
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("lambda", **kwargs)


def call_llm_agent(
    cognito_id: str,
    user_data: Dict,
    supplements: List[Dict],
    medications: List[str],
    purpose: str,
) -> Dict[int, int]:
    """
    analysis-agent Lambda를 직접 호출하여 필요 영양소 권장량 반환.

    Lambda가 미설정(placeholder)이면 mock 데이터 반환.

    Returns:
        {nutrient_id: recommended_amount}
    """
    if settings.analysis_lambda_arn == "placeholder":
        logger.warning("ANALYSIS_LAMBDA_ARN 미설정 — mock 데이터 반환")
        return _mock()

    # Lambda가 받을 이벤트 (Bedrock Agent Action Group 포맷)
    event = {
        "actionGroup": "analysis",
        "apiPath": "/full-analysis",
        "httpMethod": "POST",
        "parameters": [
            {"name": "user_id",     "value": cognito_id},
            {"name": "purpose",     "value": purpose},
            {"name": "medications", "value": json.dumps(medications, ensure_ascii=False)},
            {"name": "health_data", "value": json.dumps(user_data, ensure_ascii=False)},
        ],
    }

    try:
        client = _lambda_client()
        response = client.invoke(
            FunctionName=settings.analysis_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(event).encode(),
        )

        if response.get("FunctionError"):
            error_payload = json.loads(response["Payload"].read())
            logger.error(f"Lambda 함수 오류: {error_payload}")
            return _mock()

        result = json.loads(response["Payload"].read())

        # Lambda 응답 파싱 (Bedrock Action Group 포맷)
        body_str = result["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)

        if "error" in body:
            logger.error(f"Lambda 분석 오류: {body['error']}")
            return _mock()

        # JSON 직렬화로 int 키 → str 키 변환되므로 복원
        raw = body.get("llm_recommended", {})
        return {int(k): int(v) for k, v in raw.items()}

    except ClientError as e:
        logger.error(f"Lambda 호출 실패: {e}")
        return _mock()
    except Exception as e:
        logger.error(f"call_llm_agent 오류: {e}")
        return _mock()


def _mock() -> Dict[int, int]:
    return {
        1: 1000,  # 비타민C 1000mg
        2: 400,   # 비타민D 400IU
        3: 600,   # 오메가3 EPA 600mg
        4: 400,   # 오메가3 DHA 400mg
        5: 15,    # 아연 15mg
    }


def call_recommendation_agent(
    nutrient_gaps: List[Dict],
    user_preferences: Dict = None,
) -> List[int]:
    """
    🔌 TODO: AI 추천 Agent 연동 필요
    현재는 placeholder — 추후 AI Agent로 교체
    """
    return []
