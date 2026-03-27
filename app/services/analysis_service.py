import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Dict
from app.models import analysis as models
from app.services.agent_service import call_analysis_agent, resolve_nutrient_ids, _get_current_supplements
from app.services.user_client import get_codef_data_internal

import logging
logger = logging.getLogger(__name__)



def _get_userdata(db: Session, cognito_id: str) -> Dict:
    """analysis_userdata 조회 → AgentCore payload용"""
    userdata = db.query(models.AnalysisUserData).filter(
        models.AnalysisUserData.cognito_id == cognito_id
    ).first()
    if not userdata:
        return {}
    return {
        "birth_dt":          str(userdata.ans_birth_dt) if userdata.ans_birth_dt else None,
        "gender":            userdata.ans_gender,
        "height":            float(userdata.ans_height) if userdata.ans_height else None,
        "weight":            float(userdata.ans_weight) if userdata.ans_weight else None,
        "allergies":         userdata.ans_allergies,
        "chron_diseases":    userdata.ans_chron_diseases,
        "current_conditions": userdata.ans_current_conditions,
    }


def start_analysis(
    db: Session,
    cognito_id: str,
    purpose: str,
    health_check_data: Dict = None,
    prescription_data: List[Dict] = None,
) -> int:
    now = datetime.now(timezone.utc)

    hd = health_check_data or {}
    medication_info = prescription_data or []

    # analysis_userdata 전체 조회 (DMS 동기화 데이터)
    user_profile = _get_userdata(db, cognito_id)

    agent_result = call_analysis_agent(
        db=db,
        cognito_id=cognito_id,
        intake_purpose=purpose,
        user_profile=user_profile,
        codef_health_data=hd,
        medication_info=medication_info,
    )

    step1 = agent_result.get("step1", {})
    step2 = agent_result.get("step2", {})
    step3 = agent_result.get("step3", {})

    gaps            = resolve_nutrient_ids(db, step2.get("gaps", []))
    recommendations = step3.get("recommendations", [])

    current_supplements = _get_current_supplements(db, cognito_id)

    try:
        s1 = step1.get("summary", {})
        nutrients = step1.get("required_nutrients", [])
        key_concerns = s1.get("key_concerns", [])
        meds = [m.get("name", "") for m in medication_info if m.get("name")]
        supps = [s.get("product_name", "") for s in current_supplements if s.get("product_name")]
        nutrient_lines = ", ".join(
            f"{n.get('name_ko', '')} {n.get('rda_amount', '')}{n.get('unit', '')}"
            for n in nutrients
        )
        summary_text = (
            f"[섭취 목적] {purpose}\n"
            f"[복용 약물] {', '.join(meds) if meds else '없음'}\n"
            f"[섭취 중인 영양제] {', '.join(supps) if supps else '없음'}\n"
            f"[전반적 평가] {s1.get('overall_assessment', '')}\n"
            f"[주요 우려사항] {', '.join(key_concerns) if key_concerns else '없음'}\n"
            f"[생활습관] {s1.get('lifestyle_notes', '')}\n"
            f"[필요 영양소] {nutrient_lines}"
        )

        result = models.AnalysisResult(
            cognito_id=cognito_id,
            summary=summary_text,
            created_at=now,
        )
        db.add(result)
        db.flush()
        result_id = result.result_id

        for gap in gaps:
            if not gap.get("nutrient_id"):
                continue
            db.add(models.NutrientGap(
                result_id=result_id,
                cognito_id=cognito_id,
                nutrient_id=gap["nutrient_id"],
                current_amount=int(float(gap.get("current_amount", 0))),
                gap_amount=int(float(gap.get("gap_amount", 0))),
                unit=gap.get("unit"),
                created_at=now,
            ))

        for rec in recommendations:
            if not rec.get("product_id"):
                continue
            db.add(models.Recommendation(
                product_id=rec["product_id"],
                result_id=result_id,
                cognito_id=cognito_id,
                recommend_serving=rec.get("recommend_serving", 1),
                rank=rec.get("rank", 0),
                created_at=now,
            ))

        db.commit()

    except Exception:
        db.rollback()
        raise

    return result_id

