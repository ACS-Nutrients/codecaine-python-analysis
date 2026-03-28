# Analysis 서비스

사용자의 건강검진 데이터(CODEF 연동)와 복용 영양제를 분석하여 영양소 부족량을 계산하고,
AWS Bedrock Agent를 통해 맞춤형 영양제를 추천하는 FastAPI 마이크로서비스.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.11 |
| 프레임워크 | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (동기) |
| DB | PostgreSQL (`vitamin_analysis` DB) |
| AI | AWS Bedrock Agent |
| 외부 API | CODEF (국민건강보험 건강검진/처방기록 조회) |
| 스토리지 | AWS S3 (CODEF 원본 데이터 보관) |

---

## 실행

### 로컬

```bash
# 가상환경 생성
python3.11 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 값 입력

# 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 로컬 — RDS 접속 (Bastion SSM 포트 포워딩)

프로덕션 RDS는 VPC 내부에 있어 직접 접속 불가. Bastion EC2를 통해 포트 포워딩 후 연결.

```bash
# 1. SSM 포트 포워딩 (백그라운드 실행)
aws ssm start-session \
  --target i-0e9937c6ce9056ea3 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["cdci-prd-analysis.c9you6w8souo.ap-northeast-2.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["15432"]}' &

# 2. .env 설정 (DB 비밀번호는 AWS Secrets Manager > cdci-prd-analysis-db-secret 참고)
DATABASE_URL=postgresql://vitamin_analysis:<password>@127.0.0.1:15432/vitamin_analysis?sslmode=require

# 3. 서버 시작
uvicorn app.main:app --port 8001 --reload
```

> DB 비밀번호에 `:`, `?`, `!` 등 특수문자가 포함된 경우 DATABASE_URL에 그대로 입력.
> pgpass 파일 사용 시 콜론(`:`)은 `\:`로 이스케이프 필요.

### ECS

ECS Task Definition의 `environment` 또는 AWS Secrets Manager를 통해 아래 환경변수를 주입한다.

---

## 환경변수

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `DATABASE_URL` | PostgreSQL 연결 URL (`postgresql://user:pass@host:5432/vitamin_analysis`) | — | DB_* 대신 사용 가능 |
| `DB_USER` | DB 사용자 | — | DATABASE_URL 없을 때 필수 |
| `DB_PASSWORD` | DB 비밀번호 | — | DATABASE_URL 없을 때 필수 |
| `DB_HOST` | DB 호스트 | — | DATABASE_URL 없을 때 필수 |
| `DB_PORT` | DB 포트 | `5432` | 선택 |
| `DB_NAME` | DB 이름 | — | DATABASE_URL 없을 때 필수 |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` | 선택 |
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 (ECS Task Role 사용 시 불필요) | — | 선택 |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 키 (ECS Task Role 사용 시 불필요) | — | 선택 |
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID | — | **필수** |
| `COGNITO_REGION` | Cognito 리전 | `ap-northeast-2` | 선택 |
| `COGNITO_CLIENT_ID` | Cognito App Client ID (JWT client_id 검증) | — | **필수** |
| `AGENTCORE_RUNTIME_ARN` | AWS Bedrock AgentCore Runtime ARN | `placeholder` | **필수** |
| `USER_SERVICE_URL` | user 서비스 내부 URL (서비스간 호출) | `http://localhost:8003` | **필수** |

> **ECS 권장**: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` 대신 **ECS Task Role**에 IAM 권한을 부여하는 방식을 사용한다. DB 비밀번호 등 민감한 값은 AWS Secrets Manager에 저장 후 Task Definition에서 `secrets`로 참조한다.

### 로컬 `.env` 예시

```env
# PostgreSQL (직접 URL 또는 개별 변수)
DATABASE_URL=postgresql://user:password@localhost:5432/vitamin_analysis
# 또는
# DB_USER=user
# DB_PASSWORD=password
# DB_HOST=localhost
# DB_NAME=vitamin_analysis

# AWS
AWS_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>

# Cognito
COGNITO_USER_POOL_ID=ap-northeast-2_XXXXXXXXX
COGNITO_CLIENT_ID=<app_client_id>

# Bedrock AgentCore
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock:ap-northeast-2:123456789012:agent-runtime/XXXXXXXXXX

# 내부 서비스 URL
USER_SERVICE_URL=http://localhost:8003
```

---

## 프로젝트 구조

```
app/
├── main.py                        # FastAPI 앱 + 라우터 등록
├── api/
│   └── endpoints/
│       └── analysis.py            # 분석 + CODEF 엔드포인트
├── core/
│   ├── config.py                  # pydantic-settings 환경변수
│   └── auth.py                    # Cognito JWT 검증 (Bearer 토큰)
├── db/
│   └── database.py                # SQLAlchemy 엔진 + 세션
├── models/                        # ORM 모델
├── schemas/
│   └── analysis.py                # Pydantic 요청/응답 스키마
└── services/
    ├── analysis_service.py        # 분석 비즈니스 로직
    ├── agent_service.py           # AWS Bedrock AgentCore 호출
    ├── nutrient_calculator.py     # 영양소 갭 계산
    └── user_client.py             # user 서비스 HTTP 클라이언트
```

---

## API 엔드포인트

### 분석

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `POST` | `/api/analysis/calculate` | JWT 필요 | 영양 분석 실행 (결과 DB 저장) |
| `POST` | `/api/analysis/chat-calculate` | 없음 (VPC 내부) | 챗봇 재분석 (결과 반환만, DB 저장 없음) |
| `GET` | `/api/analysis/result/{result_id}` | JWT 필요 | 분석 결과 조회 |
| `GET` | `/api/recommendations/{result_id}` | JWT 필요 | 추천 영양제 목록 조회 |

### CODEF 건강검진

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/analysis/codef/init` | 건강검진 조회 시작 (카카오 인증 요청) |
| `POST` | `/api/analysis/codef/fetch` | 인증 완료 후 건강검진 데이터 수신 |
| `GET` | `/api/analysis/health-data/{cognito_id}` | S3에 저장된 건강 요약 조회 |

#### `POST /api/analysis/codef/init`

조회 연도 범위(최근 5년)와 처방 날짜 범위(최근 1년)는 백엔드에서 자동 계산한다.
사용자는 인증 정보만 전달하면 된다.

```json
// Request
{
  "user_name": "홍길동",
  "phone_no": "01012345678",
  "identity": "19910525",
  "nhis_id": "<SHA-256 해시된 주민등록번호>"
}

// Response
{
  "health_check_two_way": { "jobIndex": 0, "threadIndex": 0, "jti": "...", "twoWayTimestamp": 0 },
  "prescription_two_way": { ... },
  "token": "<CODEF access token>",
  "hc_start_year": "2021",
  "hc_end_year": "2025",
  "presc_start": "20250101",
  "presc_end": "20251231"
}
```

#### `POST /api/analysis/codef/fetch`

카카오 인증 완료 후 실제 건강검진 데이터를 수신한다.
`init` 응답의 년도/날짜 필드를 그대로 전달해야 한다 (2-way 인증은 동일 파라미터 필수).

```json
// Request
{
  "cognito_id": "string",
  "user_info": { "user_name": "...", "phone_no": "...", "identity": "...", "nhis_id": "..." },
  "health_check_two_way": { ... },
  "prescription_two_way": { ... },
  "token": "string",
  "hc_start_year": "2021",
  "hc_end_year": "2025",
  "presc_start": "20250101",
  "presc_end": "20251231"
}

// Response
{
  "exam_items": [
    { "id": 1, "name": "공복혈당", "value": "95", "unit": "mg/dL", "status": "정상", "range": "100 미만" }
  ],
  "medications": [ { "name": "약품명", "dose": "-", "schedule": "-" } ],
  "health_summary": { "height": "175", "weight": "70", "exam_date": "2024-10-18" }
}
```

#### `POST /api/analysis/calculate`

```json
// Request
{
  "cognito_id": "string",
  "purposes": ["피로 개선", "면역력 강화"],
  "health_check_data": {
    "exam_date": "2024-10-18",
    "gender": 1,
    "age": 33,
    "height": 175.0,
    "weight": 70.0
  }
}

// Response
{ "result_id": 123, "message": "분석이 완료되었습니다." }
```

#### `POST /api/analysis/chat-calculate`

챗봇이 내부적으로 호출하는 재분석 엔드포인트. JWT 인증 없음 (VPC 내부 전용).
이전 분석 결과(`result_id`)를 참고해 새 목적으로 재분석. 결과는 DB에 저장하지 않고 바로 반환.

```json
// Request
{
  "cognito_id": "string",
  "result_id": 33,
  "new_purpose": "피로 회복",
  "chat_history": [
    { "role": "user", "content": "요즘 피로가 너무 심해요" },
    { "role": "assistant", "content": "피로 회복에 맞춰 재분석해드리겠습니다" }
  ]
}

// Response — step1/step2/step3 전체 반환 (calculate와 동일한 분석 구조)
{
  "cognito_id": "string",
  "step1": {
    "required_nutrients": [
      { "name_ko": "비타민 B12", "name_en": "Vitamin B12", "rda_amount": "2.4", "unit": "mcg", "reason": "..." }
    ],
    "summary": {
      "overall_assessment": "...",
      "key_concerns": ["..."],
      "lifestyle_notes": "...",
      "purpose": "피로 회복",
      "medications": [],
      "supplements": []
    }
  },
  "step2": {
    "gaps": [
      { "nutrient_id": 1, "name_ko": "비타민 B12", "current_amount": "0", "gap_amount": "2.4", "unit": "mcg" }
    ]
  },
  "step3": {
    "recommendations": [
      { "rank": 1, "product_id": 12, "product_name": "...", "product_brand": "...", "recommend_serving": 1, "covered_nutrients": ["비타민 B12"] }
    ]
  }
}
```

| 항목 | `/calculate` | `/chat-calculate` |
|---|---|---|
| 인증 | JWT 필요 | 없음 (VPC 내부) |
| 입력 목적 | `purposes` 배열 | `new_purpose` 문자열 + `chat_history` |
| 이전 분석 참조 | 없음 | `result_id`로 DB 조회 |
| DB 저장 | 저장 | 저장 안 함 |
| 응답 | `result_id` | step1/step2/step3 전체 |

---

## 분석 로직

```
1. 사용자 입력 수신 (건강 데이터 + 복용 영양제 + 목적)
        ↓
2. LLM Agent (AWS Bedrock) — 1차 종합 판단
   - CODEF 건강검진 데이터 + 의약품 투약 정보 + 목적 입력
   - 영양제-의약품 상호관계 Knowledge Base 참조
   - 필요 영양소 및 권장량 출력
        ↓
3. 영양소 갭 계산
   - 최대 섭취량 - 현재 섭취 중인 해당 영양소량
   - 단위 변환 (IU → mg, µg → mg)
        ↓
4. 추천 Agent (AWS Bedrock) — AI 영양제 추천
   - 부족한 영양소를 채울 수 있는 영양제 추천
   - 아이허브 크롤링 DB 활용 (1일 섭취량, 투약횟수 등)
        ↓
5. 결과 저장 (analysis_result, nutrient_gap, recommendations 테이블)
```

> AgentCore Runtime ARN이 설정되지 않으면 `agent_service.py`가 mock 응답을 반환함. `AGENTCORE_RUNTIME_ARN` 환경변수 또는 `config.py` 기본값으로 실제 ARN 설정 필요.

---

## CODEF 건강검진 자동 조회 방식

- 조회 범위: `(현재연도 - 4) ~ 현재연도` (최근 5년, 자동 계산)
- 여러 연도 결과가 반환되면 `resCheckupYear` + `resCheckupDate` 기준 내림차순 정렬 → `[0]`이 최신
- 처방기록 조회 범위: 최근 1년 (자동 계산)
- 건강 요약(height, weight, exam_date)은 S3에 저장되어 이후 폼 자동 채움에 사용

---

## DB 스키마

`db-sql/analysisTable.sql` 참고.

| 테이블 | 설명 |
|--------|------|
| `analysis_userdata` | 분석에 사용된 유저 건강 데이터 |
| `analysis_supplements` | 분석 시점 복용 영양제 스냅샷 |
| `anaysis_current_ingredients` | 영양제별 성분 목록 |
| `analysis_result` | 분석 결과 요약 (JSONB) |
| `nutrient_gap` | 영양소별 갭 계산 결과 |
| `recommendations` | 추천 영양제 목록 |
| `nutrients` | 영양소 마스터 |
| `nutrient_reference_intake` | 권장 섭취량 (나이/성별별) |
| `products` | 영양제 제품 마스터 |
| `product_nutrients` | 제품별 영양소 함량 |
| `unit_convertor` | 단위 변환 테이블 |

---

## IAM 권한 (ECS Task Role)

| 권한 | 용도 |
|------|------|
| `bedrock:InvokeAgent` | Bedrock AgentCore Runtime 호출 |
| `s3:GetObject`, `s3:PutObject` | CODEF 건강 데이터 저장/조회 |
| `cognito-idp:DescribeUserPool` | (필요 시) Cognito JWKS 접근 |
