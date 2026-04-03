from fastapi import APIRouter

from server.routers.auth_router import auth

# from server.routers.dashboard_router import dashboard
from server.routers.department_router import department
from server.routers.skill_router import skills
from server.routers.system_router import system
from server.routers.llm_router import llm
from server.routers.prompt_router import prompts
from server.routers.market_router import market

router = APIRouter()

# 注册路由结构
router.include_router(system)  # /api/system/*
router.include_router(auth)  # /api/auth/*
# router.include_router(dashboard)  # /api/dashboard/*
router.include_router(department)  # /api/departments/*
router.include_router(skills)  # /api/system/skills/*
router.include_router(llm)  # /api/system/tools/*
router.include_router(prompts)  # /api/system/prompts/*
router.include_router(market)  # /api/market/*