def start_chat_analysis(
    db: Session,
    cognito_id: str,
    result_id: int,
    new_purpose: str = None,
    chat_history: List[Dict] = None,
) -> Dict:
    # 1. 기존 분석 결과 조회 (previous_analysis 구성)
    result = db.query(models.AnalysisResult).filter(
        and_(
            models.AnalysisResult.result_id == result_id,
            models.AnalysisResult.cognito_id == cognito_id,
        )
    ).first()
    if not result:
        raise ValueError(f"result_id={result_id} 분석 결과를 찾을 수 없습니다.")

    gaps = db.query(models.NutrientGap).filter(
        models.NutrientGap.result_id == result_id
    ).all()

    recs = db.query(models.Recommendation).filter(
        models.Recommendation.result_id == result_id
    ).order_by(models.Recommendation.rank).all()

    previous_analysis = {
        "summary": result.summary,
        "gaps": [
            {
                "nutrient_id":     g.nutrient_id,
                "current_amount":  g.current_amount,
                "gap_amount":      g.gap_amount,
                "unit":            g.unit,
            }
            for g in gaps
        ],
        "recommendations": [
            {
                "product_id":       r.product_id,
                "rank":             r.rank,
                "recommend_serving": r.recommend_serving,
            }
            for r in recs
        ],
    }

    # 2. CODEF 데이터 조회 (user 서비스 — VPC 내부 호출, JWT 없음)
    codef = get_codef_data_internal(cognito_id)
    codef_health_data = codef.get("codef_health_data") or {}
    medication_info   = codef.get("medication_info") or []

    # 3. user_profile 조회
    user_profile = _get_userdata(db, cognito_id)

    # 4. AgentCore 호출
    agent_result = call_analysis_agent(
        db=db,
        cognito_id=cognito_id,
        user_profile=user_profile,
        codef_health_data=codef_health_data,
        medication_info=medication_info,
        new_purpose=new_purpose,
        chat_history=chat_history,
        previous_analysis=previous_analysis,
    )

    # 5. step1.summary에 컨텍스트 필드 주입 (calculate의 summary_text와 동일 항목)
    current_supplements = _get_current_supplements(db, cognito_id)
    meds = [m.get("name", "") for m in medication_info if m.get("name")]
    supps = [s.get("product_name", "") for s in current_supplements if s.get("product_name")]

    step1_summary = agent_result.get("step1", {}).get("summary", {})
    if isinstance(step1_summary, dict):
        step1_summary["purpose"] = new_purpose or ""
        step1_summary["medications"] = meds
        step1_summary["supplements"] = supps

    return agent_result


def get_analysis_result(db: Session, result_id: int, cognito_id: str) -> Dict:
    """분석 결과 조회"""

    result = db.query(models.AnalysisResult).filter(
        and_(
            models.AnalysisResult.result_id == result_id,
            models.AnalysisResult.cognito_id == cognito_id
        )
    ).first()

    if not result:
        raise ValueError("Result not found")

    # 영양소 부족량 조회
    gaps = db.query(
        models.NutrientGap,
        models.Nutrient
    ).join(
        models.Nutrient,
        models.NutrientGap.nutrient_id == models.Nutrient.nutrient_id
    ).filter(
        models.NutrientGap.result_id == result_id
    ).all()

    nutrient_gaps = []
    for gap in gaps:
        ref_intake = db.query(models.NutrientReferenceIntake).filter(
            models.NutrientReferenceIntake.nutrient_id == gap.NutrientGap.nutrient_id
        ).first()
        nutrient_gaps.append({
            "nutrient_id": gap.NutrientGap.nutrient_id,
            "name_ko": gap.Nutrient.name_ko,
            "name_en": gap.Nutrient.name_en,
            "unit": gap.Nutrient.unit,
            "current_amount": gap.NutrientGap.current_amount,
            "gap_amount": gap.NutrientGap.gap_amount,
            "max_amount": ref_intake.max_amount if ref_intake else None,
        })

    return {
        "result_id": result.result_id,
        "cognito_id": result.cognito_id,
        "summary": result.summary,
        "nutrient_gaps": nutrient_gaps,
        "created_at": result.created_at,
    }

def get_recommendations(db: Session, result_id: int, cognito_id: str) -> List[Dict]:
    """추천 영양제 목록 조회"""

    recs = db.query(
        models.Recommendation,
        models.Product
    ).join(
        models.Product,
        models.Recommendation.product_id == models.Product.product_id
    ).filter(
        models.Recommendation.result_id == result_id
    ).order_by(models.Recommendation.rank).all()

    result = []
    for rec, product in recs:
        nutrients = db.query(
            models.Nutrient.name_ko,
            models.ProductNutrient.amount_per_day
        ).join(
            models.ProductNutrient,
            models.Nutrient.nutrient_id == models.ProductNutrient.nutrient_id
        ).filter(
            models.ProductNutrient.product_id == product.product_id
        ).all()

        result.append({
            "rec_id": rec.rec_id,
            "product_id": product.product_id,
            "product_brand": product.product_brand,
            "product_name": product.product_name,
            "serving_per_day": product.serving_per_day,
            "recommend_serving": rec.recommend_serving,
            "rank": rec.rank,
            "nutrients": {n.name_ko: n.amount_per_day for n in nutrients}
        })

    return result

def get_analysis_history(db: Session, cognito_id: str, limit: int = 10, offset: int = 0) -> List[Dict]:
    """분석 히스토리 조회"""

    results = db.query(models.AnalysisResult).filter(
        models.AnalysisResult.cognito_id == cognito_id
    ).order_by(desc(models.AnalysisResult.created_at)).limit(limit).offset(offset).all()

    return [
        {
            "result_id": r.result_id,
            "created_at": r.created_at,
            "summary": r.summary
        }
        for r in results
    ]
