import httpx
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from app.core.config import settings

_bearer = HTTPBearer()


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Cognito JWKS를 가져와 kid → key 매핑으로 캐싱"""
    url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    keys = response.json().get("keys", [])
    return {k["kid"]: k for k in keys}


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

    return payload


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Bearer 토큰을 검증하고 cognito_id(sub 클레임)를 반환하는 FastAPI Dependency"""
    payload = _verify_token(credentials.credentials)
    cognito_id: str | None = payload.get("sub")
    if not cognito_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub claim missing")
    return cognito_id
