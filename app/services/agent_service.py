"""
AgentCore Runtime 호출 서비스.
기존 Lambda 직접 호출 → AgentCore Runtime 호출로 전환.
"""

import json
import logging
import time
import uuid
from typing import Dict, List, Optional

import boto3


def _get_xray_trace_header() -> str:
    """현재 OTEL span의 trace context를 X-Amzn-Trace-Id 형식으로 반환."""
    try:
        from opentelemetry import trace as otel_trace
        span = otel_trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx.is_valid:
            return ""
        trace_hex = format(ctx.trace_id, '032x')
        span_hex = format(ctx.span_id, '016x')
        sampled = "1" if ctx.trace_flags.sampled else "0"
        return f"Root=1-{trace_hex[:8]}-{trace_hex[8:]};Parent={span_hex};Sampled={sampled}"
    except Exception:
        return ""


def _send_xray_segment(start_time: float, end_time: float, success: bool) -> None:
    """
    ECS cdci-prd-analysis → AgentCore cdci-prd-analysis-agent 호출을 X-Ray에 기록.
    OTEL sidecar의 awsxrayreceiver(UDP 2000)를 통해 전송 → OTEL sidecar가 X-Ray API로 forwarding.
    boto3 put_trace_segments 직접 호출은 이 환경에서 인덱싱 불가 문제가 있어 UDP 사용.
    """
    import socket
    try:
        trace_id = f"1-{int(start_time):08x}-{uuid.uuid4().hex[:24]}"
        segment = {
            "id": uuid.uuid4().hex[:16],
            "name": "cdci-prd-analysis",
            "trace_id": trace_id,
            "start_time": start_time,
            "end_time": end_time,
            "fault": not success,
            "origin": "AWS::ECS::Fargate",
            "subsegments": [{
                "id": uuid.uuid4().hex[:16],
                "name": "cdci-prd-analysis-agent",
                "start_time": start_time,
                "end_time": end_time,
                "namespace": "remote",
                "fault": not success,
            }],
        }
        doc = json.dumps(segment).encode("utf-8")
        # OTEL sidecar's awsxrayreceiver listens on UDP 2000
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(doc, ("127.0.0.1", 2000))
        finally:
            sock.close()
    except Exception as exc:
        logging.getLogger(__name__).warning("X-Ray UDP send failed: %s", exc)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import analysis as models

logger = logging.getLogger(__name__)


