# 개발 과정 기록 & 트러블슈팅

> **이 문서는 초기 통합 개발(2026-03-10) 당시의 기록입니다.**
> 현재 해결된 이슈와 최신 아키텍처는 루트의 [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)를 참고하세요.
> 구버전 경로(`backend/`) 관련 내용은 현재 `app/` 구조로 변경되었습니다.

> 백엔드 API 개발 + 프론트엔드 연동 과정에서 겪은 문제들과 해결 방법 정리

---

## 1. 백엔드 코드 검토 (Kiro 생성본)

### 상황
Kiro AI가 `backend/`에 FastAPI 백엔드를 자동 생성해둠. 코드가 동작하긴 하지만 실제 DB 스키마와 맞지 않는 부분이 있었음.

### 발견된 문제들

**문제 1: JSONB 필드 vs 정규화 테이블**
- Kiro 코드: `analysis_supplements.ans_ingredients` JSONB 필드에서 성분 읽음
- 실제 설계: `anaysis_current_ingredients` 라는 **별도 정규화 테이블**이 있었음
- 교훈: AI가 자동 생성한 코드는 DB 설계를 완전히 이해하지 못할 수 있음. 반드시 실제 SQL과 대조해야 함.

```python
# Kiro 생성본 (잘못됨)
ingredients = supplement.ans_ingredients  # JSONB 바로 참조

# 수정 후 (정규화 테이블 사용)
ingredients = db.query(models.AnaysisCurrentIngredient).filter(
    AnaysisCurrentIngredient.ans_current_id == supp.ans_current_id
).all()
```

**문제 2: models.py에 테이블 누락**
- `UnitConvertor`, `AnaysisCurrentIngredient` 두 테이블이 SQL에는 있는데 models.py에 없었음
- 해결: SQLAlchemy 모델 직접 추가

---

## 2. 단위 변환 로직 (unit_convertor)

### 배경
영양소 단위가 제품마다 다름:
- `mg` (밀리그램)
- `µg` / `mcg` (마이크로그램)
- `IU` (국제단위) ← 영양소마다 mg 환산 계수가 다름

### 설계 결정
- 모든 단위를 `mg` 기준으로 통일
- `µg` → `× 0.001` (고정값)
- `IU` → `unit_convertor` 테이블에서 영양소별 계수 조회

```python
def convert_to_standard_unit(db, name_ko, name_en, unit, amount):
    if unit == 'mg':
        return float(amount)
    if unit in ('µg', 'mcg', 'μg'):
        return float(amount) * 0.001
    if unit == 'IU':
        converter = db.query(UnitConvertor).filter(
            (UnitConvertor.vitamin_name == name_ko) |
            (UnitConvertor.vitamin_name == name_en)
        ).first()
        if converter:
            return float(amount) * float(converter.convert_unit)
    return float(amount)
```

### 트러블: nutrients.unit이 iHerb 크롤링 단위라 신뢰 불가
- `nutrient_reference_intake` (PDF에서 추출한 기준값)는 PDF 원본 단위 기준
- `nutrients.unit`은 iHerb 크롤링 시 들어온 단위 (제품 표기 기준)
- 두 단위가 다를 수 있음 (예: 구리는 PDF에서 µg인데 iHerb 제품은 mg으로 표기)
- **해결책**: 코드에 `REF_UNIT_MAP` 딕셔너리를 두어 PDF 원본 단위를 하드코딩

```python
REF_UNIT_MAP = {
    '비타민A': 'µg',
    '구리':    'µg',
    '비타민D': 'µg',
    # ...
}
# DB 데이터 수정 없이 변환 시에만 보정
ref_unit = REF_UNIT_MAP.get(nutrient.name_ko, nutrient.unit)
```

---

## 3. iHerb 크롤링 버그

### 버그: 브랜드명이 항상 "NOW Foods"
**원인**: CSS selector `.brand-name`이 iHerb 한국판에서 다른 의미로 쓰임
```python
# 잘못된 코드
brand_elem = soup.select_one(".brand-name")  # 항상 첫 번째 제품만 잡힘
```

**해결**: 여러 selector를 우선순위 순으로 시도
```python
brand_selectors = [
    "#brand a",
    "a.brand-name",
    ".brand-name a",
    ".brand-name",
    "[data-ga-label='Brand'] a",
    "span.brand",
]
for sel in brand_selectors:
    elem = soup.select_one(sel)
    if elem and elem.text.strip():
        brand = elem.text.strip()
        break
# 그래도 없으면 제품명에서 추출 ("브랜드, 제품명" 형식)
if not brand and "," in product_name:
    brand = product_name.split(",")[0].strip()
```

---

## 4. amount 파싱 (iHerb 성분 표기 형식)

