"""Prompts 管理路由"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_admin_user, get_db, get_superadmin_user, get_required_user
from src.services.prompt_service import (
    create_prompt_node,
    delete_prompt_file,
    get_prompt_tree,
    read_prompt_file,
    update_prompt_file
)
from src.storage.postgres.models_business import User
from src.utils.logging_config import logger

prompts = APIRouter(prefix="/system/prompts", tags=["prompts"])


class PromptNodeCreateRequest(BaseModel):
    path: str = Field(..., description="相对 prompt 根目录的路径")
    is_dir: bool = Field(False, description="是否创建目录")
    content: str | None = Field("", description="文件内容（仅文件创建时生效）")


class PromptFileUpdateRequest(BaseModel):
    path: str = Field(..., description="相对 prompt 根目录的路径")
    content: str = Field(..., description="文件内容")


def _raise_from_value_error(e: ValueError) -> None:
    message = str(e)
    status_code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=status_code, detail=message)

@prompts.get("/tree")
async def get_prompt_tree_route(
    _current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取技能目录树（仅超级管理员）。"""
    try:
        tree = await get_prompt_tree(db)
        return {"success": True, "data": tree}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt tree {e}")
        raise HTTPException(status_code=500, detail="获取技能目录树失败")


@prompts.get("/file")
async def get_prompt_file_route(
    path: str = Query(..., description="相对 prompt 根目录路径"),
    _current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """读取技能文本文件（仅超级管理员）。"""
    try:
        data = await read_prompt_file(db, path)
        return {"success": True, "data": data}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read prompt file '{path}': {e}")
        raise HTTPException(status_code=500, detail="读取技能文件失败")

@prompts.post("/file")
async def create_prompt_file_route(
    payload: PromptNodeCreateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """创建技能文件或目录（仅超级管理员）。"""
    try:
        await create_prompt_node(
            db,
            path=payload.path,
            is_dir=payload.is_dir,
            content=payload.content,
            updated_by=current_user.username,
        )
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create prompt node '{payload.path}': {e}")
        raise HTTPException(status_code=500, detail="创建技能文件失败")

@prompts.put("/file")
async def update_prompt_file_route(
    payload: PromptFileUpdateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新技能文本文件（仅超级管理员）。"""
    try:
        await update_prompt_file(
            db,
            path=payload.path,
            content=payload.content,
            updated_by=current_user.username,
        )
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update prompt file '{payload.path}': {e}")
        raise HTTPException(status_code=500, detail="更新技能文件失败")



@prompts.delete("/file")
async def delete_prompt_file_route(
    path: str = Query(..., description="相对 prompt 根目录路径"),
    _current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除技能文件或目录（仅超级管理员）。"""
    try:
        await delete_prompt_file(db, path=path)
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete prompt file '{path}': {e}")
        raise HTTPException(status_code=500, detail="删除技能文件失败")
