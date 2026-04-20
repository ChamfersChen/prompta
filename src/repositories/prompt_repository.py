from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.postgres.models_business import Prompt
from src.utils.datetime_utils import utc_now_naive


class PromptRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def list_all(self) -> list[Prompt]:
        result = await self.db.execute(select(Prompt).order_by(Prompt.updated_at.desc(), Prompt.id.desc()))
        return list(result.scalars().all())

    async def list_by_user(self, username: str) -> list[Prompt]:
        result = await self.db.execute(
            select(Prompt).where(Prompt.created_by == username).order_by(Prompt.updated_at.desc(), Prompt.id.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: int) -> Prompt | None:
        result = await self.db.execute(select(Prompt).where(Prompt.id == id))
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> Prompt | None:
        result = await self.db.execute(select(Prompt).where(Prompt.external_id == external_id))
        return result.scalar_one_or_none()

    async def get_by_name_path(self, name: str, path: str) -> Prompt | None:
        result = await self.db.execute(select(Prompt).where(Prompt.path == path).where(Prompt.created_by == name))
        return result.scalar_one_or_none()

    async def get_by_path(self, path: str) -> Prompt | None:
        result = await self.db.execute(select(Prompt).where(Prompt.path == path))
        return result.scalar_one_or_none()

    async def exists_id(self, id: int) -> bool:
        return (await self.get_by_id(id)) is not None

    async def update(self, path: str, content: str, updated_by: str | None) -> Prompt:
        item = await self.get_by_path(path)
        if item is None:
            raise ValueError(f"Prompt with path '{path}' not found")
        item.description = content
        item.updated_by = updated_by
        item.updated_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def create(
        self,
        *,
        name: str,
        path: str,
        description: str,
        dir_path: str,
        is_dir: bool = False,
        created_by: str | None,
    ) -> Prompt:
        now = utc_now_naive()
        item = Prompt(
            name=name,
            path=path,
            description=description,
            dir_path=dir_path,
            is_dir=1 if is_dir else 0,
            created_by=created_by,
            updated_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_dependencies(
        self,
        item: Prompt,
        *,
        updated_by: str | None,
    ) -> Prompt:
        item.updated_by = updated_by
        item.updated_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_metadata(
        self,
        item: Prompt,
        *,
        name: str,
        description: str,
        path: str,
        updated_by: str | None,
    ) -> Prompt:
        item.name = name
        item.path = path
        item.description = description
        item.updated_by = updated_by
        item.updated_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: Prompt) -> None:
        await self.db.delete(item)
        await self.db.commit()

    async def delete_by_name_path(self, name: str, path: str) -> None:
        item = await self.get_by_name_path(name, path)
        if item:
            await self.db.delete(item)
            await self.db.commit()

    async def list_by_path_prefix(self, name: str, path_prefix: str) -> list[Prompt]:
        """获取指定路径前缀的所有文件（用于删除文件夹时）"""
        normalized_prefix = (path_prefix or "").strip().strip("/")
        if not normalized_prefix:
            return []

        result = await self.db.execute(
            select(Prompt)
            .where(Prompt.created_by == name)
            .where(or_(Prompt.path == normalized_prefix, Prompt.path.like(f"{normalized_prefix}/%")))
        )
        return list(result.scalars().all())

    async def delete_by_path_prefix(self, name: str, path_prefix: str) -> list[str]:
        """删除指定路径前缀的所有文件，返回被删除的文件路径列表"""
        items = await self.list_by_path_prefix(name, path_prefix)
        deleted_paths = []
        for item in items:
            deleted_paths.append(item.path)
            await self.db.delete(item)
        await self.db.commit()
        return deleted_paths
