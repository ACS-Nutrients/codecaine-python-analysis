# Analysis 분석 로직 설계

## 전체 흐름

```
[대형 Analysis Agent - AWS Bedrock 배포 예정]
        ↓
1. LLM Agent (1차 판단)
   - 입력: CODEF 건강검진 데이터 + 복용 영양제 정보 + 의약품 투약정보 + 섭취 목적
   - 참조: 영양제-의약품 상호관계 Knowledge Base (Google 크롤링 기반)
   - 출력: 이 사람에게 필요한 영양소 & 권장량
        ↓
2. 영양소 갭 계산 (nutrient_calculator.py)
   - 최대 섭취량(nutrient_reference_intake) - 현재 섭취 중인 해당 영양소량
   - 단위 변환: IU → mg, µg → mg (unit_convertor 테이블 참조)
        ↓
3. 추천 Agent (AI 활용 예정)
   - 부족한 영양소를 채울 수 있는 영양제 추천
   - 아이허브 크롤링 DB 활용 (products, product_nutrients 테이블)
   - 1일 투약횟수 정보로 복용 편의성 고려
```

---

## 현재 구현 상태

| 단계 | 상태 | 비고 |
|------|------|------|
| CODEF 건강검진 연동 | ✅ 완료 | 최근 5년 자동 조회, 최신 결과 자동 선택 |
| 영양소 갭 계산 | ✅ 완료 | `nutrient_calculator.py` |
| LLM Agent (Bedrock) | ⬜ 미완료 | `agent_service.py` mock 반환 중 |
| 추천 Agent (Bedrock) | ⬜ 미완료 | mock 반환 중 |
| S3 원본 저장 | ✅ 완료 | CODEF fetch 시 자동 저장 |

---

## 데이터 소스

### CODEF (국민건강보험)

- 건강검진 결과: 혈압, 공복혈당, 총콜레스테롤, HDL/LDL, 중성지방, 혈색소, 크레아티닌, GFR, AST/ALT/감마지티피, 허리둘레, BMI
- 처방기록: 의약품명, 용량, 복용 주기

### MSA 데이터 복제 원칙

mypage 서비스에서 CODEF 연동 후 전처리한 데이터를 analysis 서비스가 S3를 통해 공유한다.
(MSA에서 서비스 간 DB 직접 접근 없이 데이터를 각자의 영역에 복제하는 원칙)

### 영양제-의약품 상호관계 Knowledge Base

의약품과 영양제 간 상호작용 데이터. Google 크롤링으로 수집하여 Bedrock Knowledge Base로 구축.
LLM Agent가 처방 의약품과 복용 예정 영양제 간 충돌 여부를 판단하는 데 사용.

### iHerb 크롤링 DB

- `products` 테이블: 제품명, 브랜드, 1일 복용량, 복용 횟수
- `product_nutrients` 테이블: 제품별 영양소 함량 (단위 포함)
- `nutrients` 테이블: 영양소 마스터 (name_ko, name_en, unit)
- `nutrient_reference_intake` 테이블: 한국인 영양섭취기준 (나이/성별별 권장량, 상한섭취량)

---

## 단위 변환 로직

모든 영양소 계산은 `mg` 기준으로 통일한다.

```python
# nutrient_calculator.py
if unit == 'mg':
    return float(amount)
if unit in ('µg', 'mcg', 'μg'):
    return float(amount) * 0.001
if unit == 'IU':
    # unit_convertor 테이블에서 영양소별 mg 환산 계수 조회
    converter = db.query(UnitConvertor).filter(...).first()
    return float(amount) * float(converter.convert_unit)
```

> **주의**: `nutrients.unit`은 iHerb 크롤링 기준이라 신뢰 불가.
> `nutrient_reference_intake`의 단위는 PDF(한국인 영양섭취기준) 원본 기준.
> `REF_UNIT_MAP` 딕셔너리로 PDF 원본 단위를 하드코딩하여 보정.
