from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.services.run_queue_service import close_queue_clients, get_redis_client
from src.storage.postgres.manager import pg_manager
from src.utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan事件管理器"""
    # 初始化数据库连接
    try:
        pg_manager.initialize()
        await pg_manager.create_business_tables()
        await pg_manager.ensure_business_schema_compat()
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {e}")

    # # 预热 Redis（run 队列）
    # try:
    #     redis = await get_redis_client()
    #     await redis.ping()
    # except Exception as e:
    #     logger.warning(f"Run queue redis unavailable on startup: {e}")

    yield

    await close_queue_clients()
    await pg_manager.close()
