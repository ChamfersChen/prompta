"""社区模块路由（提示词社区 + 收藏）"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user, get_superadmin_user
from src.services.community_service import CommunityService
from src.storage.postgres.models_business import User
from src.utils.logging_config import logger

community = APIRouter(prefix="/community", tags=["社区"])


def _raise_from_value_error(e: ValueError) -> None:
    message = str(e)
    status_code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=status_code, detail=message)


# ========== Pydantic 模型 ==========


class PublishPromptRequest(BaseModel):
    name: str = Field(..., description="模板名称")
    category: str = Field("writing", description="分类")
    description: str = Field("", description="模板描述")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    content: str = Field(..., description="提示词内容")
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
    is_official: bool | None = None
    file_tree: list[dict] | None = None


class RateRequest(BaseModel):
    template_id: str = Field(..., description="模板ID")
    rating: int = Field(..., ge=0, le=5, description="评分 1-5")


class FavoriteRequest(BaseModel):
    template_id: str = Field(..., description="模板ID")
    item_type: str = Field("prompt", description="类型: prompt")
    folder_path: str | None = Field(None, description="收藏夹路径")


class CommentRequest(BaseModel):
    content: str = Field(..., min_length=1, description="评论内容")


class RenameFavoriteFolderRequest(BaseModel):
    old_folder_path: str = Field(..., min_length=1, description="原收藏夹名称")
    new_folder_path: str = Field(..., min_length=1, description="新收藏夹名称")
    item_type: str = Field("prompt", description="类型: prompt")


class CreateFavoriteFolderRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, description="收藏夹名称")
    item_type: str = Field("prompt", description="类型: prompt")


class DeleteFavoriteFolderRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, description="收藏夹名称")
    item_type: str = Field("prompt", description="类型: prompt")


# ============================================================
# 提示词社区
# ============================================================


@community.get("/prompts")
async def list_prompt_templates(
    category: str | None = Query(None, description="分类筛选"),
    keyword: str | None = Query(None, description="搜索关键词"),
    sort: str = Query("latest", description="排序: popular/latest/rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取提示词社区列表"""
    try:
        service = CommunityService(db)
        department_id = current_user.department_id if current_user.department_id else None
        items, total = await service.list_prompt_templates(
            department_id=department_id,
            category=category,
            keyword=keyword,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        return {"list": items, "total": total}
    except Exception as e:
        logger.error(f"获取提示词社区列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取提示词社区列表失败")


# ============================================================
# 我的模板
# ============================================================


@community.get("/mine")
async def get_my_templates(
    community_type: str | None = Query(None, description="类型筛选: prompt"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的模板列表"""
    try:
        service = CommunityService(db)
        items = await service.get_my_templates(current_user.id, community_type=community_type)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取我的模板失败: {e}")
        raise HTTPException(status_code=500, detail="获取我的模板失败")


# ============================================================
# 发布提示词
# ============================================================


@community.post("/publish/prompt")
async def publish_prompt(
    payload: PublishPromptRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """发布提示词到社区"""
    try:
        service = CommunityService(db)
        is_official = payload.is_official
        if is_official and current_user.role != "superadmin":
            raise HTTPException(status_code=403, detail="仅超级管理员可发布官方模板")

        result = await service.publish_prompt(
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
            department_id=current_user.department_id,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"发布提示词失败: {e}")
        raise HTTPException(status_code=500, detail="发布提示词失败")


# ============================================================
# 收藏
# ============================================================


@community.get("/favorites")
async def get_favorites(
    item_type: str | None = Query(None, description="类型筛选: prompt"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的收藏"""
    try:
        service = CommunityService(db)
        items = await service.get_favorites(
            current_user.id,
            item_type=item_type,
            department_id=current_user.department_id,
        )
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取收藏失败: {e}")
        raise HTTPException(status_code=500, detail="获取收藏失败")


@community.get("/favorites/folders")
async def get_favorite_folders(
    item_type: str | None = Query(None, description="类型筛选: prompt"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取收藏夹列表"""
    try:
        service = CommunityService(db)
        folders = await service.get_favorite_folders(
            current_user.id,
            item_type=item_type,
            department_id=current_user.department_id,
        )
        return {"folders": folders}
    except Exception as e:
        logger.error(f"获取收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail="获取收藏夹失败")


@community.post("/favorites")
async def add_favorite(
    payload: FavoriteRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏模板（纯书签，不复制文件）"""
    try:
        service = CommunityService(db)
        result = await service.add_favorite(
            user_id=current_user.id,
            template_id=payload.template_id,
            item_type=payload.item_type,
            folder_path=payload.folder_path,
            department_id=current_user.department_id,
        )
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"收藏失败: {e}")
        raise HTTPException(status_code=500, detail="收藏失败")


@community.delete("/favorites/{template_id}")
async def remove_favorite(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏"""
    try:
        service = CommunityService(db)
        await service.remove_favorite(current_user.id, template_id, department_id=current_user.department_id)
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"取消收藏失败: {e}")
        raise HTTPException(status_code=500, detail="取消收藏失败")


@community.put("/favorites/folders/rename")
async def rename_favorite_folder(
    payload: RenameFavoriteFolderRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """重命名收藏夹"""
    try:
        service = CommunityService(db)
        updated = await service.rename_favorite_folder(
            user_id=current_user.id,
            old_folder_path=payload.old_folder_path,
            new_folder_path=payload.new_folder_path,
            item_type=payload.item_type,
            department_id=current_user.department_id,
        )
        return {"success": True, "updated": updated}
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"重命名收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail="重命名收藏夹失败")


@community.post("/favorites/folders")
async def create_favorite_folder(
    payload: CreateFavoriteFolderRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """创建收藏夹"""
    try:
        service = CommunityService(db)
        result = await service.create_favorite_folder(
            user_id=current_user.id,
            folder_name=payload.folder_name,
            item_type=payload.item_type,
            department_id=current_user.department_id,
        )
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"创建收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail="创建收藏夹失败")


@community.delete("/favorites/folders")
async def delete_favorite_folder(
    payload: DeleteFavoriteFolderRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除收藏夹（仅删除文件夹本身，不删除收藏项）"""
    try:
        service = CommunityService(db)
        removed_count = await service.delete_favorite_folder(
            user_id=current_user.id,
            folder_name=payload.folder_name,
            item_type=payload.item_type,
            department_id=current_user.department_id,
        )
        return {"success": removed_count > 0, "removed": removed_count}
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"删除收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail="删除收藏夹失败")


# ============================================================
# 评分
# ============================================================


@community.get("/rate/{template_id}")
async def get_my_rating(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的评分"""
    try:
        service = CommunityService(db)
        result = await service.get_user_rating(
            current_user.id,
            template_id,
            department_id=current_user.department_id,
        )
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"获取评分失败: {e}")
        raise HTTPException(status_code=500, detail="获取评分失败")


@community.post("/rate")
async def rate_template(
    payload: RateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """评分模板"""
    try:
        service = CommunityService(db)
        result = await service.rate_template(
            current_user.id,
            payload.template_id,
            payload.rating,
            department_id=current_user.department_id,
        )
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"评分失败: {e}")
        raise HTTPException(status_code=500, detail="评分失败")


# ============================================================
# 通用模板操作
# ============================================================


@community.get("/{template_id}")
async def get_template_detail(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    try:
        service = CommunityService(db)
        result = await service.get_template_detail(template_id, department_id=current_user.department_id)
        if not result:
            raise HTTPException(status_code=404, detail="模板不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取模板详情失败")


@community.put("/{template_id}")
async def update_template(
    template_id: str,
    payload: UpdateTemplateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """更新模板（仅创建者）"""
    try:
        service = CommunityService(db)
        update_data = payload.model_dump(exclude_unset=True)
        result = await service.update_template(template_id, current_user.id, **update_data)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        raise HTTPException(status_code=500, detail="更新模板失败")


@community.post("/{template_id}/unpublish")
async def unpublish_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """取消发布模板"""
    try:
        service = CommunityService(db)
        result = await service.update_template(template_id, current_user.id, is_public=False, is_official=False)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"取消发布失败: {e}")
        raise HTTPException(status_code=500, detail="取消发布失败")


@community.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除模板（仅创建者）"""
    try:
        service = CommunityService(db)
        await service.delete_template(template_id, current_user.id)
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        raise HTTPException(status_code=500, detail="删除模板失败")


@community.post("/{template_id}/fork")
async def fork_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """Fork 模板"""
    try:
        service = CommunityService(db)
        result = await service.fork_template(template_id, current_user.id, department_id=current_user.department_id)
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"Fork 模板失败: {e}")
        raise HTTPException(status_code=500, detail="Fork 模板失败")


@community.get("/{template_id}/export")
async def export_template(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """导出模板为 JSON"""
    try:
        service = CommunityService(db)
        result = await service.get_template_detail(template_id, department_id=current_user.department_id)
        if not result:
            raise HTTPException(status_code=404, detail="模板不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出模板失败: {e}")
        raise HTTPException(status_code=500, detail="导出模板失败")


@community.post("/{template_id}/comments")
async def add_comment(
    template_id: str,
    payload: CommentRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """评论模板"""
    try:
        service = CommunityService(db)
        result = await service.add_comment(
            current_user.id,
            template_id,
            payload.content,
            department_id=current_user.department_id,
        )
        return result
    except ValueError as e:
        _raise_from_value_error(e)
    except Exception as e:
        logger.error(f"评论失败: {e}")
        raise HTTPException(status_code=500, detail="评论失败")


@community.get("/{template_id}/comments")
async def get_comments(
    template_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取模板评论"""
    try:
        service = CommunityService(db)
        items = await service.get_comments(template_id, department_id=current_user.department_id)
        return {"list": items, "total": len(items)}
    except Exception as e:
        logger.error(f"获取评论失败: {e}")
        raise HTTPException(status_code=500, detail="获取评论失败")


@community.delete("/{template_id}/comments/{comment_id}")
async def delete_comment(
    template_id: str,
    comment_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除评论"""
    try:
        service = CommunityService(db)
        await service.delete_comment(comment_id, current_user.id)
        return {"success": True}
    except Exception as e:
        logger.error(f"删除评论失败: {e}")
        raise HTTPException(status_code=500, detail="删除评论失败")


# ============================================================
# 导入（保留兼容）
# ============================================================


@community.post("/import")
async def import_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """导入模板（JSON 文件）"""
    try:
        content = await file.read()
        data = json.loads(content)

        service = CommunityService(db)
        result = await service.publish_prompt(
            name=data.get("name", "导入的模板"),
            category=data.get("category", "writing"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            content=data.get("content", ""),
            variables=data.get("variables", []),
            is_public=False,
            source_path=data.get("source_path"),
            owner_id=current_user.id,
            department_id=current_user.department_id,
        )
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")
    except Exception as e:
        logger.error(f"导入模板失败: {e}")
        raise HTTPException(status_code=500, detail="导入模板失败")
