# API 명세서 (MSA 기반)

## 📌 개요
- 프로젝트: 영양제 추천 시스템
- 아키텍처: MSA (Microservice Architecture)
- 프론트엔드: React + Vite
- 백엔드: Python (FastAPI 권장)
- 데이터베이스: PostgreSQL

---

## 🔐 인증 (Authentication Service)

### 1. 사용자 로그인
```
POST /api/auth/login
```
**Request:**
```json
{
  "email": "hong1234@email.com",
  "password": "string"
}
```
**Response:**
```json
{
  "cognito_id": "uuid-string",
  "email": "hong1234@email.com",
  "access_token": "jwt-token",
  "refresh_token": "jwt-token"
}
```

### 2. 사용자 정보 조회
```
GET /api/auth/me
Headers: Authorization: Bearer {token}
```
**Response:**
```json
{
  "cognito_id": "uuid-string",
  "email": "hong1234@email.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## 👤 사용자 정보 (User Service)

### 3. 마이페이지 정보 조회
```
GET /api/users/{cognito_id}
```
**Response:**
```json
{
  "cognito_id": "uuid-string",
  "email": "hong1234@email.com",
  "ans_birth_dt": "1990-01-01",
  "ans_gender": 0,
  "ans_height": 175.5,
  "ans_weight": 72.0,
  "ans_allergies": "땅콩, 우유",
  "ans_chron_diseases": "고혈압",
  "ans_current_conditions": "피로, 수면부족",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-04-10T00:00:00Z"
}
```

### 4. 사용자 정보 수정
```
PUT /api/users/{cognito_id}
```
**Request:**
```json
{
  "ans_birth_dt": "1990-01-01",
  "ans_gender": 0,
  "ans_height": 175.5,
  "ans_weight": 72.0,
  "ans_allergies": "땅콩, 우유",
  "ans_chron_diseases": "고혈압",
  "ans_current_conditions": "피로, 수면부족"
}
```
**Response:**
```json
{
  "success": true,
  "message": "사용자 정보가 업데이트되었습니다."
}
```

---

## 💊 영양제 관리 (Supplement Service)

### 5. 현재 복용 중인 영양제 목록 조회
```
GET /api/supplements?cognito_id={cognito_id}&is_active=true
```
**Response:**
```json
{
  "supplements": [
    {
      "ans_current_id": 1,
      "cognito_id": "uuid-string",
      "ans_product_name": "Omega-3",
      "ans_serving_amount": 2,
      "ans_serving_per_day": 1,
      "ans_daily_total_amount": 2,
      "ans_is_active": true,
      "ans_ingredients": {
        "EPA": 600,
        "DHA": 400
      },
      "created_at": "2024-04-10T00:00:00Z"
    }
  ]
}
```

### 6. 영양제 추가
```
POST /api/supplements
```
**Request:**
```json
{
  "cognito_id": "uuid-string",
  "ans_product_name": "비타민 C",
  "ans_serving_amount": 1,
  "ans_serving_per_day": 2,
  "ans_daily_total_amount": 2,
  "ans_is_active": true,
  "ans_ingredients": {
    "비타민C": 1000
  }
}
```
**Response:**
```json
{
  "ans_current_id": 123,
  "success": true,
  "message": "영양제가 추가되었습니다."
}
```

### 7. 영양제 수정
```
PUT /api/supplements/{ans_current_id}
```
**Request:** (6번과 동일)

### 8. 영양제 삭제
```
DELETE /api/supplements/{ans_current_id}
```

### 9. 영양제 활성화/비활성화
```
PATCH /api/supplements/{ans_current_id}/status
```
**Request:**
```json
{
  "ans_is_active": false
}
```

---

## 📊 분석 (Analysis Service) ⭐ 핵심

### 10. 분석 히스토리 목록 조회
```
GET /api/analysis/history?cognito_id={cognito_id}&limit=10&offset=0
```
**Response:**
```json
{
  "total": 3,
  "results": [
    {
      "result_id": 1,
      "cognito_id": "uuid-string",
      "summary_jsonb": {
        "title": "영양제 추천 결과",
        "deficient_nutrients": ["비타민C", "비타민D"],
        "total_gap_count": 2
      },
      "created_at": "2026-02-10T00:00:00Z"
    }
  ]
}
```
**사용 페이지:** `AnalysisHistory.tsx`, `Home.tsx`

### 11. 영양소 갭 분석 실행
```
POST /api/analysis/calculate
```
**Request:**
```json
{
  "cognito_id": "uuid-string",
  "health_check_data": {
    "exam_date": "2024-04-10",
    "vitamin_d": 18,
    "vitamin_b12": 220
  },
  "purposes": ["면역력 강화", "에너지 증진"]
}
```
**Response:**
```json
{
  "result_id": 123,
  "message": "분석이 완료되었습니다.",
  "processing_time": "2.5s"
}
```
**사용 페이지:** `Recommendation.tsx`

### 12. 분석 결과 상세 조회
```
GET /api/analysis/result/{result_id}
```
**Response:**
```json
{
  "result_id": 123,
  "cognito_id": "uuid-string",
  "summary_jsonb": {
    "title": "건강 상태 분석 보고서",
    "report_id": "RPT-20260227",
    "health_check": {
      "exam_date": "2026-01-18",
      "blood_pressure": "128/86",
      "blood_sugar": 103
    },
    "deficient_nutrients": [
      {
        "nutrient_name": "비타민C",
        "current_amount": 0,
        "target_amount": 1000,
        "gap_amount": 1000,
        "unit": "mg"
      }
    ]
  },
  "created_at": "2026-02-27T00:00:00Z"
}
```
**사용 페이지:** `RecommendationResult.tsx`

### 13. 영양소 갭 상세 조회
```
GET /api/analysis/nutrient-gap/{result_id}
```
**Response:**
```json
{
  "gaps": [
    {
      "gap_id": 1,
      "result_id": 123,
      "nutrient_id": 5,
      "nutrient_name": "비타민C",
      "current_amount": 0,
      "gap_amount": 1000,
      "unit": "mg",
      "created_at": "2026-02-27T00:00:00Z"
    }
  ]
}
```

---

## 🎯 추천 (Recommendation Service)

### 14. 추천 영양제 목록 조회
```
GET /api/recommendations/{result_id}
```
**Response:**
```json
{
  "recommendations": [
    {
      "rec_id": 1,
      "product_id": 101,
      "product_name": "비타민C 1000mg",
      "product_brand": "브랜드A",
      "recommend_serving": 1,
      "rank": 1,
      "nutrients": [
        {
          "nutrient_name": "비타민C",
          "amount_per_serving": 1000,
          "unit": "mg"
        }
      ],
      "created_at": "2026-02-27T00:00:00Z"
    }
  ]
}
```
**사용 페이지:** `RecommendationResult.tsx`

---

## 📝 기록 (Record Service)

### 15. 영양제 복용 기록 조회 (월별)
```
GET /api/records?cognito_id={cognito_id}&year=2024&month=4
```
**Response:**
```json
{
  "records": [
    {
      "date": "2024-04-01",
      "supplements": [
        {
          "ans_current_id": 1,
          "product_name": "Omega-3",
          "taken_count": 2,
          "daily_limit": 2
        }
      ]
    }
  ]
}
```
**사용 페이지:** `RecordHistory.tsx`

### 16. 영양제 복용 기록 추가/수정
```
POST /api/records
```
**Request:**
```json
{
  "cognito_id": "uuid-string",
  "ans_current_id": 1,
  "date": "2024-04-01",
  "taken_count": 2
}
```

---

## 💬 챗봇 (Chatbot Service)

### 17. 챗봇 대화 전송
```
POST /api/chatbot/message
```
**Request:**
```json
{
  "cognito_id": "uuid-string",
  "message": "비타민C를 언제 먹는게 좋나요?",
  "context": {
    "result_id": 123
  }
}
```
**Response:**
```json
{
  "bot_message": "비타민C는 아침 식사 후 복용하는 것이 좋습니다...",
  "timestamp": "2026-02-27T10:30:00Z"
}
```
**사용 페이지:** `Chatbot.tsx`

### 18. 챗봇 대화 히스토리 조회
```
GET /api/chatbot/history?cognito_id={cognito_id}&limit=50
```
**Response:**
```json
{
  "messages": [
    {
      "type": "user",
      "content": "비타민C를 언제 먹는게 좋나요?",
      "timestamp": "2026-02-27T10:30:00Z"
    },
    {
      "type": "bot",
      "content": "비타민C는 아침 식사 후...",
      "timestamp": "2026-02-27T10:30:05Z"
    }
  ]
}
```

---

## 🏠 홈 (Dashboard Service)

### 19. 홈 대시보드 데이터 조회
```
GET /api/dashboard?cognito_id={cognito_id}
```
**Response:**
```json
{
  "user": {
    "email": "hong1234@email.com",
    "last_analysis_date": "2026-02-27"
  },
  "analysis_count": 3,
  "active_supplements_count": 6,
  "recent_analysis": {
    "result_id": 123,
    "created_at": "2026-02-27T00:00:00Z"
  }
}
```
**사용 페이지:** `Home.tsx`

---

## 📦 제품 검색 (Product Service)

### 20. 제품 검색
```
GET /api/products/search?query=비타민C&limit=10
```
**Response:**
```json
{
  "products": [
    {
      "product_id": 101,
      "product_brand": "브랜드A",
      "product_name": "비타민C 1000mg",
      "serving_per_day": 1,
      "nutrients": [
        {
          "nutrient_name": "비타민C",
          "amount_per_serving": 1000,
          "unit": "mg"
        }
      ]
    }
  ]
}
```

---

## 🎯 우선순위

### Phase 1 (필수 - Analysis 개발)
- ✅ **10. 분석 히스토리 목록 조회** (`AnalysisHistory.tsx`)
- ✅ **11. 영양소 갭 분석 실행** (`Recommendation.tsx`)
- ✅ **12. 분석 결과 상세 조회** (`RecommendationResult.tsx`)
- ✅ **14. 추천 영양제 목록 조회** (`RecommendationResult.tsx`)

### Phase 2 (중요)
- 3. 마이페이지 정보 조회
- 4. 사용자 정보 수정
- 5. 현재 복용 중인 영양제 목록 조회
- 15. 영양제 복용 기록 조회

### Phase 3 (추가)
- 17. 챗봇 대화
- 19. 홈 대시보드
- 20. 제품 검색

---

## 📝 주의사항

1. **DB 스키마 변경 금지** - 팀원과 합의된 구조
2. **인증 토큰** - 모든 API는 `Authorization: Bearer {token}` 헤더 필요
3. **에러 응답 형식** (통일)
```json
{
  "error": true,
  "message": "에러 메시지",
  "code": "ERROR_CODE"
}
```
4. **날짜 형식** - ISO 8601 (`YYYY-MM-DDTHH:mm:ssZ`)
5. **페이지네이션** - `limit`, `offset` 파라미터 사용
