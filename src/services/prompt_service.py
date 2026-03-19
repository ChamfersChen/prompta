from __future__ import annotations

import os
import asyncio
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import FilePath
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from src import config as sys_config
from src.repositories.prompt_repository import PromptRepository
# from src.repositories.skill_repository import SkillRepository
from src.storage.postgres.models_business import Prompt

PROMPT_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_PATTERN = PROMPT_SLUG_PATTERN
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

TEXT_FILE_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".html",
    ".css",
    ".sql",
    ".sh",
    ".bat",
    ".ps1",
    ".env",
    ".csv",
    ".tsv",
    ".rst",
    ".ipynb",
    ".vue",
    ".jsx",
    ".tsx",
}


def _normalize_string_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def is_valid_prompt_slug(slug: str) -> bool:
    if not isinstance(slug, str):
        return False
    return bool(PROMPT_SLUG_PATTERN.match(slug.strip()))


def get_skills_root_dir() -> Path:
    root = Path(sys_config.save_dir) / "skills"
    root.mkdir(parents=True, exist_ok=True)
    return root

def get_prompts_root_dir() -> Path:
    root = Path(sys_config.save_dir) / "prompts"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def get_skill_dependency_options(db: AsyncSession) -> dict[str, list[str] | list[dict]]:
    # 并行执行三个独立操作
    from src.services.tool_service import get_tool_metadata

    async def get_skills():
        repo = SkillRepository(db)
        return await repo.list_all()

    def get_tools():
        all_tools = get_tool_metadata()
        return [{"id": tool["id"], "name": tool.get("name", tool["id"])} for tool in all_tools]

    # items, tool_list, mcp_names = await asyncio.gather(
    #     get_skills(),
    #     asyncio.to_thread(get_tools),
    #     asyncio.to_thread(get_mcp_server_names),
    # )
    items, tool_list = await asyncio.gather(
        get_skills(),
        asyncio.to_thread(get_tools),
    )

    return {
        "tools": tool_list,
        "skills": [item.slug for item in items],
    }


async def list_skills(db: AsyncSession) -> list[Prompt]:
    repo = SkillRepository(db)
    return await repo.list_all()


def _get_all_tool_names() -> list[str]:
    """获取所有工具名称（包括 buildin 和其他来源）"""
    from src.services.tool_service import get_tool_metadata

    all_tools = get_tool_metadata()
    return [tool["id"] for tool in all_tools]


def _validate_dependencies(
    *,
    slug: str,
    tool_dependencies: list[str],
    mcp_dependencies: list[str],
    skill_dependencies: list[str],
    available_skill_slugs: set[str],
) -> tuple[list[str], list[str], list[str]]:
    tools = _normalize_string_list(tool_dependencies)
    mcps = _normalize_string_list(mcp_dependencies)
    skills = _normalize_string_list(skill_dependencies)

    # 验证所有工具（不仅仅是 buildin）
    available_tools = set(_get_all_tool_names())
    invalid_tools = [name for name in tools if name not in available_tools]
    if invalid_tools:
        raise ValueError(f"存在无效工具依赖: {', '.join(invalid_tools)}")

    available_mcps = set(get_mcp_server_names())
    invalid_mcps = [name for name in mcps if name not in available_mcps]
    if invalid_mcps:
        raise ValueError(f"存在无效 MCP 依赖: {', '.join(invalid_mcps)}")

    invalid_skills = [name for name in skills if name not in available_skill_slugs]
    if invalid_skills:
        raise ValueError(f"存在无效 skill 依赖: {', '.join(invalid_skills)}")

    if slug in skills:
        raise ValueError("skill_dependencies 不允许包含自身")

    return tools, mcps, skills


async def update_skill_dependencies(
    db: AsyncSession,
    *,
    slug: str,
    tool_dependencies: list[str],
    mcp_dependencies: list[str],
    skill_dependencies: list[str],
    updated_by: str | None,
) -> Prompt:
    item = await get_skill_or_raise(db, slug)
    repo = SkillRepository(db)
    skill_items = await repo.list_all()
    available_skill_slugs = {skill.slug for skill in skill_items}
    tools, mcps, skills = _validate_dependencies(
        slug=slug,
        tool_dependencies=tool_dependencies,
        mcp_dependencies=mcp_dependencies,
        skill_dependencies=skill_dependencies,
        available_skill_slugs=available_skill_slugs,
    )

    return await repo.update_dependencies(
        item,
        tool_dependencies=tools,
        mcp_dependencies=mcps,
        skill_dependencies=skills,
        updated_by=updated_by,
    )


