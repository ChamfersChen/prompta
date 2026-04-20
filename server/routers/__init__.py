from fastapi import APIRouter

from server.routers.auth_router import auth

# from server.routers.dashboard_router import dashboard
from server.routers.department_router import department
from server.routers.system_router import system
from server.routers.prompt_router import prompts
from server.routers.market_router import market
from server.routers.community_router import community
from server.routers.api_key_router import api_keys, open_prompts

router = APIRouter()

# 注册路由结构
router.include_router(system)  # /api/system/*
router.include_router(auth)  # /api/auth/*
# router.include_router(dashboard)  # /api/dashboard/*
router.include_router(department)  # /api/departments/*
router.include_router(prompts)  # /api/system/prompts/*
router.include_router(market)  # /api/market/*
router.include_router(community)  # /api/community/*
router.include_router(api_keys)  # /api/system/api-keys/*
router.include_router(open_prompts)  # /api/open/prompts/*
