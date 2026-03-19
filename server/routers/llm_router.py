import traceback
import uuid
import json
import os
from typing import Any
from langchain.messages import AIMessage, AIMessageChunk, HumanMessage

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres.models_business import User
from server.routers.auth_router import get_admin_user
from server.utils.auth_middleware import get_db, get_required_user
from src import config as conf
from src.models import select_model
from src.services.chat_stream_service import get_agent_state_view, llm_chat_stream, stream_agent_chat, stream_agent_resume
from src.services.agent_run_service import (
    cancel_agent_run_view,
    create_agent_run_view,
    get_active_run_by_thread,
    get_agent_run_view,
    stream_agent_run_events,
)
from src.services.conversation_service import (
    create_thread_view,
    delete_thread_attachment_view,
    delete_thread_view,
    list_thread_attachments_view,
    list_threads_view,
    list_threads_view_whth_llm,
    update_thread_view,
    upload_thread_attachment_view,
)
from src.services.history_query_service import get_llm_history_view
from src.utils.logging_config import logger
from src.utils.image_processor import process_uploaded_image
from src.utils import hashstr

from server.storage.miniio import MinIOClient
from server.utils.audio_utils import audio2text


# 图片上传响应模型
class ImageUploadResponse(BaseModel):
    success: bool
    image_content: str | None = None
    thumbnail_content: str | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    error: str | None = None