def _validate_skill_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("SKILL.md frontmatter 缺少 name")
    if len(name) > 128:
        raise ValueError("skill name 长度不能超过 128")
    if not SKILL_NAME_PATTERN.match(name):
        raise ValueError("skill name 必须是小写字母/数字/短横线，且不能连续短横线")
    return name


def _parse_skill_markdown(content: str) -> tuple[str, str, dict[str, Any]]:
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise ValueError("SKILL.md 缺少有效 frontmatter（--- ... ---）")

    frontmatter_raw = match.group(1)
    try:
        data = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError as e:
        raise ValueError(f"SKILL.md frontmatter YAML 解析失败: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter 必须是对象")

    name = _validate_skill_name(str(data.get("name", "")))
    description = str(data.get("description", "")).strip()
    if not description:
        raise ValueError("SKILL.md frontmatter 缺少 description")

    return name, description, data


def _rewrite_frontmatter_name(content: str, new_name: str) -> str:
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise ValueError("SKILL.md 缺少有效 frontmatter（--- ... ---）")

    frontmatter_raw = match.group(1)
    body = content[match.end() :]
    data = yaml.safe_load(frontmatter_raw)
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter 必须是对象")
    data["name"] = new_name
    dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{dumped}\n---\n{body}"


def _validate_zip_paths(zip_file: zipfile.ZipFile) -> None:
    for name in zip_file.namelist():
        pure = PurePosixPath(name)
        if pure.is_absolute():
            raise ValueError(f"ZIP 包含不安全绝对路径: {name}")
        if ".." in pure.parts:
            raise ValueError(f"ZIP 包含路径穿越片段: {name}")


async def _generate_available_slug(repo: SkillRepository, base_slug: str) -> str:
    root = get_skills_root_dir()
    if not await repo.exists_slug(base_slug) and not (root / base_slug).exists():
        return base_slug

    idx = 2
    while True:
        candidate = f"{base_slug}-v{idx}"
        if not await repo.exists_slug(candidate) and not (root / candidate).exists():
            return candidate
        idx += 1


def _resolve_prompt_dir(item: Prompt) -> Path:
    dir_path = Path(item.dir_path)
    if dir_path.is_absolute():
        return dir_path
    return (Path(sys_config.save_dir) / dir_path).resolve()


def _resolve_relative_path(skill_dir: Path, relative_path: str, *, allow_root: bool = False) -> tuple[Path, str]:
    rel = (relative_path or "").strip().replace("\\", "/")
    rel = rel.lstrip("/")
    if not rel and not allow_root:
        raise ValueError("path 不能为空")
    pure = PurePosixPath(rel) if rel else PurePosixPath(".")
    if ".." in pure.parts:
        raise ValueError("非法路径：不允许上级路径引用")

    target = (skill_dir / pure).resolve()
    try:
        target.relative_to(skill_dir)
    except ValueError:
        raise ValueError("非法路径：越界访问被拒绝") from None

    return target, rel

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

def _is_text_path(path: Path) -> bool:
    if path.name == "SKILL.md":
        return True
    suffix = path.suffix.lower()
    return suffix in TEXT_FILE_EXTENSIONS


def _build_tree(path: Path, base_dir: Path) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        rel = child.relative_to(base_dir).as_posix()
        if child.is_dir():
            children.append(
                {
                    "name": child.name,
                    "path": rel,
                    "is_dir": True,
                    "children": _build_tree(child, base_dir),
                }
            )
        else:
            children.append(
                {
                    "name": child.name,
                    "path": rel,
                    "is_dir": False,
                }
            )
    return children


