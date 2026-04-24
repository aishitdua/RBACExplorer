import logging
from typing import Annotated

import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.database import settings

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer()
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.clerk_jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security_scheme)],
) -> str:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk JWTs don't always have aud
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: no subject")
        return user_id
    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(401, "Invalid or expired token") from None
