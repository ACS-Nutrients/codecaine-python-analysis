from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.analysis import (
    AnalysisCalculateRequest,
    AnalysisResultResponse,
    CodefUserInfo,
    CodefInitResponse,
    CodefFetchRequest,
)
from app.services import analysis_service
from app.services import codef_service
from app.services import s3_service
from app.db.database import get_db

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/calculate", response_model=dict)
def calculate_analysis(
    request: AnalysisCalculateRequest,
    db: Session = Depends(get_db)
):
    """분석 실행 — 건강 데이터를 요청 본문에서 직접 받아 처리 후 결과를 DB에 저장"""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{result_id}", response_model=AnalysisResultResponse)
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


@router.get("/health-data/{cognito_id}", response_model=dict)
def get_health_data(cognito_id: str):
    """
    S3에 저장된 건강 요약 데이터 조회.
    — 이전 CODEF 조회 결과를 불러와 건강정보 입력 폼 자동 채움에 사용
    """
    summary = s3_service.download_json(cognito_id, "health_summary.json")
    if summary is None:
        raise HTTPException(status_code=404, detail="저장된 건강 데이터가 없습니다.")
    return summary


def _calc_year_range() -> tuple[str, str]:
    """
    건강검진 조회 년도 범위 자동 계산.
    — 건강검진은 격년으로 실시되므로 5년치를 조회해 가장 최신 결과를 확보
    """
    current_year = date.today().year
    return str(current_year - 4), str(current_year)


def _calc_prescription_range() -> tuple[str, str]:
    """
    처방기록 조회 날짜 범위 자동 계산.
    — 최근 1년치 처방 이력을 조회
    """
    today = date.today()
    end_date = today.strftime("%Y%m%d")
    start_date = today.replace(year=today.year - 1).strftime("%Y%m%d")
    return start_date, end_date


@router.post("/codef/init", response_model=CodefInitResponse)
def codef_init(user_info: CodefUserInfo):
    """CODEF 카카오 인증 요청 (1단계) — 건강검진 + 처방기록 동시 요청"""
    try:
        token = codef_service.get_access_token()

        # 년도 범위는 백엔드에서 자동 계산 — 사용자가 별도로 입력할 필요 없음
        hc_start_year, hc_end_year = _calc_year_range()
        presc_start, presc_end = _calc_prescription_range()

        hc_resp = codef_service.request_health_check(
            token=token,
            user_name=user_info.user_name,
            phone_no=user_info.phone_no,
            identity=user_info.identity,
            nhis_id=user_info.nhis_id,
            start_year=hc_start_year,
            end_year=hc_end_year,
        )

        def extract_two_way(resp: dict) -> dict:
            # CODEF 2Way 인증에 필요한 필드만 추출
            data = resp.get("data") or {}
            return {
                "jobIndex": data.get("jobIndex", 0),
                "threadIndex": data.get("threadIndex", 0),
                "jti": data.get("jti", ""),
                "twoWayTimestamp": data.get("twoWayTimestamp", 0),
            }

        hc_two_way = extract_two_way(hc_resp)

        # 처방기록은 실패해도 건강검진 인증은 진행
        try:
            presc_resp = codef_service.request_prescription(
                token=token,
                user_name=user_info.user_name,
                phone_no=user_info.phone_no,
                identity=user_info.identity,
                nhis_id=user_info.nhis_id,
                start_date=presc_start,
                end_date=presc_end,
            )
            presc_two_way = extract_two_way(presc_resp)
        except Exception:
            presc_two_way = {"jobIndex": 0, "threadIndex": 0, "jti": "", "twoWayTimestamp": 0}

        return {
            "health_check_two_way": hc_two_way,
            "prescription_two_way": presc_two_way,
            "token": token,
            # fetch 단계에서도 동일한 범위가 필요하므로 같이 반환
            "hc_start_year": hc_start_year,
            "hc_end_year": hc_end_year,
            "presc_start": presc_start,
            "presc_end": presc_end,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/codef/fetch")
def codef_fetch(req: CodefFetchRequest):
    """
    CODEF 카카오 인증 완료 후 데이터 조회 (2단계).
    — 조회 성공 시 원본(raw)과 파싱된 health_summary를 S3에 저장한다.
    """
    try:
        # init에서 받은 범위 우선 사용, 없으면 재계산 (재시도 등 예외 상황 대비)
        hc_start_year = req.hc_start_year or _calc_year_range()[0]
        hc_end_year = req.hc_end_year or _calc_year_range()[1]
        presc_start = req.presc_start or _calc_prescription_range()[0]
        presc_end = req.presc_end or _calc_prescription_range()[1]

        hc_data = codef_service.fetch_health_check(
            token=req.token,
            user_name=req.user_info.user_name,
            phone_no=req.user_info.phone_no,
            identity=req.user_info.identity,
            nhis_id=req.user_info.nhis_id,
            start_year=hc_start_year,
            end_year=hc_end_year,
            two_way_info=req.health_check_two_way,
        )
        presc_data = codef_service.fetch_prescription(
            token=req.token,
            user_name=req.user_info.user_name,
            phone_no=req.user_info.phone_no,
            identity=req.user_info.identity,
            nhis_id=req.user_info.nhis_id,
            start_date=presc_start,
            end_date=presc_end,
            two_way_info=req.prescription_two_way,
        )

        exam_items = codef_service.parse_health_check(hc_data)
        medications = codef_service.parse_prescription(presc_data)
        health_summary = codef_service.extract_health_summary(hc_data)

        # CODEF 원본 응답을 S3에 보관 — 추후 감사·재처리 용도
        s3_service.upload_json(req.cognito_id, "codef_raw.json", {
            "health_check": hc_data,
            "prescription": presc_data,
        })
        # 파싱된 건강 요약을 S3에 저장 — 건강정보 입력 폼 자동 채움용
        if health_summary:
            s3_service.upload_json(req.cognito_id, "health_summary.json", health_summary)

        return {
            "exam_items": exam_items,
            "medications": medications,
            "health_summary": health_summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


router_recommendations = APIRouter(prefix="/api/analysis/recommendations", tags=["recommendations"])


@router_recommendations.get("/{result_id}", response_model=dict)
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
