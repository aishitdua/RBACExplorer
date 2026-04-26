import logging
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.database import settings

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer()
_jwks_cache: dict | None = None
_jwks_fetched_at: datetime | None = None

_JWKS_TTL_SECONDS = 3600


async def _fetch_jwks() -> dict:
    """Fetch JWKS from Clerk with a 5-second timeout."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(settings.clerk_jwks_url)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException as e:
        logger.error("Timed out fetching JWKS from %s", settings.clerk_jwks_url)
        raise HTTPException(401, "Authentication service unavailable") from e
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching JWKS: %s", e)
        raise HTTPException(401, "Authentication service unavailable") from e


async def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = datetime.now(timezone.utc)
    cache_expired = (
        _jwks_fetched_at is None
        or (now - _jwks_fetched_at).total_seconds() >= _JWKS_TTL_SECONDS
    )
    if _jwks_cache is None or cache_expired:
        _jwks_cache = await _fetch_jwks()
        _jwks_fetched_at = now
    return _jwks_cache


def _decode_options() -> dict:
    if settings.clerk_audience:
        return {"verify_aud": True}
    return {"verify_aud": False}


def _decode_kwargs() -> dict:
    kwargs: dict = {}
    if settings.clerk_issuer:
        kwargs["issuer"] = settings.clerk_issuer
    if settings.clerk_audience:
        kwargs["audience"] = settings.clerk_audience
    return kwargs


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
            options=_decode_options(),
            **_decode_kwargs(),
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: no subject")
        return user_id
    except JWTError as e:
        # Refresh-on-key-miss: if the kid was not found in the cached JWKS,
        # clear the cache and retry once with a freshly fetched JWKS.
        if "kid" in str(e).lower():
            logger.info("JWT kid not found in cached JWKS; refreshing cache")
            global _jwks_cache, _jwks_fetched_at
            _jwks_cache = None
            _jwks_fetched_at = None
            try:
                jwks = await _get_jwks()
                payload = jwt.decode(
                    token,
                    jwks,
                    algorithms=["RS256"],
                    options=_decode_options(),
                    **_decode_kwargs(),
                )
                user_id = payload.get("sub")
                if not user_id:
                    raise HTTPException(401, "Invalid token: no subject")
                return user_id
            except JWTError as retry_e:
                logger.warning("JWT validation failed after JWKS refresh: %s", retry_e)
                raise HTTPException(401, "Invalid or expired token") from None
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(401, "Invalid or expired token") from None
