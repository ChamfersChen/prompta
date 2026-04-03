"""提示词模板 Repository"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.postgres.models_business import Template, TemplateFavorite, TemplateRating, TemplateComment


class TemplateRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ========== Template CRUD ==========

    async def list_public(
        self,
        *,
        category: str | None = None,
        keyword: str | None = None,
        sort: str = "latest",
        is_official: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Template], int]:
        query = select(Template).where(Template.is_public == True).options(selectinload(Template.owner))

        if is_official:
            query = query.where(Template.is_official == True)
        else:
            query = query.where(Template.is_official == False)

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
        items = list(result.scalars().all())
        return items, total

    async def list_by_owner(self, owner_id: int) -> list[Template]:
        query = (
            select(Template)
            .where(Template.owner_id == owner_id)
            .options(selectinload(Template.owner))
            .order_by(Template.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, template_id: str) -> Template | None:
        query = select(Template).where(Template.id == template_id).options(selectinload(Template.owner))
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
        await self.db.refresh(item)
        await self.db.execute(select(Template.owner).where(Template.id == item.id))
        await self.db.refresh(item, attribute_names=["owner"])
        return item

    async def update(self, template_id: str, **kwargs) -> Template:
        item = await self.get_by_id(template_id)
        if item is None:
            raise ValueError(f"Template '{template_id}' not found")
        for key, value in kwargs.items():
            setattr(item, key, value)
        from src.utils.datetime_utils import utc_now_naive

        item.updated_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, template_id: str) -> bool:
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

    async def add_favorite(self, user_id: int, template_id: str) -> TemplateFavorite:
        from src.utils.datetime_utils import utc_now_naive

        item = TemplateFavorite(user_id=user_id, template_id=template_id, created_at=utc_now_naive())
        self.db.add(item)

        template = await self.db.get(Template, template_id)
        if template:
            template.favorite_count = (template.favorite_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def remove_favorite(self, user_id: int, template_id: str) -> bool:
        stmt = delete(TemplateFavorite).where(
            TemplateFavorite.user_id == user_id,
            TemplateFavorite.template_id == template_id,
        )
        result = await self.db.execute(stmt)

        template = await self.db.get(Template, template_id)
        if template and template.favorite_count and template.favorite_count > 0:
            template.favorite_count = template.favorite_count - 1

        await self.db.commit()
        return result.rowcount > 0

    async def get_favorites_by_user(self, user_id: int) -> list[Template]:
        query = (
            select(Template)
            .join(TemplateFavorite, Template.id == TemplateFavorite.template_id)
            .where(TemplateFavorite.user_id == user_id)
            .options(selectinload(Template.owner))
            .order_by(TemplateFavorite.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def is_favorited(self, user_id: int, template_id: str) -> bool:
        query = select(TemplateFavorite).where(
            TemplateFavorite.user_id == user_id,
            TemplateFavorite.template_id == template_id,
        )
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
