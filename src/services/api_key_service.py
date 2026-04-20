from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.api_key_repository import APIKeyRepository
from src.storage.postgres.models_business import APIKey, Prompt, User
from src.utils.datetime_utils import coerce_any_to_utc_datetime, utc_now_naive

API_KEY_HEADER = "X-API-Key"
API_KEY_PREFIX = "pk_"


@dataclass
class APIKeyCreateResult:
    record: APIKey
    plain_key: str


def hash_api_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode("utf-8")).hexdigest()


def _generate_plain_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def _extract_api_key(request: Request, *, allow_bearer: bool = True) -> str | None:
    key_from_header = request.headers.get(API_KEY_HEADER)
    if key_from_header:
        return key_from_header.strip()

    if not allow_bearer:
        return None

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    prefix = "Bearer "
    if auth_header.startswith(prefix):
        token = auth_header[len(prefix) :].strip()
        return token or None
    return None


async def create_api_key(
    db: AsyncSession,
    *,
    name: str,
    user_id: int | None,
    department_id: int | None,
    expires_at: str | None,
    is_enabled: bool,
    created_by: str | None,
) -> APIKeyCreateResult:
    expires_at_dt = coerce_any_to_utc_datetime(expires_at)
    if expires_at_dt is not None:
        expires_at_dt = expires_at_dt.replace(tzinfo=None)
        if expires_at_dt <= utc_now_naive():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="过期时间必须晚于当前时间")

    plain_key = _generate_plain_api_key()
    key_hash = hash_api_key(plain_key)
    key_prefix = plain_key[:12]

    repo = APIKeyRepository(db)
    item = await repo.create(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        user_id=user_id,
        department_id=department_id,
        expires_at=expires_at_dt,
        is_enabled=is_enabled,
        created_by=created_by,
    )
    return APIKeyCreateResult(record=item, plain_key=plain_key)


async def authenticate_api_key_from_request(
    db: AsyncSession,
    request: Request,
    *,
    allow_bearer: bool = True,
) -> APIKey:
    token = _extract_api_key(request, allow_bearer=allow_bearer)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 API Key")

    key_hash = hash_api_key(token)
    repo = APIKeyRepository(db)
    item = await repo.get_by_hash(key_hash)
    if item is None or not item.is_valid():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或已过期的 API Key")

    await repo.touch_last_used(item)
    return item


async def can_access_prompt_by_scope(db: AsyncSession, api_key: APIKey, prompt: Prompt) -> bool:
    if prompt.is_dir:
        return False

    owner_username = prompt.created_by
    if not owner_username:
        return False

    result = await db.execute(select(User).where(User.username == owner_username, User.is_deleted == 0))
    owner = result.scalar_one_or_none()
    if owner is None:
        return False

    if api_key.user_id is not None and owner.id != api_key.user_id:
        return False

    if api_key.department_id is not None and owner.department_id != api_key.department_id:
        return False

    return True
