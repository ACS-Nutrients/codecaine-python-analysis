from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.analysis import AnalysisCalculateRequest, AnalysisResultResponse
from app.services import analysis_service
from app.db.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/calculate", response_model=dict)
def calculate_analysis(
    request: AnalysisCalculateRequest,
    db: Session = Depends(get_db),
    cognito_id: str = Depends(get_current_user),
):
    """분석 실행 — 건강 데이터를 요청 본문에서 직접 받아 처리 후 결과를 DB에 저장"""
    try:
        purposes = request.purposes or []
        purpose_str = ", ".join(purposes) if purposes else "건강 유지"

        result_id = analysis_service.start_analysis(
            db=db,
            cognito_id=cognito_id,
            purpose=purpose_str,
            medications=[],
            health_check_data=request.health_check_data.model_dump() if request.health_check_data else {},
        )
        return {
            "result_id": result_id,
            "message": "분석이 완료되었습니다.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{result_id}", response_model=AnalysisResultResponse)
def get_analysis_result(
    result_id: int,
    db: Session = Depends(get_db),
    cognito_id: str = Depends(get_current_user),
):
    """분석 결과 조회"""
    try:
        result = analysis_service.get_analysis_result(db, result_id, cognito_id)
        return {
            "result_id": result["result_id"],
            "cognito_id": result["cognito_id"],
            "status": "completed",
            "summary": result["summary"],
            "nutrient_gaps": result["nutrient_gaps"],
            "created_at": result["created_at"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


router_recommendations = APIRouter(prefix="/api/analysis/recommendations", tags=["recommendations"])


@router_recommendations.get("/{result_id}", response_model=dict)
def get_recommendations(
    result_id: int,
    db: Session = Depends(get_db),
    cognito_id: str = Depends(get_current_user),
):
    """추천 영양제 목록 조회"""
    try:
        recs = analysis_service.get_recommendations(db, result_id, cognito_id)
        return {"recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
