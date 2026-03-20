import httpx
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from app.core.config import settings

_bearer = HTTPBearer()


@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    """Cognito JWKS를 가져와 kid → key 매핑으로 캐싱 (성공한 결과만 캐싱됨)"""
    url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    keys = response.json().get("keys", [])
    return {k["kid"]: k for k in keys}


def _get_jwks() -> dict:
    """환경변수 검증 후 JWKS 반환. 실패 시 HTTPException으로 변환."""
    if not settings.cognito_user_pool_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="COGNITO_USER_POOL_ID 환경변수가 설정되지 않았습니다.",
        )
    try:
        return _fetch_jwks()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cognito JWKS 요청 실패: {e}",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cognito JWKS 응답 오류: {e.response.status_code}",
        )


def _verify_token(token: str) -> dict:
    """JWT 서명·만료·issuer 검증 후 페이로드 반환"""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")

    jwks = _get_jwks()
    raw_key = jwks.get(header.get("kid"))
    if raw_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token key")

    issuer = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}"
    )

    try:
        public_key = jwk.construct(raw_key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},  # Cognito access token은 aud 클레임 없음
        )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token validation failed: {e}")

    # Access Token의 client_id 클레임으로 App Client ID 수동 검증
    if settings.cognito_client_id:
        token_client_id = payload.get("client_id") or payload.get("aud")
        if token_client_id != settings.cognito_client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token client_id mismatch")

    return payload


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Bearer 토큰을 검증하고 cognito_id(sub 클레임)를 반환하는 FastAPI Dependency"""
    payload = _verify_token(credentials.credentials)
    cognito_id: str | None = payload.get("sub")
    if not cognito_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub claim missing")
    return cognito_id
