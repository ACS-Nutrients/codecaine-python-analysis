# POST /api/analysis/chat-calculate

챗봇이 사용자 요청에 따라 재분석을 수행할 때 호출하는 엔드포인트.

- **인증**: 없음 (VPC 내부 전용, 외부 직접 호출 불가)
- **DB 저장**: 하지 않음 — 결과를 바로 응답으로 반환
- **기반 데이터**: 이전 분석 결과(`result_id`) + CODEF 건강검진 + 복용 의약품

---

## Request

```
POST /api/analysis/chat-calculate
Content-Type: application/json
```

```json
{
  "cognito_id": "9408ddfc-b001-7049-e126-2aec0f8e2f77",
  "result_id": 33,
  "new_purpose": "피로 회복",
  "chat_history": [
    { "role": "user",      "content": "요즘 피로가 너무 심해요" },
    { "role": "assistant", "content": "피로 회복에 맞춰 재분석해드리겠습니다" }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `cognito_id` | string | ✓ | 사용자 Cognito ID |
| `result_id` | int | ✓ | 이전 분석 결과 ID (DB의 `analysis_result.result_id`) |
| `new_purpose` | string | — | 챗봇에서 파악한 새 섭취 목적 (없으면 이전 목적 유지) |
| `chat_history` | array | — | 대화 내역. `role`: `"user"` 또는 `"assistant"` |

---

## Response

```json
{
  "cognito_id": "9408ddfc-b001-7049-e126-2aec0f8e2f77",

  "step1": {
    "required_nutrients": [
      {
        "name_ko": "비타민 B12",
        "name_en": "Vitamin B12",
        "rda_amount": "2.4",
        "unit": "mcg",
        "reason": "에너지 대사와 피로 회복에 필수"
      },
      {
        "name_ko": "비타민 C",
        "name_en": "Vitamin C",
        "rda_amount": "1000",
        "unit": "mg",
        "reason": "항산화 작용과 면역력 강화로 피로 회복 지원"
      }
      // ...
    ],
    "summary": {
      "overall_assessment": "피로 회복을 위해 에너지 대사와 면역력 강화에 중점을 둔 영양소 보충이 필요합니다.",
      "key_concerns": [
        "만성적인 피로",
        "면역력 약화",
        "에너지 대사 저하"
      ],
      "lifestyle_notes": "규칙적인 운동과 충분한 수면, 스트레스 관리가 피로 회복에 도움이 됩니다.",
      "purpose": "피로 회복",
      "medications": [],
      "supplements": []
    }
  },

  "step2": {
    "gaps": [
      {
        "nutrient_id": null,
        "name_ko": "비타민 B12",
        "name_en": "Vitamin B12",
        "unit": "mg",
        "current_amount": "0.0000",
        "gap_amount": "0.0024",
        "rda_amount": "0.0024"
      }
      // ...
    ]
  },

  "step3": {
    "recommendations": [
      {
        "rank": 1,
        "product_id": 7,
        "product_name": "California Gold Nutrition, Gold C®, USP 등급 비타민C, 1,000mg, 베지 캡슐 60정",
        "product_brand": "NOW Foods (나우 푸드)",
        "recommend_serving": 1,
        "serving_per_day": 1,
        "covered_nutrients": ["비타민 C"]
      }
      // ...
    ]
  }
}
```

### 필드 설명

**step1 — AI 분석 결과**

| 필드 | 타입 | 설명 |
|---|---|---|
| `required_nutrients` | array | LLM이 도출한 필요 영양소 목록 |
| `required_nutrients[].name_ko` | string | 영양소명 (한국어) |
| `required_nutrients[].name_en` | string | 영양소명 (영어) |
| `required_nutrients[].rda_amount` | string | 권장 섭취량 (숫자) |
| `required_nutrients[].unit` | string | 단위 (`mg`, `IU`, `mcg` 등) |
| `required_nutrients[].reason` | string | 해당 영양소를 권장하는 이유 |
| `summary.overall_assessment` | string | 전체 영양 상태 평가 |
| `summary.key_concerns` | array | 주요 우려사항 (약물 상호작용 경고 포함) |
| `summary.lifestyle_notes` | string | 생활습관 조언 |
| `summary.purpose` | string | 분석에 사용된 목적 |
| `summary.medications` | array | 현재 복용 의약품 목록 |
| `summary.supplements` | array | 현재 복용 영양제 목록 |

**step2 — 영양소 갭**

| 필드 | 타입 | 설명 |
|---|---|---|
| `gaps[].nutrient_id` | int\|null | DB nutrients 테이블 ID (매핑 실패 시 null) |
| `gaps[].name_ko` | string | 영양소명 |
| `gaps[].unit` | string | 단위 (모두 mg으로 통일 변환됨) |
| `gaps[].current_amount` | string | 현재 복용 중인 해당 영양소량 |
| `gaps[].gap_amount` | string | 부족한 양 (`rda_amount - current_amount`) |
| `gaps[].rda_amount` | string | 권장 섭취량 |

> `unit`이 `IU`로 요청됐더라도 내부적으로 `mg`으로 변환된 값으로 반환될 수 있음.

**step3 — 영양제 추천**

| 필드 | 타입 | 설명 |
|---|---|---|
| `recommendations[].rank` | int | 추천 순위 (1이 최우선) |
| `recommendations[].product_id` | int | DB products 테이블 ID |
| `recommendations[].product_name` | string | 제품명 |
| `recommendations[].product_brand` | string | 브랜드명 |
| `recommendations[].recommend_serving` | int | 권장 복용 횟수 |
| `recommendations[].serving_per_day` | int | 제품 기준 1일 복용 횟수 |
| `recommendations[].covered_nutrients` | array | 이 제품이 커버하는 영양소 목록 |

---

## 에러 응답

| 상태 코드 | 원인 |
|---|---|
| `404` | `result_id`가 DB에 없거나 `cognito_id`와 불일치 |
| `500` | AgentCore 호출 실패 또는 서버 내부 오류 |

---

## 내부 동작 흐름

```
1. result_id → DB에서 이전 분석 결과(gaps, recommendations) 조회
2. cognito_id → CODEF 건강검진 + 처방 약물 데이터 조회 (user 서비스 내부 호출)
3. cognito_id → 사용자 프로필(성별, 나이, 알레르기, 만성질환) 조회
4. AgentCore 호출 (analysis-agent)
   - 이전 분석 결과 + 새 목적 + 대화 내역 + 건강 데이터 전달
   - KB(영양소-의약품 상호작용 DB) 참조
   - Step1(영양소 도출) → Step2(갭 계산 Lambda) → Step3(영양제 추천) 순 실행
5. 결과 반환 (DB 저장 없음)
```

---

## 테스트 예시

```bash
curl -X POST http://localhost:8001/api/analysis/chat-calculate \
  -H "Content-Type: application/json" \
  -d '{
    "cognito_id": "9408ddfc-b001-7049-e126-2aec0f8e2f77",
    "result_id": 33,
    "new_purpose": "피로 회복",
    "chat_history": [
      { "role": "user", "content": "요즘 피로가 너무 심해요" },
      { "role": "assistant", "content": "피로 회복에 맞춰 재분석해드리겠습니다" }
    ]
  }'
```

> 로컬 테스트 시 SSM 포트 포워딩으로 RDS 연결 필요. `README.md` 참고.