### 문제
iHerb 성분표에 금액이 복잡하게 표기됨:
- `"25mcg(5,000IU)"` → mcg가 우선 (mcg > IU)
- `"2.2g(2,200mg)"` → mg이 우선 (mg > g)
- `"1,000mg"` → 콤마 제거 필요
- `"20"` (단위 없음) → None 반환

### 해결: 우선순위 파싱
```python
priority = {'mg': 1, 'mcg': 2, 'µg': 2, 'iu': 3, 'g': 4}

# 문자열에서 (숫자, 단위) 쌍을 모두 추출
matches = re.findall(r'([\d.]+)\s*(mg|mcg|µg|IU|g)', cleaned, re.IGNORECASE)

# 우선순위 가장 높은 것 선택
best = min(matches, key=lambda x: priority.get(x[1].lower(), 999))
```

---

## 5. Python 버전 호환성 (3.9)

### 트러블
Python 3.10+에서만 동작하는 타입 힌트를 사용했다가 에러 발생:

```python
# Python 3.10+ 문법 (3.9에서 에러)
def parse_amount(s: str) -> tuple[float | None, str | None]:
    ...

# Python 3.9 호환 방식
from typing import Optional, Tuple
def parse_amount(s: str) -> Tuple[Optional[float], Optional[str]]:
    ...
```

**교훈**: 팀 환경의 Python 버전을 먼저 확인해야 함. `int | None` 같은 간편 문법도 3.10+ 전용임.

---

## 6. PDF 파싱 (한국인 영양섭취기준)

### 도구
```bash
brew install poppler   # PDF 처리 라이브러리
pip3 install pdfplumber  # Python PDF 파싱
```

### 어려움
PDF 표가 병합 셀(merged cell) 구조여서 단순 추출이 안 됨:
- 연령 그룹(예: "19~29")이 남/여 두 행에 걸쳐 있음
- 셀 하나에 여러 값이 `\n`으로 구분되어 들어옴

### 해결
셀 텍스트를 `\n` 기준으로 split하고, 마지막 값을 상한섭취량(UL)으로 사용:
```python
def parse_cell(cell_str, value_types):
    tokens = re.split(r'\s+', cell_str.strip().replace(",",""))
    # 값 타입 수에 맞춰 뒤에서부터 매핑
    offset = len(tokens) - len(value_types)
    for i, vtype in enumerate(value_types):
        result[vtype] = parse_num(tokens[offset + i])
```

---

## 7. DB 적재 (nutrient_reference_intake)

### 흐름
```
PDF → pdfplumber 파싱 → CSV → Python 스크립트 → PostgreSQL
```

### 트러블: nutrients 테이블 unit 불일치
- iHerb 크롤링으로 먼저 적재된 `nutrients` 레코드의 `unit`이 PDF 기준과 다름
- 예: 구리(Copper)가 iHerb에서는 `mg`으로 표기되지만 PDF에서는 `µg` 기준

**해결 방향**: DB 데이터는 그대로 두고, 변환 로직에서 `REF_UNIT_MAP`으로 처리 (위 2번 참고)

### 중복 방지 로직
```python
cur.execute("""
    SELECT ref_id FROM nutrient_reference_intake
    WHERE nutrient_id = %s AND gender = %s AND age_min = %s
""", (nutrient_id, gender, age_min))
if cur.fetchone():
    skip += 1
    continue  # 이미 있으면 스킵
```

---

## 8. 백엔드-프론트 연동

### API 엔드포인트 불일치
- **프론트가 기대한 엔드포인트**: `POST /api/analysis/calculate`
- **백엔드가 구현한 엔드포인트**: `POST /api/analysis/start`
- **교훈**: API 명세서(API-SPEC.md)를 먼저 확인하고 백엔드를 맞춰야 함

### 요청/응답 형식 불일치

**history 응답**:
```python
# 백엔드가 반환하던 것 (List)
return [{"result_id": 1, ...}, ...]

# 프론트가 기대하는 것 (Dict with total)
return {"total": 3, "results": [...]}
```

**recommendations 응답**:
```python
# 백엔드가 반환하던 것 (List)
return [{"rec_id": 1, ...}, ...]

# 프론트가 기대하는 것
return {"recommendations": [...]}
```

### 프론트 컴포넌트 state 구조 문제

`Recommendation.tsx`에서 `StepHealth` 컴포넌트가 건강데이터(성별, 나이 등)를 **내부 state**로 가지고 있어서, 부모 컴포넌트에서 API 호출 시 접근 불가.

**해결**: `onConfirm` 콜백의 시그니처를 바꿔서 데이터를 부모로 전달(lift state up):

