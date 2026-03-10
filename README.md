# 영양제 추천 시스템

AI 기반 개인 맞춤형 영양제 추천 및 분석 시스템

## 📋 프로젝트 개요

사용자의 건강 데이터, 현재 복용 중인 영양제, 의약품 정보를 종합 분석하여 부족한 영양소를 계산하고 최적의 영양제를 추천하는 MSA 기반 시스템입니다.

### 주요 기능

- **영양소 갭 분석**: 사용자의 현재 영양소 섭취량과 권장 섭취량을 비교하여 부족량 계산
- **AI 기반 추천**: LLM Agent를 활용한 개인 맞춤형 영양제 추천
- **의약품 상호작용 검증**: 복용 중인 의약품과 영양제 간 상호작용 체크
- **단위 자동 변환**: mg, µg, IU 등 다양한 단위를 표준 단위로 자동 변환
- **분석 히스토리 관리**: 과거 분석 결과 조회 및 비교

## 🏗️ 프로젝트 구조

```
.
├── backend/                    # FastAPI 백엔드 서비스
│   ├── main.py                # FastAPI 애플리케이션 진입점
│   ├── config.py              # 환경 설정 (DB, AWS Bedrock)
│   ├── database.py            # SQLAlchemy DB 연결
│   ├── models.py              # DB 모델 정의 (11개 테이블)
│   ├── schemas.py             # Pydantic 요청/응답 스키마
│   ├── analysis_service.py    # 분석 비즈니스 로직
│   ├── nutrient_calculator.py # 영양소 부족량 계산 (Lambda 함수)
│   ├── agent_service.py       # LLM Agent 호출 (Placeholder)
│   ├── requirements.txt       # Python 의존성
│   ├── .env.example          # 환경변수 예시
│   └── README.md             # 백엔드 상세 문서
├── db-sql/                    # 데이터베이스 스키마
│   ├── analysisTable.sql     # 분석 관련 테이블 (영양소, 제품, 추천)
│   ├── userTable.sql         # 사용자 정보 테이블
│   ├── historyTable.sql      # 복용 기록 테이블
│   ├── chatbotTable-dynamodb.sql  # 챗봇 대화 (DynamoDB)
│   └── connect-info.txt      # DB 연결 정보
├── API-SPEC.md               # API 명세서 (20개 엔드포인트)
└── README.md                 # 프로젝트 개요 (현재 문서)
```

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI 0.115.12
- **Language**: Python 3.9+
- **ORM**: SQLAlchemy 2.0.37
- **Validation**: Pydantic 2.10.6
- **Database Driver**: psycopg2-binary 2.9.10

### Database
- **RDBMS**: PostgreSQL 14+
- **NoSQL**: DynamoDB (챗봇 대화 저장)
- **Architecture**: MSA - 3개 독립 DB (user, analysis, history)

### AI/ML
- **LLM**: AWS Bedrock Agent (예정)
- **Knowledge Base**: 영양제-의약품 상호작용 DB

### Infrastructure
- **Cloud**: AWS (EC2, RDS, DynamoDB, Bedrock)
- **API Gateway**: FastAPI 내장 CORS 미들웨어

## 🚀 시작하기

### 사전 요구사항

- Python 3.9 이상
- PostgreSQL 14 이상
- pip 또는 poetry

### 1. 저장소 클론

```bash
git clone <repository-url>
cd souce-backend-analysis
```

### 2. 백엔드 설정 및 실행

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 DATABASE_URL 등 설정
```

### 3. 환경변수 설정 (.env)

```env
DATABASE_URL=postgresql://vitamin_analysis:vitamin_analysis123!@13.125.230.157:5432/vitamin_analysis
AWS_REGION=us-east-1
BEDROCK_AGENT_ID=placeholder
BEDROCK_AGENT_ALIAS_ID=placeholder
```

### 4. 서버 실행

```bash
# 방법 1: Python 직접 실행
python main.py

# 방법 2: Uvicorn 사용 (개발 모드)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

서버 실행 후:
- API 서버: http://localhost:8000
- Swagger 문서: http://localhost:8000/docs
- ReDoc 문서: http://localhost:8000/redoc

## 📊 데이터베이스 구조

### Analysis DB (vitamin_analysis)

**핵심 테이블**:
- `analysis_userdata`: 사용자 건강 정보 (생년월일, 성별, 키, 몸무게, 알레르기, 만성질환)
- `analysis_result`: 분석 결과 (summary_jsonb에 LLM 추천 결과 저장)
- `nutrient_gap`: 영양소 부족량 상세
- `recommendations`: 추천 영양제 목록
- `analysis_supplements`: 현재 복용 중인 영양제
- `anaysis_current_ingredients`: 복용 영양제의 성분 상세

**참조 테이블**:
- `nutrients`: 영양소 마스터 (name_ko, name_en, unit)
- `nutrient_reference_intake`: 한국인 영양섭취기준 (성별/연령별 RDA, 최대 섭취량)
- `products`: 영양제 제품 정보 (iHerb 크롤링 데이터)
- `product_nutrients`: 제품별 영양소 함량
- `unit_convertor`: IU → mg 변환 계수 (영양소별 상이)

### User DB (vitamin_user)
- 사용자 인증 정보 (Cognito 연동)

### History DB (vitamin_history)
- `intake_supplements`: 복용 중인 영양제 목록
- `intake_item`: 일별 복용 기록
- `purchase_history`: 구매 이력 및 재구매 알림

## 🔄 분석 플로우

