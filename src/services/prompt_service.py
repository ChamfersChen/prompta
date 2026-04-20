from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src import config as sys_config
from src.repositories.prompt_repository import PromptRepository
from src.utils.datetime_utils import utc_now_naive
from src.storage.postgres.models_business import Prompt

PROMPT_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def is_valid_prompt_slug(slug: str) -> bool:
    if not isinstance(slug, str):
        return False
    return bool(PROMPT_SLUG_PATTERN.match(slug.strip()))


def get_prompts_root_dir(username: str | None = None) -> Path:
    if username:
        root = Path(sys_config.save_dir) / "prompts" / username
    else:
        root = Path(sys_config.save_dir) / "prompts"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def get_prompt_or_raise(db: AsyncSession, id: int) -> Prompt:
    repo = PromptRepository(db)
    item = await repo.get_by_id(id)
    if not item:
        raise ValueError(f"提示词不存在")
    return item


def _resolve_prompt_dir(item: Prompt) -> Path:
    dir_path = Path(item.dir_path)
    if dir_path.is_absolute():
        return dir_path
    return (Path(sys_config.save_dir) / dir_path).resolve()


def _resolve_relative_path_without_dir(relative_path: str, *, allow_root: bool = False) -> tuple[Path, str]:
    rel = (relative_path or "").strip().replace("\\", "/")
    rel = rel.lstrip("/")
    if not rel and not allow_root:
        raise ValueError("path 不能为空")
    pure = PurePosixPath(rel) if rel else PurePosixPath(".")
    if ".." in pure.parts:
        raise ValueError("非法路径：不允许上级路径引用")

    target = (Path("") / pure).resolve()
    return target, rel


async def get_prompt_tree(db: AsyncSession, username: str | None = None) -> list[dict[str, Any]]:
    def _build_node(record: Prompt):
        """根据单条记录，构建从根到该节点的完整路径树。"""
        is_dir = bool(record.is_dir)
        target_path = record.path
        target_name = record.name

        parts = target_path.split("/")

        node = {
            "name": target_name,
            "path": target_path,
            "is_dir": is_dir,
            **({"external_id": record.external_id} if not is_dir else {}),
            **({"children": []} if is_dir else {}),
        }

        for i in range(len(parts) - 2, -1, -1):
            parent_path = "/".join(parts[: i + 1])
            parent_name = parts[i]
            node = {
                "name": parent_name,
                "path": parent_path,
                "is_dir": True,
                "children": [node],
            }

        return node

    def _merge_node(target: list, node: dict):
        """将 node 合并进 target 列表中，相同 path 的目录节点递归合并 children。"""
        for existing in target:
            if existing["path"] == node["path"] and existing["is_dir"] and node["is_dir"]:
                for child in node.get("children", []):
                    _merge_node(existing["children"], child)
                return
        target.append(node)

    def _merge_forest(nodes: list) -> list:
        """将多棵独立的树合并为一棵去重后的森林。"""
        forest = []
        for node in nodes:
            _merge_node(forest, node)
        return forest

    repo = PromptRepository(db)
    if username:
        raw_records: list[Prompt] = await repo.list_by_user(username)
    else:
        raw_records = await repo.list_all()
    result = [_build_node(r) for r in raw_records]
    result = _merge_forest(result)
    return result


async def read_prompt_file(db: AsyncSession, name: str, path: str) -> dict[str, Any]:
    repo = PromptRepository(db)
    item = await repo.get_by_name_path(name, path)
    if not item:
        raise ValueError(f"文件不存在: {path}")
    try:
        content = item.description or ""
    except UnicodeDecodeError as e:
        raise ValueError(f"文件编码不支持（仅支持 UTF-8）: {e}") from e
    return {"path": path, "content": content}


async def create_prompt_node(
    db: AsyncSession,
    *,
    path: str,
    is_dir: bool,
    content: str | None,
    updated_by: str | None,
    username: str | None = None,
) -> Prompt:
    repo = PromptRepository(db)

    if not is_dir:
        list_path = path.split("/")
        item = await repo.create(
            name=list_path[-1],
            path=path,
            description=content or "",
            dir_path="/".join(path.split("/")[:-1]) if len(path.split("/")) > 1 else path.rstrip("/"),
            is_dir=is_dir,
            created_by=updated_by,
        )
    else:
        item = await repo.create(
            name=os.path.basename(path),
            path=path,
            description="",
            dir_path=path,
            is_dir=is_dir,
            created_by=updated_by,
        )
    return item


async def update_prompt_file(
    db: AsyncSession,
    *,
    path: str,
    content: str,
    updated_by: str | None,
) -> None:
    repo = PromptRepository(db)
    item = await repo.update(path, content, updated_by)


def _normalize_prompt_path(path: str) -> str:
    rel = (path or "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        raise ValueError("path 不能为空")

    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or rel in {".", ""}:
        raise ValueError("非法路径")

    return pure.as_posix()


def _build_prompt_dir_path(path: str, is_dir: bool) -> str:
    if is_dir:
        return path
    parts = path.split("/")
    return "/".join(parts[:-1]) if len(parts) > 1 else path


def _replace_prefix(path: str, old_prefix: str, new_prefix: str) -> str:
    if path == old_prefix:
        return new_prefix
    return f"{new_prefix}{path[len(old_prefix) :]}"


async def rename_prompt_node(
    db: AsyncSession,
    *,
    username: str,
    old_path: str,
    new_path: str,
    updated_by: str | None,
) -> list[str]:
    repo = PromptRepository(db)

    src_path = _normalize_prompt_path(old_path)
    dst_path = _normalize_prompt_path(new_path)
    if src_path == dst_path:
        return [src_path]

    source_item = await repo.get_by_name_path(username, src_path)
    if not source_item:
        raise ValueError("源节点不存在")

    existed = await repo.get_by_name_path(username, dst_path)
    if existed:
        raise ValueError("目标已存在")

    if bool(source_item.is_dir) and dst_path.startswith(f"{src_path}/"):
        raise ValueError("目录不能重命名到自身子目录")

    now = utc_now_naive()
    changed_paths: list[str] = []

    if not bool(source_item.is_dir):
        source_item.path = dst_path
        source_item.name = PurePosixPath(dst_path).name
        source_item.dir_path = _build_prompt_dir_path(dst_path, False)
        source_item.updated_by = updated_by
        source_item.updated_at = now
        changed_paths.append(dst_path)
        await db.commit()
        return changed_paths

    affected_items = await repo.list_by_path_prefix(username, src_path)
    for item in affected_items:
        next_path = _replace_prefix(item.path, src_path, dst_path)
        item.path = next_path
        item.name = PurePosixPath(next_path).name
        item.dir_path = _build_prompt_dir_path(next_path, bool(item.is_dir))
        item.updated_by = updated_by
        item.updated_at = now
        changed_paths.append(next_path)

    await db.commit()
    return changed_paths


async def delete_prompt_file(
    db: AsyncSession,
    *,
    name: str,
    path: str,
) -> list[str]:
    """删除提示词文件或文件夹。如果是文件夹，同时删除所有子文件。返回被删除的文件路径列表。"""
    repo = PromptRepository(db)
    item = await repo.get_by_name_path(name, path)
    if not item:
        return []

    if item.is_dir:
        deleted_paths = await repo.delete_by_path_prefix(name, path)
        return deleted_paths
    else:
        await repo.delete(item)
        return [path]