def _agentcore_client():
    from botocore.config import Config
    
    kwargs = {
        "region_name": settings.aws_region,
        "config": Config(
            read_timeout=300,  # 5분 (기본 60초)
            connect_timeout=10
        )
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-agentcore", **kwargs)


def _get_current_supplements(db: Session, cognito_id: str) -> List[Dict]:
    """analysis_supplements 조회"""
    supplements = db.query(models.AnalysisSupplement).filter(
        models.AnalysisSupplement.cognito_id == cognito_id,
        models.AnalysisSupplement.ans_is_active == True,
    ).all()

    result = []
    for s in supplements:
        ingredients = []
        if s.ans_ingredients and isinstance(s.ans_ingredients, list):
            ingredients = [
                {"name": i.get("name", ""), "amount": float(i.get("amount", 0))}
                for i in s.ans_ingredients
            ]
        result.append({
            "product_name":    s.ans_product_name,
            "serving_per_day": s.ans_serving_per_day or 1,
            "ingredients":     ingredients,
        })
    return result


def _get_unit_cache(db: Session) -> Dict:
    """ans_unit_convertor 테이블 전체 조회"""
    rows = db.query(models.UnitConvertor).all()
    return {row.vitamin_name: str(row.convert_unit) for row in rows}


def _get_products(db: Session, gender: int = None) -> List[Dict]:
    """products + product_nutrients JOIN 조회 → Step3 추천용.

    AgentCore invoke 페이로드 한도(~256KB)를 초과하지 않도록
    영양소 보유 수 기준 상위 200개 제품만 반환한다.
    gender: 1=남성, 0=여성. 반대 성별 전용 제품 제외.
    """
    from sqlalchemy import func

    # 반대 성별 전용 제품을 제외할 키워드 (소문자 기준 — 비교 시 product_name.lower() 사용)
    # gender 인코딩: 0=남성, 1=여성 (analysis_userdata.ans_gender 기준)
    MALE_KEYWORDS   = ["남성", "남성용", "men's", "men ", "adam", " men,"]
    FEMALE_KEYWORDS = ["여성", "여성용", "women's", "women", "prenatal"]

    nutrient_count_subq = (
        db.query(
            models.ProductNutrient.product_id,
            func.count(models.ProductNutrient.nutrient_id).label("nutrient_count"),
        )
        .filter(models.ProductNutrient.amount_per_day > 0)
        .group_by(models.ProductNutrient.product_id)
        .subquery()
    )

    top_products = (
        db.query(models.Product)
        .join(nutrient_count_subq, models.Product.product_id == nutrient_count_subq.c.product_id)
        .order_by(nutrient_count_subq.c.nutrient_count.desc())
        .limit(300)  # gender 필터 후 줄어들 수 있으므로 여유 있게 조회
        .all()
    )

    # gender 필터: 반대 성별 전용 제품 제외 (대소문자 무시)
    if gender == 0:  # 남성 → 여성 전용 제품 제외
        top_products = [
            p for p in top_products
            if not any(kw in (p.product_name or "").lower() for kw in FEMALE_KEYWORDS)
        ]
    elif gender == 1:  # 여성 → 남성 전용 제품 제외
        top_products = [
            p for p in top_products
            if not any(kw in (p.product_name or "").lower() for kw in MALE_KEYWORDS)
        ]

    top_products = top_products[:200]

    result = []
    for p in top_products:
        nutrients = db.query(
            models.Nutrient.name_ko,
            models.Nutrient.name_en,
            models.ProductNutrient.amount_per_day,
        ).join(
            models.ProductNutrient,
            models.Nutrient.nutrient_id == models.ProductNutrient.nutrient_id,
        ).filter(
            models.ProductNutrient.product_id == p.product_id,
        ).all()

        result.append({
            "product_id":      p.product_id,
            "product_name":    p.product_name,
            "product_brand":   p.product_brand,
            "serving_per_day": p.serving_per_day,
            "nutrients": [
                {
                    "name_ko":        n.name_ko,
                    "name_en":        n.name_en,
                    "amount_per_day": float(n.amount_per_day or 0),
                }
                for n in nutrients
                if n.amount_per_day and n.amount_per_day > 0
            ],
        })
    return result


def call_analysis_agent(
    db: Session,
    cognito_id: str,
    intake_purpose: str = None,
    user_profile: Optional[Dict] = None,
    codef_health_data: Optional[Dict] = None,
    medication_info: Optional[List[Dict]] = None,
    new_purpose: Optional[str] = None,
    chat_history: Optional[List[Dict]] = None,
    previous_analysis: Optional[Dict] = None,
) -> Dict:
    """
    AgentCore Runtime 호출.
    미설정(placeholder)이면 mock 반환.

    Returns:
        {
          "step1": { "required_nutrients": [...], "summary": {...} },
          "step2": { "gaps": [...] },
          "step3": { "recommendations": [...] }
        }
    """
    if settings.agentcore_runtime_arn == "placeholder":
        logger.warning("AGENTCORE_RUNTIME_ARN 미설정 — mock 데이터 반환")
        return _mock()

    current_supplements = _get_current_supplements(db, cognito_id)
    unit_cache          = _get_unit_cache(db)
    gender              = (user_profile or {}).get("gender")
    products            = _get_products(db, gender=gender)

    payload = {
        "cognito_id":          cognito_id,
        "intake_purpose":      intake_purpose,
        "new_purpose":         new_purpose,
        "chat_history":        chat_history or [],
        "previous_analysis":   previous_analysis,
        "current_conditions":  (user_profile or {}).get("current_conditions"),
        "user_profile":        user_profile or {},
        "codef_health_data":   codef_health_data or {},
        "medication_info":     medication_info or [],
        "current_supplements": current_supplements,
        "unit_cache":          unit_cache,
        "products":            products,
        "_xray_trace":         _get_xray_trace_header(),
    }
    logger.info(f"[{cognito_id}] _xray_trace header: '{payload['_xray_trace']}'")

    call_start = time.time()
    try:
        client = _agentcore_client()
        response = client.invoke_agent_runtime(
            agentRuntimeArn=settings.agentcore_runtime_arn,
            payload=json.dumps(payload, ensure_ascii=False),
        )
        raw = response["response"].read()
        result = json.loads(raw)
        logger.info(f"[{cognito_id}] AgentCore 호출 성공")
        _send_xray_segment(call_start, time.time(), success=True)
        return result

    except Exception as e:
        logger.error(f"AgentCore 호출 실패: {type(e).__name__}: {e}", exc_info=True)
        _send_xray_segment(call_start, time.time(), success=False)
        return _mock()


def resolve_nutrient_ids(db: Session, gaps: List[Dict]) -> List[Dict]:
    """
    step2.gaps의 nutrient_id가 null인 경우
    name_ko로 nutrients 테이블에서 매핑.
    1) exact match
    2) 공백 제거 후 match (비타민 C → 비타민C)
    3) LIKE 검색 (오메가-3 → %오메가-3%)
    """
    resolved = []
    for gap in gaps:
        if gap.get("nutrient_id") is None:
            name_ko = gap["name_ko"]

            # 1) exact match
            nutrient = db.query(models.Nutrient).filter(
                models.Nutrient.name_ko == name_ko
            ).first()

            # 2) 공백 제거 후 match
            if not nutrient:
                normalized = name_ko.replace(" ", "")
                nutrient = db.query(models.Nutrient).filter(
                    models.Nutrient.name_ko == normalized
                ).first()

            # 3) LIKE 검색
            if not nutrient:
                nutrient = db.query(models.Nutrient).filter(
                    models.Nutrient.name_ko.ilike(f"%{name_ko}%")
                ).first()

            if not nutrient:
                logger.warning(f"'{name_ko}' nutrients에서 찾지 못함 — 스킵")
                continue

            gap = {**gap, "nutrient_id": nutrient.nutrient_id}
        resolved.append(gap)
    return resolved


def _mock() -> Dict:
    return {
        "step1": {
            "required_nutrients": [
                {"name_ko": "비타민 C", "name_en": "Vitamin C", "rda_amount": 1000, "unit": "mg", "reason": "mock"},
                {"name_ko": "비타민 D", "name_en": "Vitamin D", "rda_amount": 800,  "unit": "IU", "reason": "mock"},
            ],
            "summary": {
                "overall_assessment": "mock 데이터입니다.",
                "key_concerns": [],
                "lifestyle_notes": "",
            },
        },
        "step2": {
            "gaps": [
                {"nutrient_id": None, "name_ko": "비타민 C", "name_en": "Vitamin C", "unit": "mg", "current_amount": "0", "gap_amount": "1000", "rda_amount": "1000"},
                {"nutrient_id": None, "name_ko": "비타민 D", "name_en": "Vitamin D", "unit": "mg", "current_amount": "0", "gap_amount": "20",   "rda_amount": "20"},
            ],
        },
        "step3": {"recommendations": []},
    }
