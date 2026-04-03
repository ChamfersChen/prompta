"""提示词市场路由"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user, get_superadmin_user
from src.services.template_service import TemplateService
from src.storage.postgres.models_business import User
from src.utils.logging_config import logger

market = APIRouter(prefix="/market", tags=["market"])


def _raise_from_value_error(e: ValueError) -> None:
    message = str(e)
    status_code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=status_code, detail=message)


# ========== Pydantic 模型 ==========


class PublishTemplateRequest(BaseModel):
    name: str = Field(..., description="模板名称")
    category: str = Field(..., description="分类")
    description: str = Field("", description="模板描述")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    content: str = Field(..., description="Prompt 内容")
    variables: list[dict] = Field(default_factory=list, description="变量定义")
    is_public: bool = Field(False, description="是否公开到社区")
    is_official: bool = Field(False, description="是否为官方模板（仅超管）")
    source_path: str | None = Field(None, description="源文件路径")


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    content: str | None = None
    variables: list[dict] | None = None
    is_public: bool | None = None


class RateTemplateRequest(BaseModel):
    template_id: str = Field(..., description="模板ID")
    rating: int = Field(..., ge=0, le=5, description="评分 1-5")


class FavoriteRequest(BaseModel):
    template_id: str = Field(..., description="模板ID")
    folder_path: str = Field("", description="提示词管理中的文件夹路径")


class CommentRequest(BaseModel):
    content: str = Field(..., min_length=1, description="评论内容")


# ============================================================
# 固定路径路由（必须在 /{template_id} 之前定义）
# ============================================================

# ========== 官方模板 ==========


@market.get("/official")
async def get_official_templates(
    category: str | None = Query(None, description="分类筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    sort: str = Query("latest", description="排序: popular/latest/rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取官方模板列表"""
    try:
        service = TemplateService(db)
        items, total = await service.get_official_templates(
            category=category,
            keyword=keyword,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return {"list": items, "total": total}
    except Exception as e:
        logger.error(f"获取官方模板列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取官方模板列表失败")


# ========== 社区模板 ==========


@market.get("/community")
async def get_community_templates(
    category: str | None = Query(None, description="分类筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    sort: str = Query("latest", description="排序: popular/latest/rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取社区模板列表"""
    try:
        service = TemplateService(db)
        items, total = await service.get_community_templates(
            category=category,
            keyword=keyword,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return {"list": items, "total": total}
    except Exception as e:
        logger.error(f"获取社区模板列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取社区模板列表失败")


# ========== 我的模板 ==========


@market.get("/mine")
async def get_my_templates(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的模板列表"""
    try:
        service = TemplateService(db)
        items = await service.get_my_templates(current_user.id)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取我的模板失败: {e}")
        raise HTTPException(status_code=500, detail="获取我的模板失败")


# ========== 发布模板 ==========


@market.post("/publish")
async def publish_template(
    payload: PublishTemplateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """发布模板到市场"""
    try:
        service = TemplateService(db)
        logger.info(f"用户 {current_user.username} 发布模板: {payload.name} (官方: {payload.is_official})")
        is_official = payload.is_official
        if is_official:
            if current_user.role != "superadmin":
                raise HTTPException(status_code=403, detail="仅超级管理员可发布官方模板")

        result = await service.publish_template(
            name=payload.name,
            category=payload.category,
            description=payload.description,
            tags=payload.tags,
            content=payload.content,
            variables=payload.variables,
            is_public=payload.is_public,
            is_official=is_official,
            source_path=payload.source_path,
            owner_id=current_user.id,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"发布模板失败: {e}")
        raise HTTPException(status_code=500, detail="发布模板失败")


# ========== 导入模板 ==========


@market.post("/import")
async def import_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """导入模板（JSON 文件）"""
    try:
        content = await file.read()
        data = json.loads(content)

        service = TemplateService(db)
        result = await service.publish_template(
            name=data.get("name", "导入的模板"),
            category=data.get("category", "writing"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            content=data.get("content", ""),
            variables=data.get("variables", []),
            is_public=False,
            source_path=data.get("source_path"),
            owner_id=current_user.id,
        )
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")
    except Exception as e:
        logger.error(f"导入模板失败: {e}")
        raise HTTPException(status_code=500, detail="导入模板失败")


# ========== 排行榜 ==========


@market.get("/leaderboard")
async def get_leaderboard(
    type: str = Query("popular", description="排序类型: popular/latest/rating"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取模板排行榜"""
    try:
        service = TemplateService(db)
        items, _ = await service.get_community_templates(sort=type, page=1, page_size=limit)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取排行榜失败: {e}")
        raise HTTPException(status_code=500, detail="获取排行榜失败")


# ========== 推荐模板 ==========


@market.get("/recommended")
async def get_recommended_templates(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取推荐模板（按评分排序）"""
    try:
        service = TemplateService(db)
        items, _ = await service.get_community_templates(sort="rating", page=1, page_size=limit)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取推荐模板失败: {e}")
        raise HTTPException(status_code=500, detail="获取推荐模板失败")


# ========== 收藏 ==========


@market.get("/favorites")
async def get_favorites(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的收藏"""
    try:
        service = TemplateService(db)
        items = await service.get_favorites(current_user.id)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取收藏失败: {e}")
        raise HTTPException(status_code=500, detail="获取收藏失败")


@market.post("/favorites")
async def add_favorite(
    payload: FavoriteRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏模板（同时复制模板到提示词管理）"""
    try:
        service = TemplateService(db)
        result = await service.add_favorite(
            user_id=current_user.id,
            template_id=payload.template_id,
            folder_path=payload.folder_path,
            username=current_user.username,
        )
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"收藏模板失败: {e}")
        raise HTTPException(status_code=500, detail="收藏模板失败")


@market.delete("/favorites/{template_id}")
async def remove_favorite(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏"""
    try:
        service = TemplateService(db)
        await service.remove_favorite(current_user.id, template_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"取消收藏失败: {e}")
        raise HTTPException(status_code=500, detail="取消收藏失败")


# ========== 评分 ==========


@market.get("/rate/{template_id}")
async def get_my_rating(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的评分"""
    try:
        service = TemplateService(db)
        result = await service.get_user_rating(current_user.id, template_id)
        return result
    except Exception as e:
        logger.error(f"获取评分失败: {e}")
        raise HTTPException(status_code=500, detail="获取评分失败")


@market.post("/rate")
async def rate_template(
    payload: RateTemplateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """评分模板"""
    try:
        service = TemplateService(db)
        result = await service.rate_template(current_user.id, payload.template_id, payload.rating)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"评分模板失败: {e}")
        raise HTTPException(status_code=500, detail="评分模板失败")


# ============================================================
# 动态路径路由 /{template_id}（必须放在固定路径之后）
# ============================================================


# ========== 模板详情 ==========


@market.get("/{template_id}")
async def get_template_detail(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    try:
        service = TemplateService(db)
        result = await service.get_template_detail(template_id)
        if not result:
            raise HTTPException(status_code=404, detail="模板不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取模板详情失败")


# ========== 更新模板 ==========


@market.put("/{template_id}")
async def update_template(
    template_id: str,
    payload: UpdateTemplateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """更新模板（仅创建者）"""
    try:
        service = TemplateService(db)
        update_data = payload.model_dump(exclude_unset=True)
        result = await service.update_template(template_id, current_user.id, **update_data)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        raise HTTPException(status_code=500, detail="更新模板失败")


# ========== 删除模板 ==========


@market.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除模板（仅创建者）"""
    try:
        service = TemplateService(db)
        await service.delete_template(template_id, current_user.id)
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        raise HTTPException(status_code=500, detail="删除模板失败")


# ========== Fork 模板 ==========


@market.post("/{template_id}/fork")
async def fork_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """Fork 模板"""
    try:
        service = TemplateService(db)
        result = await service.fork_template(template_id, current_user.id)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"Fork 模板失败: {e}")
        raise HTTPException(status_code=500, detail="Fork 模板失败")


# ========== 导出模板 ==========


@market.get("/{template_id}/export")
async def export_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """导出模板为 JSON"""
    try:
        service = TemplateService(db)
        result = await service.get_template_detail(template_id)
        if not result:
            raise HTTPException(status_code=404, detail="模板不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出模板失败: {e}")
        raise HTTPException(status_code=500, detail="导出模板失败")


# ========== 评论 ==========


@market.post("/{template_id}/comments")
async def add_comment(
    template_id: str,
    payload: CommentRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """评论模板"""
    try:
        service = TemplateService(db)
        result = await service.add_comment(current_user.id, template_id, payload.content)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"评论模板失败: {e}")
        raise HTTPException(status_code=500, detail="评论模板失败")


@market.get("/{template_id}/comments")
async def get_comments(
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取模板评论"""
    try:
        service = TemplateService(db)
        items = await service.get_comments(template_id)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取评论失败: {e}")
        raise HTTPException(status_code=500, detail="获取评论失败")


@market.delete("/{template_id}/comments/{comment_id}")
async def delete_comment(
    template_id: str,
    comment_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除评论"""
    try:
        service = TemplateService(db)
        await service.delete_comment(comment_id, current_user.id)
        return {"success": True}
    except Exception as e:
        logger.error(f"删除评论失败: {e}")
        raise HTTPException(status_code=500, detail="删除评论失败")
