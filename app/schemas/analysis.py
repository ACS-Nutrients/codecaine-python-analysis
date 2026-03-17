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


