from fastapi import APIRouter

from server.routers.auth_router import auth
from server.routers.system_router import system

router = APIRouter()

# 注册路由结构
router.include_router(system)  # /api/system/*
router.include_router(auth)  # /api/auth/*