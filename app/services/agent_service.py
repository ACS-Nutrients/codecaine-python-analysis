"""
AgentCore Runtime 호출 서비스.
기존 Lambda 직접 호출 → AgentCore Runtime 호출로 전환.
"""

import json
import logging
from typing import Dict, List, Optional

import boto3
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import analysis as models

logger = logging.getLogger(__name__)


def _agentcore_client():
    kwargs = {"region_name": settings.aws_region}
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


def _get_products(db: Session) -> List[Dict]:
    """products + product_nutrients JOIN 조회 → Step3 추천용"""
    products = db.query(models.Product).all()
    result = []
    for p in products:
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
    intake_purpose: str,
    user_profile: Optional[Dict] = None,
    codef_health_data: Optional[Dict] = None,
    medication_info: Optional[List[Dict]] = None,
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
    products            = _get_products(db)

    payload = {
        "cognito_id":          cognito_id,
        "intake_purpose":      intake_purpose,
        "current_conditions":  (user_profile or {}).get("current_conditions"),
        "user_profile":        user_profile or {},
        "codef_health_data":   codef_health_data or {},
        "medication_info":     medication_info or [],
        "current_supplements": current_supplements,
        "unit_cache":          unit_cache,
        "products":            products,
    }

    try:
        client = _agentcore_client()
        response = client.invoke_agent_runtime(
            agentRuntimeArn=settings.agentcore_runtime_arn,
            payload=json.dumps(payload, ensure_ascii=False),
        )
        raw = response["response"].read()
        result = json.loads(raw)
        logger.info(f"[{cognito_id}] AgentCore 호출 성공")
        return result

    except Exception as e:
        logger.error(f"AgentCore 호출 실패: {e}")
        return _mock()


def resolve_nutrient_ids(db: Session, gaps: List[Dict]) -> List[Dict]:
    """
    step2.gaps의 nutrient_id가 null인 경우
    name_ko로 nutrients 테이블에서 매핑.
    """
    resolved = []
    for gap in gaps:
        if gap.get("nutrient_id") is None:
            nutrient = db.query(models.Nutrient).filter(
                models.Nutrient.name_ko == gap["name_ko"]
            ).first()
            if not nutrient:
                logger.warning(f"'{gap['name_ko']}' nutrients에서 찾지 못함 — 스킵")
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
