from typing import Dict, List

def call_llm_agent(
    cognito_id: str,
    user_data: Dict,
    supplements: List[Dict],
    medications: List[str],
    purpose: str
) -> Dict[int, int]:
    """
    🔌 TODO: Bedrock Agent 연동 필요

    LLM Agent 호출 - 1차 영양소 판단

    Args:
        cognito_id: 사용자 ID
        user_data: CODEF 건강검진 데이터 + 사용자 입력 정보
        supplements: 현재 복용 중인 영양제 정보
        medications: 복용 중인 의약품 리스트
        purpose: 영양제 복용 목적

    Returns:
        필요한 영양소별 권장 섭취량 {nutrient_id: amount}

    TODO:
    1. Bedrock Agent 엔드포인트 호출
    2. 영양제-의약품 상호작용 Knowledge Base 참조
    3. LLM이 종합 판단하여 필요 영양소 + 권장량 반환

    현재는 Mock 데이터 반환
    """

    # Mock 데이터 (추후 Bedrock Agent 응답으로 교체)
    return {
        1: 1000,   # 비타민C 1000mg
        2: 400,    # 비타민D 400IU
        3: 600,    # 오메가3 EPA 600mg
        4: 400,    # 오메가3 DHA 400mg
        5: 15,     # 아연 15mg
    }

def call_recommendation_agent(
    nutrient_gaps: List[Dict],
    user_preferences: Dict = None
) -> List[int]:
    """
    🔌 TODO: AI 추천 Agent 연동 필요

    추천 Agent 호출 - AI 기반 영양제 추천

    Args:
        nutrient_gaps: 부족한 영양소 리스트
        user_preferences: 사용자 선호도 (가격, 브랜드 등)

    Returns:
        추천 제품 ID 리스트 (우선순위 순)

    TODO:
    1. AI Agent를 활용한 최적 조합 추천
    2. 1일 투약 횟수 최소화
    3. 가격 대비 효율 고려

    현재는 간단한 규칙 기반 로직
    """

    # 현재는 placeholder - 추후 AI Agent로 교체
    return []
