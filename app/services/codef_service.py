import json
import logging
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

CODEF_TOKEN_URL = "https://oauth.codef.io/oauth/token"
CODEF_BASE_URL = "https://development.codef.io"


def _parse_response(resp: requests.Response) -> dict:
    """CODEF 응답 파싱 — 빈 응답·비JSON·URL인코딩 응답 모두 처리"""
    text = resp.text.strip()
    if not text:
        raise ValueError(f"CODEF 빈 응답 (HTTP {resp.status_code})")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # URL 인코딩된 경우 디코딩 후 재시도
        try:
            from urllib.parse import unquote
            decoded = unquote(text)
            return json.loads(decoded)
        except Exception:
            raise ValueError(f"CODEF 응답 파싱 실패: {text[:300]}")


def get_access_token() -> str:
    resp = requests.post(
        CODEF_TOKEN_URL,
        params={"grant_type": "client_credentials", "scope": "read"},
        auth=(settings.codef_client_id, settings.codef_client_secret),
        timeout=10,
    )
    resp.raise_for_status()
    text = resp.text.strip()
    if not text:
        raise ValueError(f"CODEF 토큰 응답 비어있음 (HTTP {resp.status_code})")
    try:
        return json.loads(text)["access_token"]
    except (json.JSONDecodeError, KeyError):
        pass
    # URL-encoded 시도
    try:
        from urllib.parse import parse_qs
        parsed = parse_qs(text)
        return parsed["access_token"][0]
    except (KeyError, Exception):
        raise ValueError(f"CODEF 토큰 파싱 실패: {text[:300]}")