```
1. 사용자 입력
   - cognito_id (사용자 식별)
   - purposes (복용 목적: 면역력 강화, 피로 개선 등)
   - health_check_data (건강검진 데이터 - 선택)
   ↓
2. 사용자 데이터 조회
   - analysis_userdata: 생년월일, 성별, 키, 몸무게, 알레르기, 만성질환
   - analysis_supplements: 현재 복용 중인 영양제 (ans_is_active=true)
   ↓
3. LLM Agent 호출 (🔌 Placeholder)
   - 입력: 사용자 정보 + 현재 영양제 + 의약품 + 복용 목적
   - Knowledge Base: 영양제-의약품 상호작용 DB
   - 출력: 필요한 영양소별 권장 섭취량 {nutrient_id: amount}
   ↓
4. 영양소 부족량 계산 (✅ Lambda 함수)
   - 현재 섭취량 계산 (anaysis_current_ingredients 집계)
   - 단위 변환 (mg, µg, IU → 표준 단위)
   - 부족량 = 권장량 - 현재 섭취량
   - 최대 섭취량 검증 (nutrient_reference_intake)
   ↓
5. 추천 영양제 생성 (🔌 Placeholder)
   - 부족한 영양소를 포함한 제품 조회 (products + product_nutrients)
   - AI Agent: 최적 조합 추천 (1일 투약 횟수 최소화)
   - 추천 결과 저장 (recommendations)
   ↓
6. 결과 반환
   - result_id (분석 결과 ID)
   - nutrient_gaps (부족한 영양소 리스트)
   - recommendations (추천 영양제 리스트)
```

## 📡 주요 API 엔드포인트

### 분석 (Analysis Service)

```bash
# 1. 분석 실행
POST /api/analysis/calculate
{
  "cognito_id": "user-123",
  "purposes": ["면역력 강화", "피로 개선"],
  "health_check_data": {
    "exam_date": "2024-04-10",
    "gender": 0,
    "age": 34,
    "height": 175.5,
    "weight": 72.0
  }
}
→ Response: {"result_id": 123, "message": "분석이 완료되었습니다."}

# 2. 분석 결과 조회
GET /api/analysis/result/123?cognito_id=user-123
→ Response: {
  "result_id": 123,
  "summary": {...},
  "nutrient_gaps": [
    {
      "nutrient_id": 1,
      "name_ko": "비타민C",
      "current_amount": 500,
      "gap_amount": 500,
      "unit": "mg"
    }
  ]
}

# 3. 추천 영양제 조회
GET /api/recommendations/123?cognito_id=user-123
→ Response: {
  "recommendations": [
    {
      "product_id": 101,
      "product_brand": "Nature Made",
      "product_name": "Vitamin C 1000mg",
      "rank": 1,
      "nutrients": {"비타민C": 1000}
    }
  ]
}

# 4. 분석 히스토리
GET /api/analysis/history?cognito_id=user-123&limit=10
→ Response: {
  "total": 3,
  "results": [...]
}
```

전체 API 명세는 [API-SPEC.md](./API-SPEC.md) 참고

## 🧪 테스트

### 1. 헬스체크

```bash
curl http://localhost:8000/
# {"message": "Analysis Service API", "status": "running"}
```

### 2. 분석 실행 테스트

```bash
curl -X POST http://localhost:8000/api/analysis/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "cognito_id": "test-user-001",
    "purposes": ["피로 개선"],
    "health_check_data": null
  }'
```

### 3. Swagger UI 사용

http://localhost:8000/docs 에서 인터랙티브 API 테스트 가능

## 🔌 TODO: AI Agent 연동

### 1. LLM Agent (agent_service.py)

**현재 상태**: Mock 데이터 반환
```python
return {
    1: 1000,   # 비타민C 1000mg
    2: 400,    # 비타민D 400IU
    ...
}
```

**연동 필요 사항**:
- AWS Bedrock Agent 엔드포인트 호출
- Knowledge Base: 영양제-의약품 상호작용 DB 연결
- LLM 프롬프트 엔지니어링 (사용자 정보 → 필요 영양소 추론)
- 응답 파싱 및 검증

### 2. 추천 Agent (analysis_service.py)

**현재 상태**: 간단한 규칙 기반 (부족한 영양소 포함 제품 조회)

**개선 필요 사항**:
- AI 기반 최적 조합 추천 (여러 제품 조합으로 부족량 충족)
- 1일 투약 횟수 최소화 (사용자 편의성)
- 가격 대비 효율 고려
- 브랜드 선호도 반영

## 📝 개발 가이드

### 코드 구조

- **main.py**: FastAPI 라우터 정의 (엔드포인트만 담당)
- **analysis_service.py**: 비즈니스 로직 (분석 플로우 오케스트레이션)
- **nutrient_calculator.py**: 순수 계산 로직 (단위 변환, 부족량 계산)
- **agent_service.py**: 외부 AI Agent 호출 (Bedrock 연동 예정)
- **models.py**: DB 테이블 정의 (SQLAlchemy ORM)
- **schemas.py**: API 요청/응답 스키마 (Pydantic)

### 주의사항

1. **DB 스키마 변경 금지**: 팀원과 합의된 구조 유지
2. **단위 변환 필수**: 모든 영양소 계산 시 표준 단위(mg) 변환 후 비교
3. **에러 처리**: HTTPException으로 통일 (404, 500)
4. **날짜 형식**: ISO 8601 (YYYY-MM-DDTHH:mm:ssZ)
5. **CORS 설정**: 프론트엔드 도메인 추가 시 main.py 수정

### 환경별 설정

- **개발**: `--reload` 옵션으로 자동 재시작
- **운영**: Gunicorn + Uvicorn worker 사용 권장
  ```bash
  gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
  ```

## 🔗 관련 문서

- [백엔드 상세 문서](./backend/README.md)
- [API 명세서](./API-SPEC.md)
- [DB 스키마](./db-sql/)

## 📞 문의

프로젝트 관련 문의사항은 팀 채널로 연락 바랍니다.
