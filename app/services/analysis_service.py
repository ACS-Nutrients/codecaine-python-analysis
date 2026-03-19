from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Dict
from app.models import analysis as models
from app.services.agent_service import call_analysis_agent, resolve_nutrient_ids

import logging
logger = logging.getLogger(__name__)


def _upsert_intake_purpose(db: Session, cognito_id: str, purpose: str, now: datetime) -> None:
    """intake_purpose를 analysis_userdata에 저장 (upsert)"""
    userdata = db.query(models.AnalysisUserData).filter(
        models.AnalysisUserData.cognito_id == cognito_id
    ).first()
    if userdata:
        userdata.intake_purpose = purpose
        userdata.updated_at = now
    else:
        db.add(models.AnalysisUserData(
            cognito_id=cognito_id,
            intake_purpose=purpose,
            created_at=now,
            updated_at=now,
        ))
    db.flush()


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
        "intake_purpose":    userdata.intake_purpose,
    }


def start_analysis(
    db: Session,
    cognito_id: str,
    purpose: str,
    medications: List[str],
    health_check_data: Dict = None,
) -> int:
    hd = health_check_data or {}
    medication_info = [{"name": m} for m in medications] if medications else []
    now = datetime.now(timezone.utc)

    # intake_purpose를 analysis_userdata에 저장
    _upsert_intake_purpose(db, cognito_id, purpose, now)

    # analysis_userdata 전체 조회 (DMS 동기화 데이터 + intake_purpose 포함)
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

    try:
        result = models.AnalysisResult(
            cognito_id=cognito_id,
            summary_jsonb={
                "purpose":            purpose,
                "medications":        medications,
                "status":             "completed",
                "overall_assessment": step1.get("summary", {}).get("overall_assessment", ""),
                "key_concerns":       step1.get("summary", {}).get("key_concerns", []),
                "lifestyle_notes":    step1.get("summary", {}).get("lifestyle_notes", ""),
                "required_nutrients": step1.get("required_nutrients", []),
            },
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
        "summary": result.summary_jsonb,
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
            "summary": r.summary_jsonb
        }
        for r in results
    ]