def request_health_check(token: str, user_name: str, phone_no: str, identity: str, nhis_id: str,
                         start_year: str, end_year: str) -> dict:
    """건강검진 결과 조회 요청 — start_year~end_year 범위 전체 조회해 가장 최신 결과를 선택"""
    payload = {
        "organization": "0002",
        "loginType": "5",
        "loginTypeLevel": "1",
        "userName": user_name,
        "phoneNo": phone_no,
        "id": nhis_id,
        "identity": identity,
        "inquiryType": "4",
        "searchStartYear": start_year,
        "searchEndYear": end_year,
        "type": "1",
    }
    resp = requests.post(
        f"{CODEF_BASE_URL}/v1/kr/public/pp/nhis-health-checkup/result",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    return _parse_response(resp)


def fetch_health_check(token: str, user_name: str, phone_no: str, identity: str, nhis_id: str,
                       start_year: str, end_year: str, two_way_info: dict) -> dict:
    """건강검진 결과 fetch (2-way 인증 완료 후) — init과 동일한 년도 범위 필수"""
    payload = {
        "organization": "0002",
        "loginType": "5",
        "loginTypeLevel": "1",
        "userName": user_name,
        "phoneNo": phone_no,
        "id": nhis_id,
        "identity": identity,
        "inquiryType": "4",
        "searchStartYear": start_year,
        "searchEndYear": end_year,
        "type": "1",
        "simpleAuth": "1",
        "secureNo": "",
        "secureNoRefresh": "",
        "is2Way": True,
        "twoWayInfo": two_way_info,
    }
    resp = requests.post(
        f"{CODEF_BASE_URL}/v1/kr/public/pp/nhis-health-checkup/result",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    return _parse_response(resp)


def request_prescription(token: str, user_name: str, phone_no: str, identity: str, nhis_id: str, start_date: str, end_date: str) -> dict:
    payload = {
        "organization": "0002",
        "loginType": "5",
        "id": nhis_id,
        "identity": identity,
        "userName": user_name,
        "loginTypeLevel": "1",
        "phoneNo": phone_no,
        "timeOut": "170",
        "startDate": start_date,
        "endDate": end_date,
        "type": "1",
        "drugImageYN": "0",
        "medicationDirectionYN": "1",
        "detailYN": "1",
    }
    resp = requests.post(
        f"{CODEF_BASE_URL}/v1/kr/public/pp/nhis-treatment/information",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return _parse_response(resp)


def fetch_prescription(token: str, user_name: str, phone_no: str, identity: str, nhis_id: str, start_date: str, end_date: str, two_way_info: dict) -> dict:
    payload = {
        "organization": "0002",
        "loginType": "5",
        "id": nhis_id,
        "identity": identity,
        "userName": user_name,
        "loginTypeLevel": "1",
        "phoneNo": phone_no,
        "timeOut": "170",
        "startDate": start_date,
        "endDate": end_date,
        "type": "1",
        "drugImageYN": "0",
        "medicationDirectionYN": "1",
        "detailYN": "1",
        "simpleAuth": "1",
        "is2Way": True,
        "twoWayInfo": two_way_info,
    }
    resp = requests.post(
        f"{CODEF_BASE_URL}/v1/kr/public/pp/nhis-treatment/information",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    return _parse_response(resp)


def _sort_exam_list_desc(exam_list: list) -> list:
    """
    검진 결과 리스트를 검진일 기준 내림차순 정렬.
    — 여러 연도 범위 조회 시 가장 최신 결과가 [0]에 오도록 보장
    """
    def sort_key(item: dict) -> str:
        year = str(item.get("resCheckupYear") or "0000")
        raw_date = str(item.get("resCheckupDate") or "0000")
        if len(raw_date) == 8:
            # YYYYMMDD 형식 — 그대로 정렬 키로 사용
            return raw_date
        elif len(raw_date) == 4 and len(year) == 4:
            # MMDD 형식 — 연도 붙여서 YYYYMMDD로 조합
            return f"{year}{raw_date}"
        return year + "0000"

    return sorted(exam_list, key=sort_key, reverse=True)


def _get_exam_list(data: dict) -> list:
    """
    CODEF 응답에서 검진 결과 리스트 추출.
    - NHIS API는 버전·조회유형에 따라 키 이름이 다름
    """
    inner = data.get("data") or {}
    logger.info("[CODEF raw data keys]: %s", list(inner.keys()) if isinstance(inner, dict) else type(inner))

    for key in ("resCheckupList", "resPreviewList", "resResultList", "resExamList", "resList"):
        val = inner.get(key) if isinstance(inner, dict) else None
        if val and isinstance(val, list) and len(val) > 0:
            logger.info("[CODEF] 리스트 키 '%s' 사용, 항목 수: %d", key, len(val))
            # 최신 검진 결과가 항상 [0]에 오도록 날짜 내림차순 정렬
            return _sort_exam_list_desc(val)

    if isinstance(inner, dict) and inner.get("resHeight"):
        logger.info("[CODEF] data 직하위 단일 검진 결과 사용")
        return [inner]

    logger.warning("[CODEF] 검진 결과 리스트를 찾지 못함. data: %s", str(inner)[:300])
    return []


def extract_health_summary(data: dict) -> dict:
    """
    CODEF 건강검진 응답에서 기본 건강 정보를 추출한다.
    — 프론트의 '건강정보 입력' 폼을 자동으로 채우기 위한 용도

    실제 CODEF NHIS 응답 구조 (resPreviewList 기준):
      resCheckupYear: "2024"         ← 연도
      resCheckupDate: "1018"         ← MMDD (4자리, 연도 없음!)
    """
    exam_list = _get_exam_list(data)
    if not exam_list:
        return {}

    latest = exam_list[0]
    summary = {}

    if latest.get("resHeight"):
        summary["height"] = str(latest["resHeight"])
    if latest.get("resWeight"):
        summary["weight"] = str(latest["resWeight"])

    year = str(latest.get("resCheckupYear") or "")
    raw_date = str(latest.get("resCheckupDate") or "")

    if len(raw_date) == 8:
        summary["exam_date"] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    elif len(raw_date) == 4 and len(year) == 4:
        summary["exam_date"] = f"{year}-{raw_date[:2]}-{raw_date[2:]}"
    elif len(year) == 4:
        summary["exam_date"] = f"{year}-01-01"

    return summary


def _determine_status(key: str, value: str) -> str:
    """항목별 수치를 기준치와 비교해 정상/부족/과잉 판정"""
    try:
        v = float(value.split("/")[0].strip())
    except (ValueError, AttributeError):
        return "정상"

    thresholds = {
        "resFastingBloodSuger": (None, 100),
        "resTotalCholesterol":  (None, 200),
        "resHDLCholesterol":    (60, None),
        "resLDLCholesterol":    (None, 130),
        "resTriglyceride":      (None, 150),
        "resHemoglobin":        (13, 16.5),
        "resSerumCreatinine":   (None, 1.6),
        "resGFR":               (60, None),
        "resAST":               (None, 40),
        "resALT":               (None, 35),
        "resyGPT":              (None, 63),
        "resWaist":             (None, 90),
        "resBMI":               (18.5, 24.9),
    }
    if key not in thresholds:
        return "정상"

    low, high = thresholds[key]
    if high is not None and v >= high:
        return "과잉"
    if low is not None and v < low:
        return "부족"
    return "정상"


def parse_health_check(data: dict) -> list:
    """CODEF 건강검진 응답을 ExamItem 리스트로 변환"""
    items = []
    exam_list = _get_exam_list(data)
    if not exam_list:
        return items

    latest = exam_list[0]

    field_map = [
        ("resBloodPressure",    "혈압",           "mmHg",          "120/80 미만"),
        ("resFastingBloodSuger","공복혈당",        "mg/dL",         "100 미만"),
        ("resTotalCholesterol", "총콜레스테롤",    "mg/dL",         "200 미만"),
        ("resHDLCholesterol",   "HDL콜레스테롤",  "mg/dL",         "60 이상"),
        ("resLDLCholesterol",   "LDL콜레스테롤",  "mg/dL",         "130 미만"),
        ("resTriglyceride",     "중성지방",        "mg/dL",         "150 미만"),
        ("resHemoglobin",       "혈색소",          "g/dL",          "남:13~16.5 / 여:12~15.5"),
        ("resSerumCreatinine",  "크레아티닌",      "mg/dL",         "1.6 이하"),
        ("resGFR",              "사구체여과율",    "mL/min/1.73m2", "60 이상"),
        ("resAST",              "AST",             "U/L",           "40 이하"),
        ("resALT",              "ALT",             "U/L",           "35 이하"),
        ("resyGPT",             "감마지티피",      "U/L",           "남:11~63 / 여:8~35"),
        ("resWaist",            "허리둘레",        "cm",            "남:90 미만 / 여:85 미만"),
        ("resBMI",              "체질량지수",      "kg/m²",         "18.5~24.9"),
    ]

    for idx, (key, name, unit, range_str) in enumerate(field_map):
        value = latest.get(key)
        if value:
            items.append({
                "id": idx + 1,
                "name": name,
                "value": str(value),
                "unit": unit,
                "status": _determine_status(key, str(value)),
                "range": range_str,
            })

    return items


def parse_prescription(data: dict) -> list:
    """CODEF 처방기록 응답을 MedItem 리스트로 변환"""
    meds = []
    d = data.get("data", {})

    treat_list = d.get("resTreatList") or d.get("resList") or []
    seen = set()
    for treat in treat_list:
        med_list = treat.get("resMedicineList") or treat.get("resMediDetailList") or []
        for med in med_list:
            name = med.get("resProductName") or med.get("resDrugName") or ""
            if not name or name in seen:
                continue
            seen.add(name)
            meds.append({
                "name": name,
                "dose": med.get("resOneDayDose") or med.get("resDose") or "-",
                "schedule": med.get("resMedicationInfo") or med.get("resUsage") or "-",
            })

    if not meds:
        for med in d.get("resMediDetailList") or []:
            name = med.get("resProductName") or med.get("resDrugName") or ""
            if not name or name in seen:
                continue
            seen.add(name)
            meds.append({
                "name": name,
                "dose": med.get("resOneDayDose") or med.get("resDose") or "-",
                "schedule": med.get("resMedicationInfo") or med.get("resUsage") or "-",
            })

    return meds
