"""提示词模板 Service"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.template_repository import TemplateRepository
from src.utils.logging_config import logger


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TemplateRepository(db)

    # ========== 官方/社区模板列表 ==========

    async def get_official_templates(
        self,
        *,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "latest",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取官方模板（is_official=True 且 is_public=True）"""
        items, total = await self.repo.list_public(
            category=category,
            keyword=keyword,
            sort=sort,
            is_official=True,
            page=page,
            page_size=page_size,
        )
        return [item.to_list_dict() for item in items], total

    async def get_community_templates(
        self,
        *,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "latest",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取社区公开模板（is_official=False 且 is_public=True）"""
        items, total = await self.repo.list_public(
            category=category,
            keyword=keyword,
            sort=sort,
            is_official=False,
            page=page,
            page_size=page_size,
        )
        return [item.to_list_dict() for item in items], total

    # ========== 我的模板 ==========

    async def get_my_templates(self, owner_id: int) -> list[dict]:
        items = await self.repo.list_by_owner(owner_id)
        return [item.to_list_dict() for item in items]

    # ========== 发布模板 ==========

    async def publish_template(
        self,
        *,
        name: str,
        category: str,
        description: str,
        tags: list[str],
        content: str,
        variables: list[dict],
        is_public: bool,
        is_official: bool = False,
        source_path: str | None,
        owner_id: int,
    ) -> dict:
        item = await self.repo.create(
            name=name,
            category=category,
            description=description,
            tags=tags,
            content=content,
            variables=variables,
            is_public=is_public,
            is_official=is_official,
            source_path=source_path,
            owner_id=owner_id,
        )
        logger.info(f"Template published: {item.id} by user {owner_id} (official={is_official})")
        return item.to_dict()

    # ========== 更新模板 ==========

    async def update_template(
        self,
        template_id: str,
        owner_id: int,
        **kwargs,
    ) -> dict:
        item = await self.repo.get_by_id(template_id)
        if not item:
            raise ValueError("模板不存在")
        if item.owner_id != owner_id:
            raise ValueError("无权修改此模板")

        allowed = {"name", "category", "description", "tags", "content", "variables", "is_public"}
        update_data = {k: v for k, v in kwargs.items() if k in allowed}
        item = await self.repo.update(template_id, **update_data)
        return item.to_dict()

    # ========== 删除模板 ==========

    async def delete_template(self, template_id: str, owner_id: int) -> bool:
        item = await self.repo.get_by_id(template_id)
        if not item:
            raise ValueError("模板不存在")
        if item.owner_id != owner_id:
            raise ValueError("无权删除此模板")
        return await self.repo.delete(template_id)

    # ========== 获取详情 ==========

    async def get_template_detail(self, template_id: str) -> dict | None:
        item = await self.repo.get_by_id(template_id)
        if not item:
            return None
        await self.repo.increment_usage(template_id)
        return item.to_dict()

    # ========== Fork 模板 ==========

    async def fork_template(self, template_id: str, owner_id: int) -> dict:
        source = await self.repo.get_by_id(template_id)
        if not source:
            raise ValueError("模板不存在")

        item = await self.repo.create(
            name=f"{source.name} (Fork)",
            category=source.category,
            description=source.description,
            tags=source.tags,
            content=source.content,
            variables=source.variables,
            is_public=False,
            source_path=source.source_path,
            owner_id=owner_id,
        )
        logger.info(f"Template forked: {source.id} -> {item.id}")
        return item.to_dict()

    # ========== 收藏 ==========

    async def add_favorite(self, user_id: int, template_id: str, folder_path: str = "", username: str = "") -> dict:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        if await self.repo.is_favorited(user_id, template_id):
            raise ValueError("已收藏")

        fav = await self.repo.add_favorite(user_id, template_id)

        if folder_path:
            from src.services.prompt_service import create_prompt_node

            file_path = (
                f"{folder_path}/{template.name}.md"
                if not template.name.endswith(".md")
                else f"{folder_path}/{template.name}"
            )
            try:
                await create_prompt_node(
                    self.db,
                    path=file_path,
                    is_dir=False,
                    content=template.content,
                    updated_by=username,
                )
                logger.info(f"Template '{template.name}' copied to prompt management: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to copy template to prompt management: {e}")

        return fav.to_dict()

    async def remove_favorite(self, user_id: int, template_id: str) -> bool:
        return await self.repo.remove_favorite(user_id, template_id)

    async def get_favorites(self, user_id: int) -> list[dict]:
        items = await self.repo.get_favorites_by_user(user_id)
        return [item.to_list_dict() for item in items]

    # ========== 评分 ==========

    async def rate_template(self, user_id: int, template_id: str, rating: int) -> dict:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        result = await self.repo.rate_template(user_id, template_id, rating)
        return result.to_dict()

    async def get_user_rating(self, user_id: int, template_id: str) -> dict | None:
        rating = await self.repo.get_rating(user_id, template_id)
        if rating:
            return rating.to_dict()
        return None

    # ========== 评论 ==========

    async def add_comment(self, user_id: int, template_id: str, content: str) -> dict:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        comment = await self.repo.add_comment(user_id, template_id, content)
        return comment.to_dict()

    async def get_comments(self, template_id: str) -> list[dict]:
        items = await self.repo.get_comments(template_id)
        return [item.to_dict() for item in items]

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        return await self.repo.delete_comment(comment_id, user_id)
