# Analysis Backend API

영양제 추천 시스템의 분석 백엔드 API

## 🚀 시작하기

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어서 DATABASE_URL 등 설정
```

### 2. 서버 실행

```bash
python main.py
```

또는

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

서버가 실행되면 http://localhost:8000 에서 접속 가능합니다.

API 문서: http://localhost:8000/docs

---

## 📡 API 엔드포인트

### 1. 분석 시작
```
POST /api/analysis/start
```

**Request:**
```json
{
  "cognito_id": "user-123",
  "purpose": "피로 개선 및 면역력 강화",
  "medications": ["아스피린", "메트포르민"]
}
```

**Response:**
```json
{
  "success": true,
  "result_id": 42,
  "message": "Analysis completed"
}
```

### 2. 분석 결과 조회
```
GET /api/analysis/result/{result_id}?cognito_id={cognito_id}
```

**Response:**
```json
{
  "result_id": 42,
  "cognito_id": "user-123",
  "status": "completed",
  "summary": {
    "purpose": "피로 개선 및 면역력 강화",
    "medications": ["아스피린"],
    "status": "completed"
  },
  "nutrient_gaps": [
    {
      "nutrient_id": 1,
      "name_ko": "비타민C",
      "name_en": "Vitamin C",
      "unit": "mg",
      "current_amount": 500,
      "gap_amount": 500
    }
  ],
  "created_at": "2024-04-10T12:00:00Z"
}
```

### 3. 추천 영양제 목록
```
GET /api/recommendations/{result_id}?cognito_id={cognito_id}
```

**Response:**
```json
[
  {
    "rec_id": 1,
    "product_id": 101,
    "product_brand": "Nature Made",
    "product_name": "Vitamin C 1000mg",
    "serving_per_day": 1,
    "recommend_serving": 1,
    "rank": 1,
    "nutrients": {
      "비타민C": 1000
    }
  }
]
```

### 4. 분석 히스토리
```
GET /api/analysis/history?cognito_id={cognito_id}&limit=10&offset=0
```

**Response:**
```json
[
  {
    "result_id": 42,
    "created_at": "2024-04-10T12:00:00Z",
    "summary": {
      "purpose": "피로 개선",
      "status": "completed"
    }
  }
]
```

---

## 🏗️ 아키텍처

### 분석 플로우

```
1. 사용자 입력 (목적, 의약품)
   ↓
2. LLM Agent 호출 (Placeholder) 🔌
   - CODEF 건강검진 데이터
   - 현재 복용 영양제
   - 의약품 정보
   - 영양제-의약품 상호작용 KB
   → 필요 영양소 + 권장량
   ↓
3. Lambda 함수 (영양소 부족량 계산) ✅
   - 최대 섭취량 - 현재 섭취량
   → 부족한 영양소 리스트
   ↓
4. 추천 Agent (Placeholder) 🔌
   - 아이허브 영양제 DB 조회
   - 1일 투약 횟수 최소화
   → 추천 영양제 리스트
```

### 구현 상태

- ✅ **완료**: API 엔드포인트, Lambda 계산 로직, DB 조회
- 🔌 **Placeholder**: LLM Agent, 추천 Agent (Bedrock 연동 대기)

---

## 📦 파일 구조

```
backend-kiro/
├── main.py                  # FastAPI 애플리케이션
├── config.py                # 환경 설정
├── database.py              # DB 연결
├── models.py                # SQLAlchemy 모델
├── schemas.py               # Pydantic 스키마
├── analysis_service.py      # 분석 비즈니스 로직
├── nutrient_calculator.py   # Lambda 함수 (영양소 계산)
├── agent_service.py         # Agent 호출 (Placeholder)
├── requirements.txt         # 의존성
└── .env.example            # 환경변수 예시
```

---

## 🔌 TODO: Bedrock Agent 연동

### 1. LLM Agent (`agent_service.py::call_llm_agent`)

**현재**: Mock 데이터 반환
**TODO**: 
- Bedrock Agent 엔드포인트 호출
- 영양제-의약품 상호작용 KB 참조
- LLM 응답 파싱

### 2. 추천 Agent (`agent_service.py::call_recommendation_agent`)

**현재**: 간단한 규칙 기반
**TODO**:
- AI 기반 최적 조합 추천
- 1일 투약 횟수 최소화
- 가격 대비 효율 고려

---

## 🧪 테스트

```bash
# 서버 실행 후
curl -X POST http://localhost:8000/api/analysis/start \
  -H "Content-Type: application/json" \
  -d '{
    "cognito_id": "test-user-001",
    "purpose": "피로 개선",
    "medications": []
  }'
```

---

## 📝 참고

- DB 스키마: `../db-sql/analysisTable.sql`
- API 명세: `../API-SPEC.md`
- 프론트엔드: `../src/app/`
