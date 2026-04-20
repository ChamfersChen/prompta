from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.postgres.models_business import APIKey
from src.utils.datetime_utils import utc_now_naive


class APIKeyRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def list_all(self) -> list[APIKey]:
        result = await self.db.execute(select(APIKey).order_by(APIKey.created_at.desc(), APIKey.id.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, key_id: int) -> APIKey | None:
        result = await self.db.execute(select(APIKey).where(APIKey.id == key_id))
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        result = await self.db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        key_hash: str,
        key_prefix: str,
        name: str,
        user_id: int | None,
        department_id: int | None,
        expires_at,
        is_enabled: bool,
        created_by: str | None,
    ) -> APIKey:
        now = utc_now_naive()
        item = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            user_id=user_id,
            department_id=department_id,
            expires_at=expires_at,
            is_enabled=is_enabled,
            created_by=created_by,
            created_at=now,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def set_enabled(self, item: APIKey, is_enabled: bool) -> APIKey:
        item.is_enabled = is_enabled
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def touch_last_used(self, item: APIKey) -> APIKey:
        item.last_used_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: APIKey) -> None:
        await self.db.delete(item)
        await self.db.commit()
