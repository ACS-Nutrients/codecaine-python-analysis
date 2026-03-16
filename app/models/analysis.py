from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Date, Boolean, TIMESTAMP, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class UnitConvertor(Base):
    __tablename__ = "unit_convertor"

    vitamin_name = Column(String(255), primary_key=True)
    convert_unit = Column(Numeric(12, 8))

class AnalysisUserData(Base):
    __tablename__ = "analysis_userdata"

    cognito_id = Column(String(36), primary_key=True)
    ans_birth_dt = Column(Date)
    ans_gender = Column(Integer)
    ans_height = Column(Numeric(5, 1))
    ans_weight = Column(Numeric(5, 1))
    ans_allergies = Column(String(255))
    ans_chron_diseases = Column(String(255))
    ans_current_conditions = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    result_id = Column(BigInteger, primary_key=True, autoincrement=True)
    cognito_id = Column(String(36), primary_key=True)
    summary_jsonb = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class NutrientGap(Base):
    __tablename__ = "nutrient_gap"

    gap_id = Column(BigInteger, primary_key=True, autoincrement=True)
    result_id = Column(BigInteger, primary_key=True)
    cognito_id = Column(String(36), primary_key=True)
    nutrient_id = Column(BigInteger, primary_key=True)
    current_amount = Column(Integer)
    gap_amount = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Nutrient(Base):
    __tablename__ = "nutrients"

    nutrient_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name_ko = Column(String(255))
    name_en = Column(String(255))
    unit = Column(String(20))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class NutrientReferenceIntake(Base):
    __tablename__ = "nutrient_reference_intake"

    ref_id = Column(BigInteger, primary_key=True, autoincrement=True)
    nutrient_id = Column(BigInteger, primary_key=True)
    gender = Column(Integer)
    age_min = Column(Integer)
    age_max = Column(Integer)
    rda_amount = Column(Integer)
    max_amount = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class Product(Base):
    __tablename__ = "products"

    product_id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_brand = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=False)
    serving_per_day = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class ProductNutrient(Base):
    __tablename__ = "product_nutrients"

    prdt_nutrient_id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, primary_key=True)
    nutrient_id = Column(BigInteger, primary_key=True)
    amount_per_serving = Column(Integer)
    amount_per_day = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class AnalysisSupplement(Base):
    __tablename__ = "analysis_supplements"

    ans_current_id = Column(BigInteger, primary_key=True, autoincrement=True)
    cognito_id = Column(String(36), primary_key=True)
    ans_product_name = Column(String(255))
    ans_serving_amount = Column(Integer)
    ans_serving_per_day = Column(Integer)
    ans_daily_total_amount = Column(Integer)
    ans_is_active = Column(Boolean)
    ans_ingredients = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class AnaysisCurrentIngredient(Base):
    """현재 복용 중인 영양제의 성분 상세 (정규화 테이블)"""
    __tablename__ = "anaysis_current_ingredients"  # SQL 원본 오타 유지

    ans_ingredient_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ans_current_id = Column(BigInteger, primary_key=True)
    cognito_id = Column(String(36), primary_key=True)
    ans_ingredient_name = Column(String(255))
    ans_nutrient_amount = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Recommendation(Base):
    __tablename__ = "recommendations"

    rec_id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, nullable=False)
    result_id = Column(BigInteger, nullable=False)
    cognito_id = Column(String(36), nullable=False)
    recommend_serving = Column(Integer)
    rank = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
