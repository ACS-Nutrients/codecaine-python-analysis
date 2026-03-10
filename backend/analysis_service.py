from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Dict
import models
from nutrient_calculator import calculate_nutrient_gaps
from agent_service import call_llm_agent, call_recommendation_agent

def start_analysis(db: Session, cognito_id: str, purpose: str, medications: List[str], health_check_data: Dict = None) -> int:
    """분석 시작"""
    
    # 1. 사용자 데이터 조회
    user_data = db.query(models.AnalysisUserData).filter(
        models.AnalysisUserData.cognito_id == cognito_id
    ).first()
    
    if not user_data:
        raise ValueError("User data not found")
    
    # 2. 현재 복용 중인 영양제 조회
    supplements = db.query(models.AnalysisSupplement).filter(
        and_(
            models.AnalysisSupplement.cognito_id == cognito_id,
            models.AnalysisSupplement.ans_is_active == True
        )
    ).all()
    
    # 3. LLM Agent 호출 (Placeholder)
    user_dict = {
        "birth_dt": user_data.ans_birth_dt,
        "gender": user_data.ans_gender,
        "height": float(user_data.ans_height) if user_data.ans_height else None,
        "weight": float(user_data.ans_weight) if user_data.ans_weight else None,
        "allergies": user_data.ans_allergies,
        "chronic_diseases": user_data.ans_chron_diseases,
        "current_conditions": user_data.ans_current_conditions,
    }
    
    supplements_dict = [
        {
            "name": s.ans_product_name,
            "ingredients": s.ans_ingredients,
            "daily_amount": s.ans_daily_total_amount
        }
        for s in supplements
    ]
    
    llm_recommended = call_llm_agent(
        cognito_id=cognito_id,
        user_data=user_dict,
        supplements=supplements_dict,
        medications=medications,
        purpose=purpose
    )
    
    # 4. 영양소 부족량 계산 (Lambda 함수)
    nutrient_gaps = calculate_nutrient_gaps(db, cognito_id, llm_recommended)
    
    # 5. 분석 결과 저장
    result = models.AnalysisResult(
        cognito_id=cognito_id,
        summary_jsonb={
            "purpose": purpose,
            "medications": medications,
            "status": "completed",
            "llm_recommended": llm_recommended,
        }
    )
    db.add(result)
    db.flush()
    
    result_id = result.result_id
    
    # 6. 영양소 부족량 저장
    for gap in nutrient_gaps:
        gap_record = models.NutrientGap(
            result_id=result_id,
            cognito_id=cognito_id,
            nutrient_id=gap["nutrient_id"],
            current_amount=gap["current_amount"],
            gap_amount=gap["gap_amount"]
        )
        db.add(gap_record)
    
    # 7. 추천 영양제 생성 (Placeholder)
    recommended_products = recommend_products(db, result_id, cognito_id, nutrient_gaps)
    
    db.commit()
    
    return result_id

def recommend_products(
    db: Session,
    result_id: int,
    cognito_id: str,
    nutrient_gaps: List[Dict]
) -> List[int]:
    """
    영양제 추천 로직
    
    TODO: AI Agent로 교체 예정
    현재는 간단한 규칙 기반
    """
    
    if not nutrient_gaps:
        return []
    
    # 부족한 영양소 ID 리스트
    needed_nutrient_ids = [gap["nutrient_id"] for gap in nutrient_gaps]
    
    # 해당 영양소를 포함한 제품 조회
    products = db.query(
        models.Product.product_id,
        models.Product.product_brand,
        models.Product.product_name,
        models.Product.serving_per_day
    ).join(
        models.ProductNutrient,
        models.Product.product_id == models.ProductNutrient.product_id
    ).filter(
        models.ProductNutrient.nutrient_id.in_(needed_nutrient_ids)
    ).distinct().limit(10).all()
    
    # 추천 저장
    for rank, product in enumerate(products, start=1):
        rec = models.Recommendation(
            product_id=product.product_id,
            result_id=result_id,
            cognito_id=cognito_id,
            recommend_serving=product.serving_per_day,
            rank=rank
        )
        db.add(rec)
    
    db.commit()
    
    return [p.product_id for p in products]

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
        and_(
            models.NutrientGap.result_id == result_id,
            models.NutrientGap.cognito_id == cognito_id
        )
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
        and_(
            models.Recommendation.result_id == result_id,
            models.Recommendation.cognito_id == cognito_id
        )
    ).order_by(models.Recommendation.rank).all()
    
    result = []
    for rec, product in recs:
        # 제품의 영양소 정보 조회
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
