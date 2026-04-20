"""Prompts 管理路由"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src import config as app_config
from src.models.chat import select_model, split_model_spec
from src.utils import format_prompt
from server.utils.auth_middleware import get_admin_user, get_db, get_superadmin_user, get_required_user
from server.utils.auth_middleware import get_current_user
from src.services.prompt_service import (
    create_prompt_node,
    delete_prompt_file,
    get_prompt_tree,
    read_prompt_file,
    rename_prompt_node,
    update_prompt_file,
)
from src.repositories.prompt_repository import PromptRepository
from src.storage.postgres.models_business import User
from src.utils.logging_config import logger

prompts = APIRouter(prefix="/system/prompts", tags=["提示词管理"])


class PromptNodeCreateRequest(BaseModel):
    path: str = Field(..., description="相对 prompt 根目录的路径")
    is_dir: bool = Field(False, description="是否创建目录")
    content: str | None = Field("", description="文件内容（仅文件创建时生效）")


class PromptFileUpdateRequest(BaseModel):
    path: str = Field(..., description="相对 prompt 根目录的路径")
    content: str = Field(..., description="文件内容")


class PromptNodeRenameRequest(BaseModel):
    old_path: str = Field(..., description="原始相对路径")
    new_path: str = Field(..., description="目标相对路径")


class PromptTestRequest(BaseModel):
    path: str | None = Field(default=None, description="提示词文件路径（可选）")
    content: str = Field(..., description="待测试提示词内容")
    variables: dict[str, str] = Field(default_factory=dict, description="变量赋值")
    model_spec: str | None = Field(default=None, description="模型规格 provider/model")


def _raise_from_value_error(e: ValueError) -> None:
    message = str(e)
    status_code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=status_code, detail=message)


def _check_prompt_access(item, current_user: User) -> bool:
    """检查用户是否有权限访问该prompt"""
    return item.created_by == current_user.username


def _extract_prompt_variables(content: str) -> list[str]:
    found: set[str] = set()
    for match in re.finditer(r"\{\{([^}]+)\}\}", content or ""):
        name = match.group(1).strip()
        if name:
            found.add(name)
    return sorted(found)


def _build_prompt_test_capability() -> dict:
    model_names = {}
    status_map = getattr(app_config, "model_provider_status", {}) or {}

    for provider, info in (getattr(app_config, "model_names", {}) or {}).items():
        model_names[provider] = {
            "name": info.name,
            "base_url": info.base_url,
            "models": list(info.models or []),
            "enabled": bool(status_map.get(provider, False)),
        }

    default_model = getattr(app_config, "default_model", "") or ""
    default_provider, default_model_name = split_model_spec(default_model)
    issues = []
    available_models = []

    for provider, info in model_names.items():
        if not info.get("enabled"):
            continue
        if not (info.get("base_url") or "").strip():
            continue
        for model_name in info.get("models") or []:
            available_models.append(f"{provider}/{model_name}")

    if not available_models:
        issues.append("当前没有可用模型，请在系统设置中启用提供方并配置 base_url")

    default_issues = []
    if not default_provider or not default_model_name:
        default_issues.append("系统默认模型未配置，请在系统设置中设置 default_model")
    elif default_provider not in model_names:
        default_issues.append(f"默认模型提供方不存在: {default_provider}")
    else:
        default_provider_info = model_names[default_provider]
        if not default_provider_info.get("enabled"):
            default_issues.append(f"默认模型提供方未就绪: {default_provider}")
        if not (default_provider_info.get("base_url") or "").strip():
            default_issues.append(f"默认模型提供方未配置 base_url: {default_provider}")
        if default_model_name not in (default_provider_info.get("models") or []):
            default_issues.append(f"默认模型不存在于提供方列表: {default_model}")

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "default_model": default_model,
        "default_ready": len(default_issues) == 0,
        "default_issues": default_issues,
        "available_models": available_models,
        "model_provider_status": status_map,
        "model_names": model_names,
    }


@prompts.get("/tree")
async def get_prompt_tree_route(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的提示词目录树。"""
    try:
        tree = await get_prompt_tree(db, username=current_user.username)
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
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """读取当前用户的提示词文件。"""
    try:
        repo = PromptRepository(db)
        item = await repo.get_by_name_path(current_user.username, path)
        if not item or not _check_prompt_access(item, current_user):
            raise HTTPException(status_code=404, detail="文件不存在")
        data = await read_prompt_file(db, current_user.username, path)
        return {"success": True, "data": {"path": path, "content": data.get("content", "")}}
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
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """创建提示词文件或目录。"""
    try:
        await create_prompt_node(
            db,
            path=payload.path,
            is_dir=payload.is_dir,
            content=payload.content,
            updated_by=current_user.username,
            username=current_user.username,
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
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """更新提示词文本文件。"""
    try:
        # user_path = _get_user_path(payload.path, current_user)
        repo = PromptRepository(db)
        item = await repo.get_by_name_path(current_user.username, payload.path)
        if not item or not _check_prompt_access(item, current_user):
            raise HTTPException(status_code=404, detail="文件不存在")
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
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除提示词文件或目录。"""
    try:
        repo = PromptRepository(db)
        item = await repo.get_by_name_path(current_user.username, path)
        if not item or not _check_prompt_access(item, current_user):
            raise HTTPException(status_code=404, detail="文件不存在")
        await delete_prompt_file(db, name=current_user.username, path=path)
        return {"success": True}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete prompt file '{path}': {e}")
        raise HTTPException(status_code=500, detail="删除技能文件失败")


@prompts.put("/rename")
async def rename_prompt_node_route(
    payload: PromptNodeRenameRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """重命名提示词文件或目录。"""
    try:
        repo = PromptRepository(db)
        source_item = await repo.get_by_name_path(current_user.username, payload.old_path)
        if not source_item or not _check_prompt_access(source_item, current_user):
            raise HTTPException(status_code=404, detail="源节点不存在")

        target_item = await repo.get_by_name_path(current_user.username, payload.new_path)
        if target_item:
            raise HTTPException(status_code=400, detail="目标已存在")

        changed_paths = await rename_prompt_node(
            db,
            username=current_user.username,
            old_path=payload.old_path,
            new_path=payload.new_path,
            updated_by=current_user.username,
        )
        return {"success": True, "data": {"paths": changed_paths}}
    except ValueError as e:
        _raise_from_value_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename prompt node '{payload.old_path}' -> '{payload.new_path}': {e}")
        raise HTTPException(status_code=500, detail="重命名技能文件失败")


@prompts.get("/test-capability")
async def get_prompt_test_capability_route(current_user: User = Depends(get_required_user)):
    """获取提示词测试能力（模型配置就绪状态）。"""
    _ = current_user
    return {"success": True, "data": _build_prompt_test_capability()}


@prompts.post("/test")
async def test_prompt_route(
    payload: PromptTestRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """测试提示词：变量替换 + 模型推理。"""
    try:
        path = (payload.path or "").strip()
        if path:
            repo = PromptRepository(db)
            item = await repo.get_by_name_path(current_user.username, path)
            if not item or not _check_prompt_access(item, current_user):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

        content = (payload.content or "").strip()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="提示词内容不能为空")

        required_variables = _extract_prompt_variables(content)
        variables = payload.variables or {}
        missing_variables = [name for name in required_variables if not str(variables.get(name, "")).strip()]
        if missing_variables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "存在未赋值变量",
                    "missing_variables": missing_variables,
                },
            )

        capability = _build_prompt_test_capability()
        resolved_model_spec = (payload.model_spec or capability["default_model"] or "").strip()
        if not resolved_model_spec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先选择测试模型，或在系统设置中配置 default_model",
            )

        provider, model_name = split_model_spec(resolved_model_spec)
        if not provider or not model_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型参数无效")

        provider_info = capability["model_names"].get(provider)
        if not provider_info:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知模型提供方: {provider}")
        if model_name not in (provider_info.get("models") or []):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"模型不存在: {resolved_model_spec}")
        if not provider_info.get("enabled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"模型提供方未就绪: {provider}")
        if not (provider_info.get("base_url") or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"模型提供方未配置 base_url: {provider}"
            )

        slots = {name: str(variables.get(name, "")) for name in required_variables}
        rendered_prompt = format_prompt(content, slots)

        model = select_model(model_spec=resolved_model_spec)
        response = await model.call([{"role": "user", "content": rendered_prompt}], stream=False)
        response_text = getattr(response, "content", None)
        if response_text is None:
            response_text = str(response)

        return {
            "success": True,
            "data": {
                "model_spec": resolved_model_spec,
                "rendered_prompt": rendered_prompt,
                "response": response_text,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test prompt for '{current_user.username}' path='{payload.path}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="测试提示词失败")
