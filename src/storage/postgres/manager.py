"""PostgreSQL 数据库管理器 - 支持知识库和业务数据"""

import json
import os
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from server.utils.singleton import SingletonMeta
from src.storage.postgres.models_business import Base as BusinessBase
from src.utils import logger

# 合并两个 Base
CombinedBase = declarative_base()

# 继承所有表
for module in [BusinessBase]:
    for table_name in dir(module):
        table = getattr(module, table_name)
        if isinstance(table, type) and hasattr(table, "__tablename__"):
            setattr(CombinedBase, table_name, table)


class PostgresManager(metaclass=SingletonMeta):
    """PostgreSQL 数据库管理器 - 支持知识库和业务数据"""

    # 知识库 PostgreSQL URL 环境变量名
    KB_DATABASE_URL_ENV = "POSTGRES_URL"

    def __init__(self):
        self.async_engine = None
        self.AsyncSession = None
        self._initialized = False

    def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return

        db_url = os.getenv(self.KB_DATABASE_URL_ENV)
        if not db_url:
            logger.error(
                f"环境变量 {self.KB_DATABASE_URL_ENV} 未设置，"
                "请在 docker-compose.yml 或 .env 中配置 PostgreSQL 连接字符串"
            )
            return

        try:
            # 创建异步 SQLAlchemy 引擎
            self.async_engine = create_async_engine(
                db_url,
                json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
                json_deserializer=json.loads,
                pool_pre_ping=True,
                pool_recycle=1800,
            )

            # 创建异步会话工厂
            self.AsyncSession = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self._initialized = True
            logger.info(f"PostgreSQL manager initialized for knowledge base: {db_url.split('@')[0]}://***")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL manager: {e}")
            # 不抛出异常，允许应用启动，但在使用时会报错

    def _check_initialized(self):
        """检查是否已初始化"""
        if not self._initialized:
            raise RuntimeError("PostgreSQL manager not initialized. Please check configuration.")

    async def create_tables(self):
        """创建所有表（知识库和业务表）"""
        self._check_initialized()
        async with self.async_engine.begin() as conn:
            await conn.run_sync(BusinessBase.metadata.create_all)
        logger.info("PostgreSQL tables created/checked (knowledge + business)")

    async def create_business_tables(self):
        """创建所有业务数据表"""
        self._check_initialized()
        async with self.async_engine.begin() as conn:
            await conn.run_sync(BusinessBase.metadata.create_all)
        logger.info("PostgreSQL business tables created/checked")

    async def ensure_business_schema_compat(self):
        """补齐历史库缺失字段/索引，避免 create_all 无法 alter 的问题"""
        self._check_initialized()
        if self.async_engine.dialect.name != "postgresql":
            return

        async with self.async_engine.begin() as conn:
            await conn.execute(text("ALTER TABLE prompts ADD COLUMN IF NOT EXISTS external_id VARCHAR(36)"))
            await conn.execute(
                text(
                    "ALTER TABLE template_favorites ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id)"
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE template_favorites tf
                    SET department_id = t.department_id
                    FROM templates t
                    WHERE tf.template_id = t.id AND tf.department_id IS NULL
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_template_favorites_department_id ON template_favorites (department_id)"
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS template_favorite_folders (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        department_id INTEGER NULL REFERENCES departments(id),
                        item_type VARCHAR(16) NOT NULL DEFAULT 'prompt',
                        folder_name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                        CONSTRAINT uq_user_department_item_folder
                            UNIQUE (user_id, department_id, item_type, folder_name)
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_template_favorite_folders_user_id ON template_favorite_folders (user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_template_favorite_folders_department_id ON template_favorite_folders (department_id)"
                )
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO template_favorite_folders (user_id, department_id, item_type, folder_name)
                    SELECT DISTINCT tf.user_id, tf.department_id, tf.item_type, tf.folder_path
                    FROM template_favorites tf
                    WHERE tf.folder_path IS NOT NULL AND tf.folder_path <> ''
                    ON CONFLICT (user_id, department_id, item_type, folder_name) DO NOTHING
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    UPDATE prompts
                    SET external_id = lower(
                        substr(md5(random()::text || clock_timestamp()::text || id::text), 1, 8)
                        || '-' || substr(md5(random()::text || id::text), 1, 4)
                        || '-' || substr(md5(clock_timestamp()::text || random()::text), 1, 4)
                        || '-' || substr(md5(id::text || random()::text), 1, 4)
                        || '-' || substr(md5(clock_timestamp()::text || id::text || random()::text), 1, 12)
                    )
                    WHERE external_id IS NULL OR external_id = ''
                    """
                )
            )

            await conn.execute(text("ALTER TABLE prompts ALTER COLUMN external_id SET NOT NULL"))
            await conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_prompts_external_id ON prompts (external_id)")
            )

    async def drop_tables(self):
        """删除所有表（慎用！）"""
        self._check_initialized()
        async with self.async_engine.begin() as conn:
            await conn.run_sync(BusinessBase.metadata.drop_all)
        logger.info("PostgreSQL tables dropped")

    @property
    def is_postgresql(self) -> bool:
        """检查是否是 PostgreSQL 数据库"""
        if not self._initialized:
            return False
        return self.async_engine.dialect.name == "postgresql"

    async def get_async_session(self) -> AsyncSession:
        """获取异步数据库会话"""
        self._check_initialized()
        return self.AsyncSession()

    @asynccontextmanager
    async def get_async_session_context(self):
        """获取异步数据库会话的上下文管理器"""
        self._check_initialized()
        session = self.AsyncSession()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"PostgreSQL async operation failed: {e}")
            raise
        finally:
            await session.close()

    async def close(self):
        """关闭引擎"""
        if self.async_engine:
            await self.async_engine.dispose()

    async def async_check_first_run(self):
        """检查是否首次运行（异步版本）- 检查用户表是否有数据"""
        from sqlalchemy import func, select

        self._check_initialized()
        async with self.get_async_session_context() as session:
            from src.storage.postgres.models_business import User

            result = await session.execute(select(func.count(User.id)))
            count = result.scalar()
            return count == 0

    async def execute(self, statement):
        """直接执行 SQL 语句（用于迁移脚本）"""
        self._check_initialized()
        async with self.get_async_session_context() as session:
            return await session.execute(statement)

    async def add(self, instance):
        """添加实例到会话（用于迁移脚本）"""
        self._check_initialized()
        async with self.get_async_session_context() as session:
            session.add(instance)

    async def commit(self):
        """提交当前会话"""
        self._check_initialized()
        async with self.get_async_session_context():
            pass  # commit is automatic in context manager


# 创建全局 PostgreSQL 管理器实例
pg_manager = PostgresManager()