async def import_skill_zip(
    db: AsyncSession,
    *,
    filename: str,
    file_bytes: bytes,
    created_by: str | None,
) -> Prompt:
    if not filename.lower().endswith(".zip"):
        raise ValueError("仅支持上传 .zip 文件")

    repo = SkillRepository(db)
    skills_root = get_skills_root_dir()

    with tempfile.TemporaryDirectory(prefix=".skill-import-", dir=str(skills_root.parent)) as temp_root:
        temp_root_path = Path(temp_root)
        zip_path = temp_root_path / "upload.zip"
        extract_dir = temp_root_path / "extract"
        stage_dir = temp_root_path / "stage"
        extract_dir.mkdir(parents=True, exist_ok=True)

        zip_path.write_bytes(file_bytes)

        with zipfile.ZipFile(zip_path, "r") as zf:
            _validate_zip_paths(zf)
            zf.extractall(extract_dir)

        skill_md_files = list(extract_dir.rglob("SKILL.md"))
        if len(skill_md_files) != 1:
            raise ValueError("ZIP 必须且只能包含一个技能（检测到一个 SKILL.md）")

        skill_md_path = skill_md_files[0]
        source_skill_dir = skill_md_path.parent
        content = skill_md_path.read_text(encoding="utf-8")
        parsed_name, parsed_desc, _ = _parse_skill_markdown(content)

        final_slug = await _generate_available_slug(repo, parsed_name)
        final_name = parsed_name
        if final_slug != parsed_name:
            final_name = final_slug
            content = _rewrite_frontmatter_name(content, final_name)
            skill_md_path.write_text(content, encoding="utf-8")

        shutil.copytree(source_skill_dir, stage_dir)

        temp_target = skills_root / f".{final_slug}.tmp-{uuid.uuid4().hex[:8]}"
        if temp_target.exists():
            shutil.rmtree(temp_target)
        shutil.move(str(stage_dir), str(temp_target))

        final_dir = skills_root / final_slug
        if final_dir.exists():
            shutil.rmtree(temp_target, ignore_errors=True)
            raise ValueError(f"技能目录冲突，请重试: {final_slug}")
        temp_target.rename(final_dir)

        try:
            item = await repo.create(
                slug=final_slug,
                name=final_name,
                description=parsed_desc,
                tool_dependencies=[],
                mcp_dependencies=[],
                skill_dependencies=[],
                dir_path=(Path("skills") / final_slug).as_posix(),
                created_by=created_by,
            )
        except Exception:
            shutil.rmtree(final_dir, ignore_errors=True)
            raise

    return item


async def get_prompt_or_raise(db: AsyncSession, id:int) -> Prompt:
    repo = PromptRepository(db)
    item = await repo.get_by_id(id)
    if not item:
        raise ValueError(f"提示词不存在")
    return item


async def get_skill_tree(db: AsyncSession, slug: str) -> list[dict[str, Any]]:
    item = await get_prompt_or_raise(db, slug)
    skill_dir = _resolve_prompt_dir(item)
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise ValueError(f"技能目录不存在: {item.dir_path}")
    return _build_tree(skill_dir, skill_dir)

async def get_prompt_tree(db: AsyncSession) -> list[dict[str, Any]]:
    def _build_node(record:Prompt):
        """根据单条记录，构建从根到该节点的完整路径树。"""
        is_dir = bool(record.is_dir)
        target_path = record.path
        target_name = record.name
    
        # 拆分路径各段，例如 "src/test/test.py" -> ["src", "test", "test.py"]
        parts = target_path.split("/")
    
        # 从最深层节点开始，由内向外逐层包裹
        node = {
            "name": target_name,
            "path": target_path,
            "is_dir": is_dir,
            **({"children": []} if is_dir else {}),
        }
    
        # 逐层向上构建父目录节点（倒数第二段开始）
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
                # 同路径目录已存在，递归合并其子节点
                for child in node.get("children", []):
                    _merge_node(existing["children"], child)
                return
        # 没有找到同路径节点，直接追加
        target.append(node)
    
    
    def _merge_forest(nodes: list) -> list:
        """将多棵独立的树合并为一棵去重后的森林。"""
        forest = []
        for node in nodes:
            _merge_node(forest, node)
        return forest
    
    # 获取所有的prompt记录
    raw_records:list[Prompt] = await PromptRepository(db).list_all()
    result = [_build_node(r) for r in raw_records]
    result = _merge_forest(result)
    return result 

