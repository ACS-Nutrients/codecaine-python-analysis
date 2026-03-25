from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import schemas
import analysis_service
from database import get_db

app = FastAPI(title="Analysis Service API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Analysis Service API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/analysis/calculate", response_model=dict)
def calculate_analysis(
    request: schemas.AnalysisCalculateRequest,
    db: Session = Depends(get_db)
):
    """
    분석 실행
    - LLM Agent 호출 (Placeholder)
    - 영양소 부족량 계산
    - 추천 영양제 생성
    """
    try:
        purposes = request.purposes or []
        purpose_str = ", ".join(purposes) if purposes else "건강 유지"

        result_id = analysis_service.start_analysis(
            db=db,
            cognito_id=request.cognito_id,
            purpose=purpose_str,
            medications=[],
            health_check_data=request.health_check_data.model_dump() if request.health_check_data else {},
        )
        return {
            "result_id": result_id,
            "message": "분석이 완료되었습니다.",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/result/{result_id}", response_model=schemas.AnalysisResultResponse)
def get_analysis_result(
    result_id: int,
    cognito_id: str,
    db: Session = Depends(get_db)
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


@app.get("/api/recommendations/{result_id}", response_model=dict)
def get_recommendations(
    result_id: int,
    cognito_id: str,
    db: Session = Depends(get_db)
):
    """추천 영양제 목록 조회"""
    try:
        recs = analysis_service.get_recommendations(db, result_id, cognito_id)
        return {"recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/history", response_model=dict)
def get_analysis_history(
    cognito_id: str,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """분석 히스토리 조회"""
    try:
        results = analysis_service.get_analysis_history(db, cognito_id, limit, offset)
        return {"total": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
