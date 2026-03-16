from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class HealthCheckData(BaseModel):
    exam_date: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None


class AnalysisCalculateRequest(BaseModel):
    cognito_id: str
    health_check_data: Optional[HealthCheckData] = None
    purposes: Optional[List[str]] = []


class NutrientGapResponse(BaseModel):
    nutrient_id: int
    name_ko: Optional[str] = None
    name_en: Optional[str] = None
    unit: Optional[str] = None
    current_amount: Optional[int] = None
    max_amount: Optional[int] = None
    gap_amount: Optional[int] = None


class RecommendationResponse(BaseModel):
    rec_id: int
    product_id: int
    product_brand: str
    product_name: str
    serving_per_day: Optional[int] = None
    recommend_serving: Optional[int] = None
    rank: int
    nutrients: Dict[str, int]


class AnalysisResultResponse(BaseModel):
    result_id: int
    cognito_id: str
    status: str
    summary: Optional[Dict] = None
    nutrient_gaps: Optional[List[NutrientGapResponse]] = None
    created_at: Optional[datetime] = None


class AnalysisHistoryItem(BaseModel):
    result_id: int
    created_at: Optional[datetime] = None
    summary: Optional[Dict] = None


# ── CODEF ─────────────────────────────────────────────────────────────────────

class CodefUserInfo(BaseModel):
    user_name: str
    phone_no: str
    identity: str        # 생년월일 YYYYMMDD
    nhis_id: str         # NHIS 해시 ID
    # year/start_date/end_date는 백엔드에서 자동 계산 — 프론트에서 전송 불필요


class TwoWayInfo(BaseModel):
    jobIndex: int
    threadIndex: int
    jti: str
    twoWayTimestamp: int


class CodefInitResponse(BaseModel):
    health_check_two_way: Optional[Dict] = None
    prescription_two_way: Optional[Dict] = None
    token: str
    # fetch 단계에서 재사용할 조회 범위
    hc_start_year: str = ""
    hc_end_year: str = ""
    presc_start: str = ""
    presc_end: str = ""


class CodefFetchRequest(BaseModel):
    cognito_id: str          # S3 저장 키로 사용
    user_info: CodefUserInfo
    health_check_two_way: Dict
    prescription_two_way: Dict
    token: str
    # init 응답에서 전달받은 조회 범위 — 2-way 인증 시 init과 동일한 파라미터 필수
    hc_start_year: str = ""
    hc_end_year: str = ""
    presc_start: str = ""
    presc_end: str = ""
