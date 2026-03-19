import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// import { useAgentStore } from './agent'

export const useUserStore = defineStore('user', () => {
  // 状态
  // const token = ref(localStorage.getItem('user_token') || '')
  const token = ref(sessionStorage.getItem('user_token') || '')
  const userId = ref(null)
  const username = ref('')
  const userIdLogin = ref('')
  const phoneNumber = ref('')
  const avatar = ref('')
  const userRole = ref('')
  const departmentId = ref(null)
  const departmentName = ref('')

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userRole.value === 'admin' || userRole.value === 'superadmin')
  const isSuperAdmin = computed(() => userRole.value === 'superadmin')

  // 动作
  async function login(credentials) {
    try {
      const formData = new FormData()
      // 支持user_id或phone_number登录
      formData.append('username', credentials.loginId) // 使用loginId作为通用登录标识
      formData.append('password', credentials.password)

      const response = await fetch('/api/auth/token', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()

        // 如果是423锁定状态码，抛出包含状态码的错误
        if (response.status === 423) {
          const lockError = new Error(error.detail || '账户被锁定')
          lockError.status = 423
          lockError.headers = response.headers
          throw lockError
        }

        throw new Error(error.detail || '登录失败')
      }

      const data = await response.json()

      // 更新状态
      token.value = data.access_token
      userId.value = data.user_id
      username.value = data.username
      userIdLogin.value = data.user_id_login
      phoneNumber.value = data.phone_number || ''
      avatar.value = data.avatar || ''
      userRole.value = data.role
      departmentId.value = data.department_id || null
      departmentName.value = data.department_name || ''

      // 只保存 token 到本地存储
      // localStorage.setItem('user_token', data.access_token)
      sessionStorage.setItem('user_token', data.access_token)

      return true
    } catch (error) {
      console.error('登录错误:', error)
      throw error
    }
  }

  async function loginNoVerify(credentials) {
    try {
      const formData = new FormData()
      // 支持user_id或phone_number登录
      formData.append('username', credentials.loginId) // 使用loginId作为通用登录标识
      formData.append('password', credentials.password)

      const response = await fetch('/api/auth/token-no-verify', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()

        // 如果是423锁定状态码，抛出包含状态码的错误
        if (response.status === 423) {
          const lockError = new Error(error.detail || '账户被锁定')
          lockError.status = 423
          lockError.headers = response.headers
          throw lockError
        }

        throw new Error(error.detail || '登录失败')
      }

      const data = await response.json()

      // 更新状态
      token.value = data.access_token
      userId.value = data.user_id
      username.value = data.username
      userIdLogin.value = data.user_id_login
      phoneNumber.value = data.phone_number || ''
      avatar.value = data.avatar || ''
      userRole.value = data.role
      departmentId.value = data.department_id || null
      departmentName.value = data.department_name || ''

      // 只保存 token 到本地存储
      // localStorage.setItem('user_token', data.access_token)
      sessionStorage.setItem('user_token', data.access_token)

      return true
    } catch (error) {
      console.error('登录错误:', error)
      throw error
    }
  }

  function logout() {
    // 清除状态
    token.value = ''
    userId.value = null
    username.value = ''
    userIdLogin.value = ''
    phoneNumber.value = ''
    avatar.value = ''
    userRole.value = ''
    departmentId.value = null
    departmentName.value = ''

    // 清除 agentStore 状态，确保重新登录时能正确加载数据
    // const agentStore = useAgentStore()
    // agentStore.reset()

    // 只清除 token
    // localStorage.removeItem('user_token')
    sessionStorage.removeItem('user_token')
  }

  async function initialize(admin) {
    try {
      const response = await fetch('/api/auth/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(admin)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '初始化管理员失败')
      }

      const data = await response.json()

      // 更新状态
      token.value = data.access_token
      userId.value = data.user_id
      username.value = data.username
      userIdLogin.value = data.user_id_login
      phoneNumber.value = data.phone_number || ''
      avatar.value = data.avatar || ''
      userRole.value = data.role
      departmentId.value = data.department_id || null
      departmentName.value = data.department_name || ''

      // 只保存 token 到本地存储
      // localStorage.setItem('user_token', data.access_token)
      sessionStorage.setItem('user_token', data.access_token)

      return true
    } catch (error) {
      console.error('初始化管理员错误:', error)
      throw error
    }
  }

  async function checkFirstRun() {
    try {
      const response = await fetch('/api/auth/check-first-run')
      const data = await response.json()
      return data.first_run
    } catch (error) {
      console.error('检查首次运行状态错误:', error)
      return false
    }
  }

  // 用于API请求的授权头
  function getAuthHeaders() {
    return {
      Authorization: `Bearer ${token.value}`
    }
  }

  // 用户管理功能
  async function getUsers() {
    try {
      const response = await fetch('/api/auth/users', {
        headers: {
          ...getAuthHeaders()
        }
      })

      if (!response.ok) {
        throw new Error('获取用户列表失败')
      }

      return await response.json()
    } catch (error) {
      console.error('获取用户列表错误:', error)
      throw error
    }
  }

  async function createUser(userData) {
    try {
      const response = await fetch('/api/auth/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(userData)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '创建用户失败')
      }

      return await response.json()
    } catch (error) {
      console.error('创建用户错误:', error)
      throw error
    }
  }

  async function updateUser(userId, userData) {
    try {
      const response = await fetch(`/api/auth/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(userData)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '更新用户失败')
      }

      return await response.json()
    } catch (error) {
      console.error('更新用户错误:', error)
      throw error
    }
  }

  async function deleteUser(userId) {
    try {
      const response = await fetch(`/api/auth/users/${userId}`, {
        method: 'DELETE',
        headers: {
          ...getAuthHeaders()
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '删除用户失败')
      }

      return await response.json()
    } catch (error) {
      console.error('删除用户错误:', error)
      throw error
    }
  }

  // 验证用户名并生成user_id
  async function validateUsernameAndGenerateUserId(username) {
    try {
      const response = await fetch('/api/auth/validate-username', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({ username })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '用户名验证失败')
      }

      return await response.json()
    } catch (error) {
      console.error('用户名验证错误:', error)
      throw error
    }
  }

  // 上传头像
  async function uploadAvatar(file) {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/auth/upload-avatar', {
        method: 'POST',
        headers: {
          ...getAuthHeaders()
        },
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '头像上传失败')
      }

      const data = await response.json()

      // 更新本地头像状态
      avatar.value = data.avatar_url

      return data
    } catch (error) {
      console.error('头像上传错误:', error)
      throw error
    }
  }

  // 获取当前用户信息
  async function getCurrentUser() {
    try {
      const response = await fetch('/api/auth/me', {
        headers: {
          ...getAuthHeaders()
        }
      })

      if (!response.ok) {
        throw new Error('获取用户信息失败')
      }

      const userData = await response.json()

      // 更新本地状态
      userId.value = userData.id
      username.value = userData.username
      userIdLogin.value = userData.user_id
      phoneNumber.value = userData.phone_number || ''
      avatar.value = userData.avatar || ''
      userRole.value = userData.role
      departmentId.value = userData.department_id || null
      departmentName.value = userData.department_name || ''

      return userData
    } catch (error) {
      console.error('获取用户信息错误:', error)
      throw error
    }
  }

  // 更新个人资料
  async function updateProfile(profileData) {
    try {
      const response = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(profileData)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '更新个人资料失败')
      }

      const userData = await response.json()

      // 更新本地状态
      if (typeof userData.username === 'string') {
        username.value = userData.username
      }
      if (typeof userData.phone_number !== 'undefined') {
        phoneNumber.value = userData.phone_number || ''
      }

      return userData
    } catch (error) {
      console.error('更新个人资料错误:', error)
      throw error
    }
  }

  // 轮询后端API，若token不一致则自动登出
  let pollTimer = null
  function startTokenPoll() {
    if (pollTimer) return // 避免重复启动
    pollTimer = setInterval(async () => {
      try {
        const res = await fetch('/api/auth/token-check', {
          headers: { ...getAuthHeaders() }
        })
        if (!res.ok) throw new Error('token-check failed')
        console.log('token-check passed: ', res)
        const { access_token: serverToken } = await res.json()
        if (serverToken !== token.value) {
          console.warn('Token 不一致，广播登出')

          // 1. 清理本地状态
          logout()

          // 2. 通知其他页面
          // localStorage.setItem('FORCE_LOGOUT', Date.now().toString())
          sessionStorage.setItem('FORCE_LOGOUT', Date.now().toString())
          // 3. 当前页面跳转
          window.location.replace('/login_agents_show')
          stopTokenPoll()
        }
      } catch (e) {
        console.error('Token 轮询异常:', e)
        logout()
        stopTokenPoll()
      }
    }, 10000)
  }

  function stopTokenPoll() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  // 暴露给外部调用
  function pollApi(action = 'start') {
    if (action === 'start') startTokenPoll()
    else if (action === 'stop') stopTokenPoll()
  }

  return {
    // 状态
    token,
    userId,
    username,
    userIdLogin,
    phoneNumber,
    avatar,
    userRole,
    departmentId,
    departmentName,

    // 计算属性
    isLoggedIn,
    isAdmin,
    isSuperAdmin,

    // 方法
    login,
    loginNoVerify,
    logout,
    initialize,
    checkFirstRun,
    getAuthHeaders,
    getUsers,
    createUser,
    updateUser,
    deleteUser,
    validateUsernameAndGenerateUserId,
    uploadAvatar,
    getCurrentUser,
    updateProfile,
    pollApi
  }
})

// 检查当前用户是否有管理员权限
export const checkAdminPermission = () => {
  const userStore = useUserStore()
  if (!userStore.isAdmin) {
    throw new Error('需要管理员权限')
  }
  return true
}

// 检查当前用户是否有超级管理员权限
export const checkSuperAdminPermission = () => {
  const userStore = useUserStore()
  return userStore.isSuperAdmin
}
