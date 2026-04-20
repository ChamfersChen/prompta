from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import (
    get_admin_user,
    get_db,
    get_valid_api_key_header_only,
)
from src.repositories.api_key_repository import APIKeyRepository
from src.repositories.prompt_repository import PromptRepository
from src.services.api_key_service import can_access_prompt_by_scope, create_api_key
from src.storage.postgres.models_business import APIKey, User
from src.utils.logging_config import logger

api_keys = APIRouter(prefix="/system/api-keys", tags=["API Key 管理"])
open_prompts = APIRouter(prefix="/open/prompts", tags=["开放提示词 API"])


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    user_id: int | None = None
    department_id: int | None = None
    expires_at: str | None = None
    is_enabled: bool = True


class APIKeyEnabledRequest(BaseModel):
    is_enabled: bool


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == 0))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


async def _is_api_key_visible_to_admin(db: AsyncSession, current_user: User, item: APIKey) -> bool:
    if current_user.role == "superadmin":
        return True

    if item.department_id is not None:
        return item.department_id == current_user.department_id

    if item.user_id is not None:
        result = await db.execute(select(User).where(User.id == item.user_id, User.is_deleted == 0))
        owner = result.scalar_one_or_none()
        if owner is None:
            return False
        return owner.department_id == current_user.department_id

    # 全局 API Key 仅 superadmin 可见
    return False


async def _ensure_api_key_manage_permission(db: AsyncSession, current_user: User, item: APIKey) -> None:
    allowed = await _is_api_key_visible_to_admin(db, current_user, item)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限操作该 API Key")


@api_keys.get("")
async def list_api_keys(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    repo = APIKeyRepository(db)
    items = await repo.list_all()

    if current_user.role == "superadmin":
        data = [item.to_dict() for item in items]
        return {"success": True, "data": data}

    data = []
    for item in items:
        if await _is_api_key_visible_to_admin(db, current_user, item):
            data.append(item.to_dict())
    return {"success": True, "data": data}


@api_keys.post("")
async def create_api_key_route(
    payload: APIKeyCreateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    scoped_user_id = payload.user_id
    scoped_department_id = payload.department_id

    owner_user: User | None = None
    if scoped_user_id is not None:
        owner_user = await _get_user_or_404(db, scoped_user_id)

    if current_user.role != "superadmin":
        if scoped_department_id is not None and scoped_department_id != current_user.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能为其他部门创建 API Key")

        if owner_user is not None and owner_user.department_id != current_user.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能为其他部门用户创建 API Key")

        if scoped_user_id is None and scoped_department_id is None:
            scoped_department_id = current_user.department_id

    if owner_user is not None and scoped_department_id is not None and owner_user.department_id != scoped_department_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户与部门不匹配")

    try:
        created = await create_api_key(
            db,
            name=payload.name.strip(),
            user_id=scoped_user_id,
            department_id=scoped_department_id,
            expires_at=payload.expires_at,
            is_enabled=payload.is_enabled,
            created_by=current_user.username,
        )
        return {
            "success": True,
            "data": {
                **created.record.to_dict(),
                "plain_key": created.plain_key,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create api key: {e}")
        raise HTTPException(status_code=500, detail="创建 API Key 失败")


@api_keys.put("/{key_id}/enabled")
async def update_api_key_enabled(
    key_id: int,
    payload: APIKeyEnabledRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    repo = APIKeyRepository(db)
    item = await repo.get_by_id(key_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")

    await _ensure_api_key_manage_permission(db, current_user, item)

    updated = await repo.set_enabled(item, payload.is_enabled)
    return {"success": True, "data": updated.to_dict()}


@api_keys.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    repo = APIKeyRepository(db)
    item = await repo.get_by_id(key_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")

    await _ensure_api_key_manage_permission(db, current_user, item)

    await repo.delete(item)
    return {"success": True}


@open_prompts.get("/{external_id}")
async def get_open_prompt_file(
    external_id: str,
    include_path: bool = Query(default=False),
    api_key: APIKey = Depends(get_valid_api_key_header_only),
    db: AsyncSession = Depends(get_db),
):
    prompt_repo = PromptRepository(db)
    item = await prompt_repo.get_by_external_id(external_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提示词不存在")

    allowed = await can_access_prompt_by_scope(db, api_key, item)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key 无权限访问该提示词")

    data = {
        "external_id": item.external_id,
        "name": item.name,
        "content": item.description or "",
    }
    if include_path:
        data["path"] = item.path
    return {"success": True, "data": data}