class AgentConfigCreate(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None
    pics: list[str] | None = None
    examples: list[str] | None = None
    config_json: dict | None = None
    set_default: bool = False


class AgentConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    pics: list[str] | None = None
    examples: list[str] | None = None
    config_json: dict | None = None


class AgentRunCreate(BaseModel):
    query: str
    config: dict = Field(default_factory=dict)
    image_content: str | None = None


llm = APIRouter(prefix="/llm", tags=["llm"])


@llm.post("/call")
async def call(query: str = Body(...), meta: dict = Body(None), current_user: User = Depends(get_required_user)):
    """调用模型进行简单问答（需要登录）"""
    meta = meta or {}

    # 确保 request_id 存在
    if "request_id" not in meta or not meta.get("request_id"):
        meta["request_id"] = str(uuid.uuid4())

    model = select_model(
        model_provider=meta.get("model_provider"),
        model_name=meta.get("model_name"),
        model_spec=meta.get("model_spec") or meta.get("model"),
    )

    response = await model.call(query)
    logger.debug({"query": query, "response": response.content})

    return {"response": response.content, "request_id": meta["request_id"]}



@llm.post("/llm/{llm_id}")
async def chat_llm(
    llm_id: str,
    query: str = Body(...),
    config: dict = Body({}),
    meta: dict = Body({}),
    image_content: str | None = Body(None),
    # current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """使用特定智能体进行对话（需要登录）"""
    logger.info(f"agent_id: {llm_id}, query: {query}, config: {config}, meta: {meta}")
    logger.info(f"image_content present: {image_content is not None}")
    if image_content:
        logger.info(f"image_content length: {len(image_content)}")
        logger.info(f"image_content preview: {image_content[:50]}...")

    # 确保 request_id 存在
    if "request_id" not in meta or not meta.get("request_id"):
        meta["request_id"] = str(uuid.uuid4())

    meta.update(
        {
            "query": query,
            "llm_id": llm_id,
            "server_model_name": config.get("model", llm_id),
            "thread_id": config.get("thread_id"),
            "user_id": 1,
            "has_image": bool(image_content),
        }
    )
    model = select_model(
        model_provider=meta.get("model_provider"),
        model_name=meta.get("model_name"),
        model_spec=meta.get("model_spec") or meta.get("model"),
    )


    # response = await model.call(query, stream=True)
    return StreamingResponse(
        llm_chat_stream(model, query, meta, config=config, db=db),
        # stream_agent_chat(
        #     agent_id=agent_id,
        #     query=query,
        #     config=config,
        #     meta=meta,
        #     image_content=image_content,
        #     current_user=current_user,
        #     db=db,
        # ),
        media_type="application/json",
    )


@llm.get("/runs/{run_id}")
async def get_agent_run(
    run_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 run 状态（需要登录）"""
    return await get_agent_run_view(run_id=run_id, current_user_id=str(current_user.id), db=db)


@llm.post("/runs/{run_id}/cancel")
async def cancel_agent_run(
    run_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """取消 run（需要登录）"""
    return await cancel_agent_run_view(run_id=run_id, current_user_id=str(current_user.id), db=db)


@llm.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    after_seq: str = Query("0"),
    current_user: User = Depends(get_required_user),
):
    """SSE 拉取 run 事件（需要登录）"""
    return StreamingResponse(
        stream_agent_run_events(
            run_id=run_id,
            after_seq=after_seq,
            current_user_id=str(current_user.id),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@llm.get("/thread/{thread_id}/active_run")
async def get_thread_active_run(
    thread_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前会话活跃 run（需要登录）"""
    return await get_active_run_by_thread(thread_id=thread_id, current_user_id=str(current_user.id), db=db)


# =============================================================================
# > === 模型管理分组 ===
# =============================================================================


@llm.get("/models")
async def get_chat_models(model_provider: str, current_user: User = Depends(get_admin_user)):
    """获取指定模型提供商的模型列表（需要登录）"""
    model = select_model(model_provider=model_provider)
    models = await model.get_models()
    return {"models": models}


@llm.post("/models/update")
async def update_chat_models(model_provider: str, model_names: list[str], current_user=Depends(get_admin_user)):
    """更新指定模型提供商的模型列表 (仅管理员)"""
    conf.model_names[model_provider].models = model_names
    conf._save_models_to_file(model_provider)
    return {"models": conf.model_names[model_provider].models}



@llm.get("/message/history")
async def get_llm_history(
    thread_id: str, current_user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)
):
    """获取智能体历史消息（需要登录）- 包含用户反馈状态"""
    try:
        return await get_llm_history_view(
            thread_id=thread_id,
            current_user_id=str(current_user.id),
            db=db,
        )

    except Exception as e:
        logger.error(f"获取智能体历史消息出错: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取智能体历史消息出错: {str(e)}")


@llm.get("/agent/{agent_id}/state")
async def get_agent_state(
    agent_id: str,
    thread_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取智能体当前状态（需要登录）"""
    try:
        return await get_agent_state_view(
            agent_id=agent_id,
            thread_id=thread_id,
            current_user_id=str(current_user.id),
            db=db,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AgentState出错: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取AgentState出错: {str(e)}")


# ==================== 线程管理 API ====================


class ThreadCreate(BaseModel):
    title: str | None = None
    llm_id: str
    metadata: dict | None = None


class ThreadResponse(BaseModel):
    id: str
    user_id: str
    llm_id: str
    title: str | None = None
    is_pinned: bool = False
    created_at: str
    updated_at: str


# =============================================================================
# > === 会话管理分组 ===
# =============================================================================


@llm.post("/thread", response_model=ThreadResponse)
async def create_thread(
    thread: ThreadCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_required_user)
):
    """创建新对话线程 (使用新存储系统)"""
    return await create_thread_view(
        llm_id=thread.llm_id,
        title=thread.title,
        metadata=thread.metadata,
        db=db,
        current_user_id=str(current_user.id),
    )


@llm.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    llm_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取用户的所有对话线程 (使用新存储系统)"""
    return await list_threads_view_whth_llm(
        llm_id=llm_id, db=db, current_user_id=str(current_user.id), limit=limit, offset=offset
    )


@llm.delete("/thread/{thread_id}")
async def delete_thread(
    thread_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_required_user)
):
    """删除对话线程 (使用新存储系统)"""
    return await delete_thread_view(thread_id=thread_id, db=db, current_user_id=str(current_user.id))


class ThreadUpdate(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None


@llm.put("/thread/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    thread_update: ThreadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """更新对话线程信息 (使用新存储系统)"""
    return await update_thread_view(
        thread_id=thread_id,
        title=thread_update.title,
        is_pinned=thread_update.is_pinned,
        db=db,
        current_user_id=str(current_user.id),
    )
