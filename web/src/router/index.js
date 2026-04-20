import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'main',
      component: BlankLayout,
      children: [
        {
          path: '',
          name: 'Home',
          component: () => import('../views/HomeView.vue'),
          meta: { keepAlive: true, requiresAuth: false }
        }
      ]
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/extensions',
      name: 'extensions',
      component: AppLayout,
redirect: '/extensions/prompts',
      children: [
        {
          path: 'prompts',
          name: 'ExtensionsPrompts',
          component: () => import('../views/ExtensionsView.vue'),
          props: { tab: 'prompts' },
          meta: {
            keepAlive: false,
            requiresAuth: false,
            requiresAdmin: false,
            requiresSuperAdmin: false
          }
        }
      ]
    },
    {
      path: '/community',
      name: 'community',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'Community',
          component: () => import('../views/CommunityView.vue'),
          meta: { keepAlive: true, requiresAuth: false }
        }
      ]
    },
    {
      path: '/market',
      name: 'market',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'TemplateMarket',
          component: () => import('../views/TemplateMarketView.vue'),
          meta: { keepAlive: true, requiresAuth: false }
        }
      ]
    },
{
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/EmptyView.vue'),
      meta: { requiresAuth: false }
    }
  ]
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  // 检查路由是否需要认证
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth === true)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)
  const requiresSuperAdmin = to.matched.some((record) => record.meta.requiresSuperAdmin)

  const userStore = useUserStore()

  // 如果有 token 但用户信息未加载，先获取用户信息
  if (userStore.token && !userStore.userId) {
    try {
      await userStore.getCurrentUser()
    } catch (error) {
      // 如果获取用户信息失败（如 token 过期），清除 token
      console.error('获取用户信息失败:', error)
      userStore.logout()
    }
  }

  const isLoggedIn = userStore.isLoggedIn
  const isAdmin = userStore.isAdmin
  const isSuperAdmin = userStore.isSuperAdmin

  // 如果路由需要认证但用户未登录
  if (requiresAuth && !isLoggedIn) {
    // 保存尝试访问的路径，登录后跳转
    sessionStorage.setItem('redirect', to.fullPath)
    next('/login')
    return
  }

  // 如果用户已登录但访问登录页
  if (to.path === '/login' && isLoggedIn) {
    next('/')
    return
  }

  // Regular users default to community
  if (isLoggedIn && !isAdmin && !['/community', '/market'].includes(to.path)) {
    next('/community')
    return
  }

  // 其他情况正常导航
  next()
})

export default router