```tsx
// 변경 전
function StepHealth({ onConfirm }: { onConfirm: () => void }) { ... }

// 변경 후: 데이터를 콜백으로 전달
function StepHealth({ onConfirm }: {
  onConfirm: (data: { gender: number; age: number; ... }) => void
}) {
  // ...
  <button onClick={() => onConfirm({ gender: gender === 'male' ? 0 : 1, age: parseInt(age), ... })}>
}

// 부모에서 ref로 임시 보관 후 API 호출 시 사용
const healthDataRef = useRef(null);
const handleHealthConfirm = (data) => {
  healthDataRef.current = data;
  fadeTo('purpose');
};
const handlePurposeConfirm = async (purposes) => {
  await api.startAnalysis({ health_check_data: healthDataRef.current, purposes });
};
```

---

## 9. Pydantic 스키마 Optional 누락

### 트러블
`created_at` 컬럼이 DB에서 `NULL`로 들어오는데 스키마에 `Optional`이 아니어서 500 에러:

```python
# 에러 발생
class AnalysisResultResponse(BaseModel):
    created_at: datetime  # NULL이면 Pydantic validation 실패 → 500

# 수정
class AnalysisResultResponse(BaseModel):
    created_at: Optional[datetime] = None
```

**교훈**: DB 컬럼이 `NULL` 허용이면 무조건 `Optional`로 선언해야 함.

---

## 10. 프론트 빌드 에러 (RecordHistory.tsx)

### 증상
```
Error: Expected ";" but found ":"
src/app/pages/RecordHistory.tsx:73:20
```

### 원인
기존 Mock 데이터에서 일부만 지워지고 `useState` 초기화 블록 밖에 코드 조각이 남아있었음:

```tsx
// 망가진 상태
const [supplements, setSupplements] = useState<Supplement[]>([
  // TODO: API에서 영양제 섭취 기록 가져오기
]);
      '2024-04-14': 2,   // ← 여기가 문법 에러 (블록 밖에 떠있음)
      '2024-04-21': 1,
    },
  },
]);
```

```tsx
// 수정
const [supplements, setSupplements] = useState<Supplement[]>([]);
```

**교훈**: 주석 처리로 TODO 블록을 지울 때 관련 코드 전체를 정확히 제거해야 함.

---

## 11. CORS 설정

### 문제
프론트(localhost:5173)에서 백엔드(localhost:8000)로 직접 fetch 시 CORS 에러 발생 가능.

**1차 해결**: Vite proxy 설정 (이미 되어 있었음)
```ts
// vite.config.ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true }
  }
}
```
→ 프론트에서 `/api/...` 요청 시 Vite가 8000으로 중계해줌. 브라우저는 같은 origin(5173)으로 인식 → CORS 우회.

**2차 해결**: 배포 환경 대비 FastAPI에도 CORS 미들웨어 추가
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 12. 테스트 유저 삽입

### 상황
분석 API가 `analysis_userdata` 테이블에서 유저를 조회하는데, DB에 유저가 없어서 `"User data not found"` 에러 발생.

```python
# POST /api/analysis/calculate 호출 시
# → analysis_service.start_analysis()
# → db.query(AnalysisUserData).filter(cognito_id == ...).first()
# → None 반환 → ValueError 발생
```

**해결**: 테스트용 유저 직접 삽입
```python
cur.execute('''
    INSERT INTO analysis_userdata (cognito_id, ans_birth_dt, ans_gender, ans_height, ans_weight)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (cognito_id) DO NOTHING
''', ('test-user', '1994-01-01', 0, 175.0, 72.0))
```

**교훈**: API 테스트 전에 의존하는 테이블에 테스트 데이터가 있는지 확인해야 함. 특히 FK 관계가 있는 경우.

---

## 전체 흐름 요약

```
1. DB 스키마 확인 (analysisTable.sql)
        ↓
2. 백엔드 모델 수정 (models.py)
   - 누락된 테이블 추가 (UnitConvertor, AnaysisCurrentIngredient)
        ↓
3. 비즈니스 로직 수정 (nutrient_calculator.py)
   - JSONB → 정규화 테이블로 변경
   - 단위 변환 로직 구현 (mg 기준 통일)
   - REF_UNIT_MAP 추가 (DB unit 불신뢰 보완)
        ↓
4. 응답 버그 수정 (analysis_service.py, schemas.py)
   - max_amount 누락 수정
   - Optional 필드 처리
        ↓
5. API 명세서 대조 (API-SPEC.md)
   - 엔드포인트명 맞추기 (/start → /calculate)
   - 응답 형식 맞추기 (wrapping)
        ↓
6. 프론트 연동 (api.ts, 각 페이지)
   - api.ts에 analysis 함수 추가
   - Recommendation.tsx: state lift up + 실제 API 호출
   - RecommendationResult.tsx: URL result_id로 fetch
   - AnalysisHistory.tsx: mock → 실제 API
        ↓
7. 테스트 & 버그 수정
   - created_at Optional 누락
   - RecordHistory.tsx 문법 에러
   - 테스트 유저 DB 삽입
```