async def read_prompt_file(db: AsyncSession, path: str) -> dict[str, Any]:
    repo = PromptRepository(db)
    item = await repo.get_by_path(path)
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
) -> Prompt:
    repo = PromptRepository(db)
    if not is_dir:
        list_path = path.split("/")
        item = await repo.create(
            name=list_path[-1],
            path=path,
            description=content or "",
            dir_path="/".join(list_path[:-1]) if len(list_path) > 1 else "",
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

async def create_skill_node(
    db: AsyncSession,
    *,
    slug: str,
    relative_path: str,
    is_dir: bool,
    content: str | None,
    updated_by: str | None,
) -> None:
    item = await get_skill_or_raise(db, slug)
    skill_dir = _resolve_prompt_dir(item)
    target, _ = _resolve_relative_path(skill_dir, relative_path)
    if target.exists():
        raise ValueError("目标已存在")

    if is_dir:
        target.mkdir(parents=True, exist_ok=False)
        return

    if not _is_text_path(target):
        raise ValueError("仅支持创建文本文件")

    target.parent.mkdir(parents=True, exist_ok=True)

    # 先写入文件，再更新元数据
    target.write_text(content or "", encoding="utf-8")

    await _update_skill_metadata_if_skills_md(db, item, content or "", skill_dir, target, updated_by)


async def update_skill_file(
    db: AsyncSession,
    *,
    slug: str,
    relative_path: str,
    content: str,
    updated_by: str | None,
) -> None:
    item = await get_skill_or_raise(db, slug)
    skill_dir = _resolve_prompt_dir(item)
    target, _ = _resolve_relative_path(skill_dir, relative_path)
    if not target.exists() or not target.is_file():
        raise ValueError("文件不存在")
    if not _is_text_path(target):
        raise ValueError("仅支持编辑文本文件")

    await _update_skill_metadata_if_skills_md(db, item, content, skill_dir, target, updated_by)

    target.write_text(content, encoding="utf-8")

async def update_prompt_file(
    db: AsyncSession,
    *,
    path: str,
    content: str,
    updated_by: str | None,
) -> None:
    repo = PromptRepository(db)
    item = await repo.update(path, content, updated_by)

async def delete_prompt_file(
    db: AsyncSession,
    *,
    path: str,
) -> None:
    repo = PromptRepository(db)
    item = await repo.delete_by_path(path)


async def _update_skill_metadata_if_skills_md(
    db: AsyncSession,
    item: Prompt,
    content: str,
    skill_dir: Path,
    target: Path,
    updated_by: str | None,
) -> None:
    """如果目标文件是 SKILL.md，则解析并更新元数据"""
    if target.name == "SKILL.md" and target.parent == skill_dir:
        parsed_name, parsed_desc, _ = _parse_skill_markdown(content)
        if parsed_name != item.slug:
            raise ValueError("SKILL.md frontmatter.name 必须与 skill slug 一致")
        repo = SkillRepository(db)
        await repo.update_metadata(item, name=parsed_name, description=parsed_desc, updated_by=updated_by)


async def _update_prompt_metadata(
    db: AsyncSession,
    item: Prompt,
    name: str,
    filename: str,
    content: str,
    target: Path,
    updated_by: str | None,
) -> None:
    """更新元数据"""
    repo = PromptRepository(db)
    await repo.update_metadata(item, name=name, description=content, filename=filename,updated_by=updated_by)


async def delete_skill_node(db: AsyncSession, *, slug: str, relative_path: str) -> None:
    item = await get_skill_or_raise(db, slug)
    skill_dir = _resolve_prompt_dir(item)
    target, rel = _resolve_relative_path(skill_dir, relative_path, allow_root=False)
    if not target.exists():
        raise ValueError("目标不存在")

    if rel == "SKILL.md":
        raise ValueError("不允许删除根目录 SKILL.md")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()


async def export_skill_zip(db: AsyncSession, slug: str) -> tuple[str, str]:
    item = await get_skill_or_raise(db, slug)
    skill_dir = _resolve_prompt_dir(item)
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise ValueError("技能目录不存在")

    fd, export_path = tempfile.mkstemp(prefix=f"skill-{slug}-", suffix=".zip")
    Path(export_path).unlink(missing_ok=True)
    export_file = Path(export_path)
    try:
        with zipfile.ZipFile(export_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in skill_dir.rglob("*"):
                arcname = Path(slug) / p.relative_to(skill_dir)
                zf.write(p, arcname.as_posix())
    except Exception:
        export_file.unlink(missing_ok=True)
        raise
    return export_path, f"{slug}.zip"


async def delete_skill(db: AsyncSession, *, slug: str) -> None:
    repo = SkillRepository(db)
    item = await repo.get_by_slug(slug)
    if not item:
        raise ValueError(f"技能 '{slug}' 不存在")

    skill_dir = _resolve_prompt_dir(item)
    trash_dir: Path | None = None

    if skill_dir.exists():
        trash_dir = skill_dir.with_name(f".deleted-{slug}-{uuid.uuid4().hex[:8]}")
        skill_dir.rename(trash_dir)

    try:
        await repo.delete(item)
    except Exception:
        if trash_dir and trash_dir.exists():
            trash_dir.rename(skill_dir)
        raise

    if trash_dir and trash_dir.exists():
        shutil.rmtree(trash_dir, ignore_errors=True)
