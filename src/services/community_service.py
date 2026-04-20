"""社区模块 Service（提示词社区 + 收藏）"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.template_repository import TemplateRepository
from src.utils.logging_config import logger


class CommunityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TemplateRepository(db)

    # ========== 提示词社区 ==========

    @staticmethod
    def _can_access_template(template, department_id: int | None) -> bool:
        return template.department_id == department_id

    async def list_prompt_templates(
        self,
        *,
        department_id: int | None = None,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "latest",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        items, total = await self.repo.list_public(
            community_type="prompt",
            department_id=department_id,
            category=category,
            keyword=keyword,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return [{**item[0].to_list_dict(), "commentCount": item[1]} for item in items], total

    # ========== 我的模板（按类型筛选） ==========

    async def get_my_templates(self, owner_id: int, community_type: str | None = None) -> list[dict]:
        items = await self.repo.list_by_owner(owner_id, community_type=community_type)
        return [{**item[0].to_list_dict(), "commentCount": item[1]} for item in items]

    # ========== 发布提示词 ==========

    async def publish_prompt(
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
        department_id: int | None,
    ) -> dict:
        item = await self.repo.create(
            name=name,
            category=category,
            community_type="prompt",
            description=description,
            tags=tags,
            content=content,
            variables=variables,
            is_public=is_public,
            is_official=is_official,
            source_path=source_path,
            owner_id=owner_id,
            department_id=department_id,
        )
        logger.info(f"Prompt template published: {item.id} by user {owner_id}")
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

        allowed = {
            "name",
            "category",
            "description",
            "tags",
            "content",
            "variables",
            "is_public",
            "is_official",
            "file_tree",
            "source_slug",
        }
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

    async def get_template_detail(self, template_id: str, department_id: int | None = None) -> dict | None:
        item = await self.repo.get_by_id(template_id)
        if not item:
            return None
        if not self._can_access_template(item, department_id):
            return None
        await self.repo.increment_usage(template_id)
        comment_count = await self.repo.get_comment_count(template_id)
        return {**item.to_dict(), "commentCount": comment_count}

    # ========== Fork 模板 ==========

    async def fork_template(self, template_id: str, owner_id: int, department_id: int | None = None) -> dict:
        source = await self.repo.get_by_id(template_id)
        if not source:
            raise ValueError("模板不存在")
        if not self._can_access_template(source, department_id):
            raise ValueError("无权访问该模板")

        item = await self.repo.create(
            name=f"{source.name} (Fork)",
            category=source.category,
            community_type=source.community_type,
            description=source.description,
            tags=source.tags,
            content=source.content,
            variables=source.variables,
            file_tree=source.file_tree,
            is_public=False,
            source_path=source.source_path,
            source_slug=source.source_slug,
            owner_id=owner_id,
            department_id=department_id,
        )
        logger.info(f"Template forked: {source.id} -> {item.id}")
        return item.to_dict()

    # ========== 收藏（纯书签，不复制文件） ==========

    async def add_favorite(
        self,
        user_id: int,
        template_id: str,
        item_type: str = "prompt",
        folder_path: str | None = None,
        department_id: int | None = None,
    ) -> dict:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        if template.department_id != department_id:
            raise ValueError("无权访问该模板")
        if await self.repo.is_favorited(user_id, template_id, department_id=department_id):
            raise ValueError("已收藏")

        folder_name = (folder_path or "").strip() or None
        if folder_name and not await self.repo.folder_exists(
            user_id=user_id,
            folder_name=folder_name,
            item_type=item_type,
            department_id=department_id,
        ):
            await self.repo.create_favorite_folder(
                user_id=user_id,
                folder_name=folder_name,
                item_type=item_type,
                department_id=department_id,
            )

        fav = await self.repo.add_favorite(
            user_id,
            template_id,
            item_type=item_type,
            folder_path=folder_name,
            department_id=department_id,
        )
        return fav.to_dict()

    async def remove_favorite(self, user_id: int, template_id: str, department_id: int | None = None) -> bool:
        removed = await self.repo.remove_favorite(user_id, template_id, department_id=department_id)
        return removed

    async def get_favorites(
        self,
        user_id: int,
        item_type: str | None = None,
        department_id: int | None = None,
    ) -> list[dict]:
        items = await self.repo.get_favorites_with_meta_by_user(
            user_id,
            item_type=item_type,
            department_id=department_id,
        )
        return [
            {
                **item[0].to_list_dict(),
                "commentCount": item[1],
                "_favorite_folder": item[2],
                "_favorite_item_type": item[3],
            }
            for item in items
        ]

    async def get_favorite_folders(
        self,
        user_id: int,
        item_type: str | None = None,
        department_id: int | None = None,
    ) -> list[str]:
        return await self.repo.get_favorite_folders(user_id, item_type=item_type, department_id=department_id)

    # ========== 评分 ==========

    async def rate_template(
        self,
        user_id: int,
        template_id: str,
        rating: int,
        department_id: int | None = None,
    ) -> dict:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        if not self._can_access_template(template, department_id):
            raise ValueError("无权访问该模板")
        result = await self.repo.rate_template(user_id, template_id, rating)
        return result.to_dict()

    async def get_user_rating(
        self,
        user_id: int,
        template_id: str,
        department_id: int | None = None,
    ) -> dict | None:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        if not self._can_access_template(template, department_id):
            raise ValueError("无权访问该模板")
        rating = await self.repo.get_rating(user_id, template_id)
        if rating:
            return rating.to_dict()
        return None

    # ========== 评论 ==========

    async def add_comment(
        self,
        user_id: int,
        template_id: str,
        content: str,
        department_id: int | None = None,
    ) -> dict:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        if not self._can_access_template(template, department_id):
            raise ValueError("无权访问该模板")
        comment = await self.repo.add_comment(user_id, template_id, content)
        return comment.to_dict()

    async def get_comments(self, template_id: str, department_id: int | None = None) -> list[dict]:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise ValueError("模板不存在")
        if not self._can_access_template(template, department_id):
            raise ValueError("无权访问该模板")
        items = await self.repo.get_comments(template_id)
        return [item.to_dict() for item in items]

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        return await self.repo.delete_comment(comment_id, user_id)

    # ========== 收藏夹 ==========

    async def create_favorite_folder(
        self,
        user_id: int,
        folder_name: str,
        item_type: str = "prompt",
        department_id: int | None = None,
    ) -> dict:
        name = (folder_name or "").strip()
        if not name:
            raise ValueError("收藏夹名称不能为空")
        if await self.repo.folder_exists(
            user_id=user_id,
            folder_name=name,
            item_type=item_type,
            department_id=department_id,
        ):
            raise ValueError("收藏夹已存在")
        folder = await self.repo.create_favorite_folder(
            user_id=user_id,
            folder_name=name,
            item_type=item_type,
            department_id=department_id,
        )
        return folder.to_dict()

    async def rename_favorite_folder(
        self,
        user_id: int,
        old_folder_path: str,
        new_folder_path: str,
        department_id: int | None = None,
        item_type: str | None = None,
    ) -> int:
        old_name = (old_folder_path or "").strip()
        new_name = (new_folder_path or "").strip()

        if not old_name:
            raise ValueError("原收藏夹名称不能为空")
        if not new_name:
            raise ValueError("新收藏夹名称不能为空")
        if old_name == new_name:
            return 0

        existing_folders = await self.repo.get_favorite_folders(
            user_id,
            item_type=item_type,
            department_id=department_id,
        )
        if new_name in existing_folders:
            raise ValueError("收藏夹已存在")

        updated = await self.repo.rename_favorite_folder(
            user_id=user_id,
            old_folder_path=old_name,
            new_folder_path=new_name,
            department_id=department_id,
            item_type=item_type,
        )
        if updated == 0:
            raise ValueError("收藏夹不存在")
        return updated

    async def delete_favorite_folder(
        self,
        user_id: int,
        folder_name: str,
        item_type: str = "prompt",
        department_id: int | None = None,
    ) -> int:
        name = (folder_name or "").strip()
        if not name:
            raise ValueError("收藏夹名称不能为空")
        return await self.repo.delete_favorite_folder(
            user_id=user_id,
            folder_name=name,
            item_type=item_type,
            department_id=department_id,
        )
