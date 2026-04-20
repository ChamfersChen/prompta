"""PostgreSQL 业务数据模型 - 用户、部门、提示词等相关表"""

from typing import Any
from datetime import timedelta
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from src.utils.datetime_utils import format_utc_datetime, utc_now_naive

Base = declarative_base()

MAX_LOGIN_FAILED_ATTEMPTS = 5
LOGIN_LOCK_DURATION_SECONDS = 300


class Department(Base):
    """部门模型"""

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    # 关联关系
    users = relationship("User", back_populates="department", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": format_utc_datetime(self.created_at),
        }


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)  # 显示名称
    user_id = Column(String, nullable=False, unique=True, index=True)  # 登录ID
    phone_number = Column(String, nullable=True, unique=True, index=True)  # 手机号
    avatar = Column(String, nullable=True)  # 头像URL
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # 角色: superadmin, admin, user
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # 部门ID
    created_at = Column(DateTime, default=utc_now_naive)
    last_login = Column(DateTime, nullable=True)

    # 登录失败限制相关字段
    login_failed_count = Column(Integer, nullable=False, default=0)  # 登录失败次数
    last_failed_login = Column(DateTime, nullable=True)  # 最后一次登录失败时间
    login_locked_until = Column(DateTime, nullable=True)  # 锁定到什么时候

    # 软删除相关字段
    is_deleted = Column(Integer, nullable=False, default=0, index=True)  # 是否已删除：0=否，1=是
    deleted_at = Column(DateTime, nullable=True)  # 删除时间

    # 关联操作日志
    operation_logs = relationship("OperationLog", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    # 关联部门
    department = relationship("Department", back_populates="users")

    def to_dict(self, include_password: bool = False) -> dict[str, Any]:
        result = {
            "id": self.id,
            "username": self.username,
            "user_id": self.user_id,
            "phone_number": self.phone_number,
            "avatar": self.avatar,
            "role": self.role,
            "department_id": self.department_id,
            "created_at": format_utc_datetime(self.created_at),
            "last_login": format_utc_datetime(self.last_login),
            "login_failed_count": self.login_failed_count,
            "last_failed_login": format_utc_datetime(self.last_failed_login),
            "login_locked_until": format_utc_datetime(self.login_locked_until),
            "is_deleted": self.is_deleted,
            "deleted_at": format_utc_datetime(self.deleted_at),
        }
        if include_password:
            result["password_hash"] = self.password_hash
        return result

    def is_login_locked(self) -> bool:
        """检查用户是否处于登录锁定状态"""
        if self.login_locked_until is None:
            return False
        return utc_now_naive() < self.login_locked_until

    def increment_failed_login(self):
        """增加登录失败计数，并在达到阈值后锁定登录"""
        self.login_failed_count += 1
        self.last_failed_login = utc_now_naive()
        if self.login_failed_count >= MAX_LOGIN_FAILED_ATTEMPTS:
            self.login_locked_until = self.last_failed_login + timedelta(seconds=LOGIN_LOCK_DURATION_SECONDS)

    def get_remaining_lock_time(self) -> int:
        """获取剩余锁定时间（秒）"""
        if self.login_locked_until is None:
            return 0
        remaining = int((self.login_locked_until - utc_now_naive()).total_seconds())
        return max(0, remaining)

    def reset_failed_login(self):
        """重置登录失败相关字段"""
        self.login_failed_count = 0
        self.last_failed_login = None
        self.login_locked_until = None

class OperationLog(Base):
    """操作日志模型"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utc_now_naive)

    # 关联用户
    user = relationship("User", back_populates="operation_logs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "operation": self.operation,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": format_utc_datetime(self.timestamp),
        }


class Prompt(Base):
    """Prompt 元数据模型（内容存文件系统，索引存数据库）"""

    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=True, comment="提示词名称")
    path = Column(String(128), nullable=True, comment="提示词文件路径")
    description = Column(Text, nullable=True, comment="提示词描述")
    dir_path = Column(String(512), nullable=False, comment="技能目录路径（相对 save_dir）")
    is_dir = Column(Integer, nullable=False, default=0, comment="是否为目录：0=否，1=是")
    created_by = Column(String(64), nullable=True)
    updated_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "external_id": self.external_id,
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "dir_path": self.dir_path,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class Template(Base):
    """社区模板模型（提示词或技能发布到社区）"""

    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, comment="UUID")
    name = Column(String(128), nullable=False, comment="模板名称")
    community_type = Column(String(32), nullable=False, default="prompt", comment="类型: prompt/skill")
    category = Column(String(64), nullable=False, default="writing", comment="分类")
    description = Column(Text, nullable=True, comment="模板描述")
    tags = Column(JSON, nullable=True, comment="标签列表")
    content = Column(Text, nullable=True, comment="提示词内容（prompt 类型）")
    variables = Column(JSON, nullable=True, comment="变量定义列表")
    file_tree = Column(JSON, nullable=True, comment="技能文件树快照（skill 类型）")
    source_path = Column(String(512), nullable=True, comment="源文件路径")
    source_slug = Column(String(128), nullable=True, comment="源技能 slug（skill 类型）")
    is_public = Column(Boolean, nullable=False, default=False, comment="是否公开到社区")
    is_official = Column(Boolean, nullable=False, default=False, comment="是否为官方模板")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, comment="所属部门ID")
    usage_count = Column(Integer, nullable=False, default=0, comment="使用次数")
    view_count = Column(Integer, nullable=False, default=0, comment="浏览次数")
    favorite_count = Column(Integer, nullable=False, default=0, comment="收藏次数")
    rating = Column(Float, nullable=False, default=0.0, comment="平均评分")
    rating_count = Column(Integer, nullable=False, default=0, comment="评分人数")
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    owner = relationship("User")
    department = relationship("Department")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "community_type": self.community_type,
            "category": self.category,
            "description": self.description,
            "tags": self.tags or [],
            "content": self.content,
            "variables": self.variables or [],
            "file_tree": self.file_tree,
            "source_path": self.source_path,
            "source_slug": self.source_slug,
            "is_public": self.is_public,
            "is_official": self.is_official,
            "owner_id": self.owner_id,
            "department_id": self.department_id,
            "author": self.owner.username if self.owner else "匿名",
            "department_name": self.department.name if self.department else None,
            "usageCount": self.usage_count,
            "viewCount": self.view_count,
            "rating": self.rating,
            "ratingCount": self.rating_count,
            "favoriteCount": self.favorite_count,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }

    def to_list_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "community_type": self.community_type,
            "category": self.category,
            "description": self.description,
            "tags": self.tags or [],
            "variables": self.variables or [],
            "source_path": self.source_path,
            "source_slug": self.source_slug,
            "is_public": self.is_public,
            "is_official": self.is_official,
            "author": self.owner.username if self.owner else "匿名",
            "department_name": self.department.name if self.department else None,
            "usageCount": self.usage_count,
            "viewCount": self.view_count,
            "favoriteCount": self.favorite_count,
            "rating": self.rating,
            "ratingCount": self.rating_count,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class TemplateFavorite(Base):
    """社区收藏模型"""

    __tablename__ = "template_favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(String(36), ForeignKey("templates.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    item_type = Column(String(16), nullable=False, default="prompt", comment="收藏类型: prompt/skill")
    folder_path = Column(String(512), nullable=True, comment="收藏夹路径")
    created_at = Column(DateTime, default=utc_now_naive)

    __table_args__ = (UniqueConstraint("user_id", "template_id", name="uq_user_template_favorite"),)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "department_id": self.department_id,
            "item_type": self.item_type,
            "folder_path": self.folder_path,
            "created_at": format_utc_datetime(self.created_at),
        }


class TemplateFavoriteFolder(Base):
    """收藏夹模型（支持空收藏夹与持久化）"""

    __tablename__ = "template_favorite_folders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    item_type = Column(String(16), nullable=False, default="prompt", comment="收藏类型: prompt/skill")
    folder_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "department_id",
            "item_type",
            "folder_name",
            name="uq_user_department_item_folder",
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "item_type": self.item_type,
            "folder_name": self.folder_name,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class TemplateRating(Base):
    """模板评分模型"""

    __tablename__ = "template_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(String(36), ForeignKey("templates.id"), nullable=False)
    rating = Column(Integer, nullable=False, comment="评分 1-5")
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    __table_args__ = (UniqueConstraint("user_id", "template_id", name="uq_user_template_rating"),)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "rating": self.rating,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class TemplateComment(Base):
    """模板评论模型"""

    __tablename__ = "template_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(String(36), ForeignKey("templates.id"), nullable=False)
    content = Column(Text, nullable=False, comment="评论内容")
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "author": self.owner.username if self.owner else "匿名",
            "content": self.content,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }

    # 关联 owner
    owner = relationship("User")


class APIKey(Base):
    """API Key 模型"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    key_prefix = Column(String(32), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    user = relationship("User", back_populates="api_keys")
    department = relationship("Department")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key_prefix": self.key_prefix,
            "name": self.name,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "expires_at": format_utc_datetime(self.expires_at),
            "is_enabled": bool(self.is_enabled),
            "last_used_at": format_utc_datetime(self.last_used_at),
            "created_by": self.created_by,
            "created_at": format_utc_datetime(self.created_at),
        }

    def is_valid(self) -> bool:
        if not self.is_enabled:
            return False
        if self.expires_at is not None and self.expires_at <= utc_now_naive():
            return False
        return True
