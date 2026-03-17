from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from typing import Dict, List
from app.models import analysis as models

# PDF(한국인 영양섭취기준) 기준 단위 매핑
# nutrients.unit은 iHerb 크롤링 단위라 신뢰할 수 없으므로,
# nutrient_reference_intake의 rda/max 값은 아래 단위 기준으로 저장된 것으로 간주
REF_UNIT_MAP = {
    '비타민A':   'µg',   # µg RE
    '비타민D':   'µg',
    '비타민E':   'mg',
    '비타민K':   'µg',
    '비타민C':   'mg',
    '비타민B6':  'mg',
    '비타민B12': 'µg',
    '티아민':    'mg',
    '리보플라빈': 'mg',
    '니아신':    'mg',
    '판토텐산':  'mg',
    '비오틴':    'µg',
    '엽산':      'µg',
    '칼슘':      'mg',
    '인':        'mg',
    '마그네슘':  'mg',
    '철':        'mg',
    '아연':      'mg',
    '구리':      'µg',
    '불소':      'mg',
    '망간':      'mg',
    '요오드':    'µg',
    '셀레늄':    'µg',
    '몰리브덴':  'µg',
}


def calculate_age(birth_date: date) -> int:
    """생년월일로 나이 계산"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def get_nutrient_reference(db: Session, nutrient_id: int, gender: int, age: int) -> models.NutrientReferenceIntake:
    """영양소별 권장/최대 섭취량 조회"""
    return db.query(models.NutrientReferenceIntake).filter(
        and_(
            models.NutrientReferenceIntake.nutrient_id == nutrient_id,
            models.NutrientReferenceIntake.gender == gender,
            models.NutrientReferenceIntake.age_min <= age,
            models.NutrientReferenceIntake.age_max >= age
        )
    ).first()


def convert_to_standard_unit(
    db: Session,
    nutrient_name_ko: str,
    nutrient_name_en: str,
    unit: str,
    amount: int
) -> float:
    """
    영양소 단위를 mg 기준으로 통일

    - mg  : 변환 없음 (기준 단위)
    - µg  : × 0.001 (고정)
    - IU  : unit_convertor 테이블에서 영양소별 계수 조회 (영양소마다 다름)
    """
    if unit == 'mg':
        return float(amount)

    if unit in ('µg', 'mcg', 'μg'):
        return float(amount) * 0.001

    if unit == 'IU':
        converter = db.query(models.UnitConvertor).filter(
            (models.UnitConvertor.vitamin_name == nutrient_name_ko) |
            (models.UnitConvertor.vitamin_name == nutrient_name_en)
        ).first()
        if converter and converter.convert_unit:
            return float(amount) * float(converter.convert_unit)

    # 알 수 없는 단위 → 변환 없이 반환
    return float(amount)


def calculate_current_nutrient_intake(db: Session, cognito_id: str) -> Dict[int, float]:
    """
    anaysis_current_ingredients 테이블에서 현재 복용 영양소별 1일 섭취량 계산
    단위 변환 포함 (표준 단위로 반환)
    """
    supplements = db.query(models.AnalysisSupplement).filter(
        and_(
            models.AnalysisSupplement.cognito_id == cognito_id,
            models.AnalysisSupplement.ans_is_active == True
        )
    ).all()

    nutrient_totals: Dict[int, float] = {}

    for supp in supplements:
        ingredients = db.query(models.AnaysisCurrentIngredient).filter(
            and_(
                models.AnaysisCurrentIngredient.ans_current_id == supp.ans_current_id,
                models.AnaysisCurrentIngredient.cognito_id == cognito_id
            )
        ).all()

        for ingredient in ingredients:
            if not ingredient.ans_ingredient_name or ingredient.ans_nutrient_amount is None:
                continue

            nutrient = db.query(models.Nutrient).filter(
                (models.Nutrient.name_ko == ingredient.ans_ingredient_name) |
                (models.Nutrient.name_en == ingredient.ans_ingredient_name)
            ).first()

            if not nutrient:
                continue

            # 1회 성분량 × 1일 복용 횟수
            daily_amount = ingredient.ans_nutrient_amount * (supp.ans_serving_per_day or 1)

            # 단위 변환 → mg 기준으로 통일
            converted = convert_to_standard_unit(db, nutrient.name_ko, nutrient.name_en, nutrient.unit, daily_amount)

            nutrient_totals[nutrient.nutrient_id] = nutrient_totals.get(nutrient.nutrient_id, 0.0) + converted

    return nutrient_totals


def calculate_nutrient_gaps(
    db: Session,
    cognito_id: str,
    llm_recommended_nutrients: Dict[int, int]
) -> List[Dict]:
    """
    Lambda 함수: 영양소 부족량 계산

    Args:
        db: DB 세션
        cognito_id: 사용자 ID
        llm_recommended_nutrients: LLM Agent가 추천한 영양소별 필요량 {nutrient_id: amount}

    Returns:
        부족한 영양소 리스트
    """
    # 1. 사용자 정보 조회
    user = db.query(models.AnalysisUserData).filter(
        models.AnalysisUserData.cognito_id == cognito_id
    ).first()

    if not user or not user.ans_birth_dt:
        raise ValueError("User data not found")

    age = calculate_age(user.ans_birth_dt)
    gender = user.ans_gender

    if gender is None:
        raise ValueError("User gender not set")

    # 2. 현재 섭취 중인 영양소 계산 (표준 단위)
    current_intake = calculate_current_nutrient_intake(db, cognito_id)

    # 3. 각 영양소별 부족량 계산
    gaps = []
    for nutrient_id, recommended_amount in llm_recommended_nutrients.items():
        nutrient = db.query(models.Nutrient).filter(
            models.Nutrient.nutrient_id == nutrient_id
        ).first()

        if not nutrient:
            continue

        ref_intake = get_nutrient_reference(db, nutrient_id, gender, age)
        if not ref_intake:
            continue

        # LLM 권장량을 mg 기준으로 변환 (단위 통일 후 비교)
        converted_recommended = convert_to_standard_unit(
            db, nutrient.name_ko, nutrient.name_en, nutrient.unit, recommended_amount
        )

        # ref_intake(rda/max)는 PDF 원본 단위 기준 → 동일하게 mg으로 변환
        ref_unit = REF_UNIT_MAP.get(nutrient.name_ko, nutrient.unit)
        converted_max = convert_to_standard_unit(
            db, nutrient.name_ko, nutrient.name_en, ref_unit, ref_intake.max_amount
        ) if ref_intake.max_amount is not None else None

        current = current_intake.get(nutrient_id, 0.0)
        gap = converted_recommended - current

        if gap > 0:
            gaps.append({
                "nutrient_id": nutrient_id,
                "name_ko": nutrient.name_ko,
                "name_en": nutrient.name_en,
                "unit": nutrient.unit,
                "current_amount": round(current),
                "recommended_amount": round(converted_recommended),
                "max_amount": round(converted_max) if converted_max is not None else None,
                "gap_amount": round(gap)
            })

    return gaps
