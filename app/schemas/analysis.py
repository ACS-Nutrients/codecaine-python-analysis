from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class ExamItem(BaseModel):
    name: str
    value: str
    unit: str


class PrescriptionItem(BaseModel):
    name: str
    dose: str
    usage: str


class HealthCheckData(BaseModel):
    exam_date: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    exam_items: Optional[List[ExamItem]] = None


class AnalysisCalculateRequest(BaseModel):
    health_check_data: Optional[HealthCheckData] = None
    prescription_data: Optional[List[PrescriptionItem]] = None
    purposes: Optional[List[str]] = None


class ChatCalculateRequest(BaseModel):
    cognito_id: str
    result_id: int
    new_purpose: Optional[str] = None
    chat_history: Optional[List[Dict]] = None


class NutrientGapResponse(BaseModel):
    nutrient_id: int
    name_ko: Optional[str] = None
    name_en: Optional[str] = None
    unit: Optional[str] = None
    current_amount: Optional[int] = None
    rda_amount: Optional[int] = None
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
    summary: Optional[str] = None
    nutrient_gaps: Optional[List[NutrientGapResponse]] = None
    created_at: Optional[datetime] = None


class AnalysisHistoryItem(BaseModel):
    result_id: int
    created_at: Optional[datetime] = None
    summary: Optional[str] = None


