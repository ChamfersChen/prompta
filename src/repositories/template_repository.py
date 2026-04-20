"""提示词模板 Repository"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.postgres.models_business import (
    Template,
    TemplateFavorite,
    TemplateFavoriteFolder,
    TemplateRating,
    TemplateComment,
)


class TemplateRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ========== Template CRUD ==========

    async def list_public(
        self,
        *,
        community_type: str | None = None,
        department_id: int | None = None,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "latest",
        is_official: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[Template, int]], int]:
        comment_sub = (
            select(TemplateComment.template_id, func.count(TemplateComment.id).label("comment_count"))
            .group_by(TemplateComment.template_id)
            .subquery()
        )
        query = (
            select(Template, func.coalesce(comment_sub.c.comment_count, 0).label("comment_count"))
            .where(Template.is_public == True)
            .options(selectinload(Template.owner), selectinload(Template.department))
            .outerjoin(comment_sub, Template.id == comment_sub.c.template_id)
        )

        if community_type:
            query = query.where(Template.community_type == community_type)

        if department_id is None:
            query = query.where(Template.department_id.is_(None))
        else:
            query = query.where(Template.department_id == department_id)

        if is_official:
            query = query.where(Template.is_official == True)

        if category:
            query = query.where(Template.category == category)
        if keyword:
            query = query.where(Template.name.ilike(f"%{keyword}%") | Template.description.ilike(f"%{keyword}%"))

        if sort == "popular":
            query = query.order_by(Template.favorite_count.desc())
        elif sort == "rating":
            query = query.order_by(Template.rating.desc())
        else:
            query = query.order_by(Template.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        rows = result.all()
        items = [(row[0], row[1]) for row in rows]
        return items, total

    async def list_by_owner(self, owner_id: int, community_type: str | None = None) -> list[tuple[Template, int]]:
        comment_sub = (
            select(TemplateComment.template_id, func.count(TemplateComment.id).label("comment_count"))
            .group_by(TemplateComment.template_id)
            .subquery()
        )
        query = (
            select(Template, func.coalesce(comment_sub.c.comment_count, 0).label("comment_count"))
            .where(Template.owner_id == owner_id)
            .options(selectinload(Template.owner), selectinload(Template.department))
            .outerjoin(comment_sub, Template.id == comment_sub.c.template_id)
            .order_by(Template.created_at.desc())
        )
        if community_type:
            query = query.where(Template.community_type == community_type)
        result = await self.db.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def get_by_id(self, template_id: str) -> Template | None:
        query = (
            select(Template)
            .where(Template.id == template_id)
            .options(selectinload(Template.owner), selectinload(Template.department))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Template:
        now = kwargs.pop("created_at", None)
        if not now:
            from src.utils.datetime_utils import utc_now_naive

            now = utc_now_naive()

        item = Template(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self.db.add(item)
        await self.db.commit()
        created = await self.get_by_id(item.id)
        return created or item

    async def update(self, template_id: str, **kwargs) -> Template:
        item = await self.get_by_id(template_id)
        if item is None:
            raise ValueError(f"Template '{template_id}' not found")
        for key, value in kwargs.items():
            setattr(item, key, value)
        from src.utils.datetime_utils import utc_now_naive

        item.updated_at = utc_now_naive()
        await self.db.commit()
        updated = await self.get_by_id(template_id)
        return updated or item

    async def delete(self, template_id: str) -> bool:
        await self.db.execute(delete(TemplateRating).where(TemplateRating.template_id == template_id))
        await self.db.execute(delete(TemplateFavorite).where(TemplateFavorite.template_id == template_id))
        await self.db.execute(delete(TemplateComment).where(TemplateComment.template_id == template_id))
        stmt = delete(Template).where(Template.id == template_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def increment_usage(self, template_id: str) -> None:
        from sqlalchemy import update

        stmt = update(Template).where(Template.id == template_id).values(usage_count=Template.usage_count + 1)
        await self.db.execute(stmt)
        await self.db.commit()

    # ========== Favorites ==========

    async def add_favorite(
        self,
        user_id: int,
        template_id: str,
        item_type: str = "prompt",
        folder_path: str | None = None,
        department_id: int | None = None,
    ) -> TemplateFavorite:
        from src.utils.datetime_utils import utc_now_naive

        item = TemplateFavorite(
            user_id=user_id,
            template_id=template_id,
            department_id=department_id,
            item_type=item_type,
            folder_path=folder_path,
            created_at=utc_now_naive(),
        )
        self.db.add(item)

        template = await self.db.get(Template, template_id)
        if template:
            template.favorite_count = (template.favorite_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def remove_favorite(self, user_id: int, template_id: str, department_id: int | None = None) -> bool:
        stmt = delete(TemplateFavorite).where(
            TemplateFavorite.user_id == user_id,
            TemplateFavorite.template_id == template_id,
        )
        if department_id is None:
            stmt = stmt.where(TemplateFavorite.department_id.is_(None))
        else:
            stmt = stmt.where(TemplateFavorite.department_id == department_id)
        result = await self.db.execute(stmt)

        template = await self.db.get(Template, template_id)
        if template and template.favorite_count and template.favorite_count > 0:
            template.favorite_count = template.favorite_count - 1

        await self.db.commit()
        return result.rowcount > 0

    async def get_favorites_by_user(
        self,
        user_id: int,
        item_type: str | None = None,
        department_id: int | None = None,
    ) -> list[tuple[Template, int]]:
        comment_sub = (
            select(TemplateComment.template_id, func.count(TemplateComment.id).label("comment_count"))
            .group_by(TemplateComment.template_id)
            .subquery()
        )
        query = (
            select(Template, func.coalesce(comment_sub.c.comment_count, 0).label("comment_count"))
            .join(TemplateFavorite, Template.id == TemplateFavorite.template_id)
            .outerjoin(comment_sub, Template.id == comment_sub.c.template_id)
            .where(TemplateFavorite.user_id == user_id)
            .options(selectinload(Template.owner), selectinload(Template.department))
            .order_by(TemplateFavorite.created_at.desc())
        )
        if department_id is None:
            query = query.where(TemplateFavorite.department_id.is_(None))
        else:
            query = query.where(TemplateFavorite.department_id == department_id)
        if item_type:
            query = query.where(TemplateFavorite.item_type == item_type)
        result = await self.db.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def get_favorites_with_meta_by_user(
        self,
        user_id: int,
        item_type: str | None = None,
        department_id: int | None = None,
    ) -> list[tuple[Template, int, str | None, str | None]]:
        comment_sub = (
            select(TemplateComment.template_id, func.count(TemplateComment.id).label("comment_count"))
            .group_by(TemplateComment.template_id)
            .subquery()
        )
        query = (
            select(
                Template,
                func.coalesce(comment_sub.c.comment_count, 0).label("comment_count"),
                TemplateFavorite.folder_path,
                TemplateFavorite.item_type,
            )
            .join(TemplateFavorite, Template.id == TemplateFavorite.template_id)
            .outerjoin(comment_sub, Template.id == comment_sub.c.template_id)
            .where(TemplateFavorite.user_id == user_id)
            .options(selectinload(Template.owner), selectinload(Template.department))
            .order_by(TemplateFavorite.created_at.desc())
        )
        if department_id is None:
            query = query.where(TemplateFavorite.department_id.is_(None))
        else:
            query = query.where(TemplateFavorite.department_id == department_id)
        if item_type:
            query = query.where(TemplateFavorite.item_type == item_type)
        result = await self.db.execute(query)
        return [(row[0], row[1], row[2], row[3]) for row in result.all()]

    async def get_favorite_folders(
        self,
        user_id: int,
        item_type: str | None = None,
        department_id: int | None = None,
    ) -> list[str]:
        fav_stmt = select(TemplateFavorite.folder_path).where(
            TemplateFavorite.user_id == user_id,
            TemplateFavorite.folder_path.isnot(None),
            TemplateFavorite.folder_path != "",
        )
        folder_stmt = select(TemplateFavoriteFolder.folder_name).where(TemplateFavoriteFolder.user_id == user_id)

        if department_id is None:
            fav_stmt = fav_stmt.where(TemplateFavorite.department_id.is_(None))
            folder_stmt = folder_stmt.where(TemplateFavoriteFolder.department_id.is_(None))
        else:
            fav_stmt = fav_stmt.where(TemplateFavorite.department_id == department_id)
            folder_stmt = folder_stmt.where(TemplateFavoriteFolder.department_id == department_id)

        if item_type:
            fav_stmt = fav_stmt.where(TemplateFavorite.item_type == item_type)
            folder_stmt = folder_stmt.where(TemplateFavoriteFolder.item_type == item_type)

        fav_result = await self.db.execute(fav_stmt.distinct())
        folder_result = await self.db.execute(folder_stmt.distinct())

        names = {row[0] for row in fav_result.all() if row[0]}
        names.update({row[0] for row in folder_result.all() if row[0]})
        return sorted(names)

    async def rename_favorite_folder(
        self,
        user_id: int,
        old_folder_path: str,
        new_folder_path: str,
        department_id: int | None = None,
        item_type: str | None = None,
    ) -> int:
        stmt = (
            update(TemplateFavorite)
            .where(
                TemplateFavorite.user_id == user_id,
                TemplateFavorite.folder_path == old_folder_path,
            )
            .values(folder_path=new_folder_path)
        )
        folder_stmt = (
            update(TemplateFavoriteFolder)
            .where(
                TemplateFavoriteFolder.user_id == user_id,
                TemplateFavoriteFolder.folder_name == old_folder_path,
            )
            .values(folder_name=new_folder_path)
        )

        if department_id is None:
            stmt = stmt.where(TemplateFavorite.department_id.is_(None))
            folder_stmt = folder_stmt.where(TemplateFavoriteFolder.department_id.is_(None))
        else:
            stmt = stmt.where(TemplateFavorite.department_id == department_id)
            folder_stmt = folder_stmt.where(TemplateFavoriteFolder.department_id == department_id)

        if item_type:
            stmt = stmt.where(TemplateFavorite.item_type == item_type)
            folder_stmt = folder_stmt.where(TemplateFavoriteFolder.item_type == item_type)

        result = await self.db.execute(stmt)
        folder_result = await self.db.execute(folder_stmt)
        await self.db.commit()
        return max(result.rowcount or 0, folder_result.rowcount or 0)

    async def create_favorite_folder(
        self,
        user_id: int,
        folder_name: str,
        item_type: str = "prompt",
        department_id: int | None = None,
    ) -> TemplateFavoriteFolder:
        from src.utils.datetime_utils import utc_now_naive

        now = utc_now_naive()
        folder = TemplateFavoriteFolder(
            user_id=user_id,
            department_id=department_id,
            item_type=item_type,
            folder_name=folder_name,
            created_at=now,
            updated_at=now,
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def delete_favorite_folder(
        self,
        user_id: int,
        folder_name: str,
        item_type: str = "prompt",
        department_id: int | None = None,
    ) -> int:
        clear_fav_stmt = (
            update(TemplateFavorite)
            .where(
                TemplateFavorite.user_id == user_id,
                TemplateFavorite.folder_path == folder_name,
                TemplateFavorite.item_type == item_type,
            )
            .values(folder_path=None)
        )
        stmt = delete(TemplateFavoriteFolder).where(
            TemplateFavoriteFolder.user_id == user_id,
            TemplateFavoriteFolder.folder_name == folder_name,
            TemplateFavoriteFolder.item_type == item_type,
        )
        if department_id is None:
            clear_fav_stmt = clear_fav_stmt.where(TemplateFavorite.department_id.is_(None))
            stmt = stmt.where(TemplateFavoriteFolder.department_id.is_(None))
        else:
            clear_fav_stmt = clear_fav_stmt.where(TemplateFavorite.department_id == department_id)
            stmt = stmt.where(TemplateFavoriteFolder.department_id == department_id)
        await self.db.execute(clear_fav_stmt)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount or 0

    async def folder_exists(
        self,
        user_id: int,
        folder_name: str,
        item_type: str = "prompt",
        department_id: int | None = None,
    ) -> bool:
        stmt = select(TemplateFavoriteFolder.id).where(
            TemplateFavoriteFolder.user_id == user_id,
            TemplateFavoriteFolder.folder_name == folder_name,
            TemplateFavoriteFolder.item_type == item_type,
        )
        if department_id is None:
            stmt = stmt.where(TemplateFavoriteFolder.department_id.is_(None))
        else:
            stmt = stmt.where(TemplateFavoriteFolder.department_id == department_id)
        result = await self.db.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def is_favorited(self, user_id: int, template_id: str, department_id: int | None = None) -> bool:
        query = select(TemplateFavorite).where(
            TemplateFavorite.user_id == user_id,
            TemplateFavorite.template_id == template_id,
        )
        if department_id is None:
            query = query.where(TemplateFavorite.department_id.is_(None))
        else:
            query = query.where(TemplateFavorite.department_id == department_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    # ========== Ratings ==========

    async def rate_template(self, user_id: int, template_id: str, rating: int) -> TemplateRating:
        from src.utils.datetime_utils import utc_now_naive

        existing = await self.get_rating(user_id, template_id)
        if existing:
            old_rating = existing.rating
            existing.rating = rating
            existing.updated_at = utc_now_naive()
            await self.db.commit()

            avg_stmt = select(func.avg(TemplateRating.rating)).where(TemplateRating.template_id == template_id)
            avg_result = await self.db.execute(avg_stmt)
            new_avg = avg_result.scalar() or 0.0
            t_result = await self.db.execute(select(Template).where(Template.id == template_id))
            template = t_result.scalar_one()
            template.rating = round(new_avg, 2)
            await self.db.commit()
            return existing
        else:
            item = TemplateRating(
                user_id=user_id,
                template_id=template_id,
                rating=rating,
                created_at=utc_now_naive(),
                updated_at=utc_now_naive(),
            )
            self.db.add(item)
            await self.db.commit()

            t_result = await self.db.execute(select(Template).where(Template.id == template_id))
            template = t_result.scalar_one()
            template.rating_count += 1
            avg_stmt = select(func.avg(TemplateRating.rating)).where(TemplateRating.template_id == template_id)
            avg_result = await self.db.execute(avg_stmt)
            template.rating = round(avg_result.scalar() or 0.0, 2)
            await self.db.commit()
            return item

    async def get_rating(self, user_id: int, template_id: str) -> TemplateRating | None:
        query = select(TemplateRating).where(
            TemplateRating.user_id == user_id,
            TemplateRating.template_id == template_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ========== Comments ==========

    async def add_comment(self, user_id: int, template_id: str, content: str) -> TemplateComment:
        from src.utils.datetime_utils import utc_now_naive

        item = TemplateComment(
            user_id=user_id,
            template_id=template_id,
            content=content,
            created_at=utc_now_naive(),
            updated_at=utc_now_naive(),
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_comments(self, template_id: str) -> list[TemplateComment]:
        from sqlalchemy.orm import selectinload

        query = (
            select(TemplateComment)
            .where(TemplateComment.template_id == template_id)
            .options(selectinload(TemplateComment.owner))
            .order_by(TemplateComment.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        stmt = delete(TemplateComment).where(
            TemplateComment.id == comment_id,
            TemplateComment.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_comment_count(self, template_id: str) -> int:
        stmt = select(func.count(TemplateComment.id)).where(TemplateComment.template_id == template_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
