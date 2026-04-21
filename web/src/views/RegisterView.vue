<template>
  <div class="login-view">
    <!-- 顶部导航 -->
    <nav class="login-navbar">
      <div class="navbar-content">
        <div class="brand-container">
          <h1 class="brand-text">
            <span v-if="brandOrgName" class="brand-org">{{ brandOrgName }}</span>
            <span v-if="brandOrgName && brandName !== brandOrgName" class="brand-separator"></span>
            <span class="brand-main">{{ brandName }}</span>
          </h1>
        </div>
        <div class="login-top-action">
          <a-button type="text" size="small" class="back-home-btn auth-text-btn" @click="goToLogin">
            已有账号？立即登录
          </a-button>
        </div>
      </div>
    </nav>

    <!-- 主要内容区 -->
    <main class="login-main">
      <div class="login-card">
        <!-- 左侧图片 -->
        <div class="card-side is-image">
          <img :src="loginBgImage" alt="注册背景" class="login-bg-image" />
        </div>

        <!-- 右侧表单 -->
        <div class="card-side is-form">
          <div class="form-wrapper">
            <header class="form-header">
              <p class="welcome-text">欢迎注册</p>
              <h2 class="form-title">创建您的账号</h2>
            </header>

            <!-- 注册表单 -->
            <div class="login-form">
              <a-form :model="registerForm" @finish="handleRegister" layout="vertical">
                <a-form-item
                  label="用户名"
                  name="username"
                  :rules="[{ required: true, message: '请输入用户名' }, { min: 2, message: '用户名至少2个字符' }]"
                >
                  <a-input v-model:value="registerForm.username" placeholder="请输入用户名">
                    <template #prefix>
                      <user-outlined />
                    </template>
                  </a-input>
                </a-form-item>

                <a-form-item
                  label="密码"
                  name="password"
                  :rules="[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6个字符' }]"
                >
                  <a-input-password v-model:value="registerForm.password" placeholder="请输入密码">
                    <template #prefix>
                      <lock-outlined />
                    </template>
                  </a-input-password>
                </a-form-item>

                <a-form-item
                  label="确认密码"
                  name="confirmPassword"
                  :rules="[{ required: true, message: '请确认密码' }, { validator: validateConfirmPassword }]"
                >
                  <a-input-password v-model:value="registerForm.confirmPassword" placeholder="请再次输入密码">
                    <template #prefix>
                      <lock-outlined />
                    </template>
                  </a-input-password>
                </a-form-item>

                <a-form-item>
                  <a-button
                    type="primary"
                    html-type="submit"
                    :loading="loading"
                    class="auth-primary-btn"
                    block
                    size="large"
                  >
                    注册
                  </a-button>
                </a-form-item>

                <div class="login-options" style="justify-content: center;">
                  <a @click="goToLogin">已有账号？立即登录</a>
                </div>
              </a-form>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useInfoStore } from '@/stores/info'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { apiPost } from '@/apis/base'

const router = useRouter()
const infoStore = useInfoStore()

const loginBgImage = computed(() => {
  return infoStore.organization?.login_bg || '/login-bg.jpg'
})

const brandName = computed(() => infoStore.organization?.name || 'Prompta')
const brandOrgName = computed(() => infoStore.organization?.org_name || '')

const loading = ref(false)
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = async () => {
  if (registerForm.confirmPassword !== registerForm.password) {
    return Promise.reject('两次输入的密码不一致')
  }
  return Promise.resolve()
}

const goToLogin = () => {
  router.push('/login')
}

const goHome = () => {
  router.push('/')
}

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.password || !registerForm.confirmPassword) {
    message.error('请填写完整信息')
    return
  }

  if (registerForm.password !== registerForm.confirmPassword) {
    message.error('两次输入的密码不一致')
    return
  }

  if (registerForm.password.length < 6) {
    message.error('密码长度不能少于6位')
    return
  }

  loading.value = true
  try {
    const result = await apiPost('/api/auth/register', {
      username: registerForm.username,
      password: registerForm.password,
      confirm_password: registerForm.confirmPassword
    }, {}, false)

    if (result.success) {
      message.success('注册成功，请登录')
      router.push('/login')
    } else {
      message.error(result.detail || '注册失败')
    }
  } catch (error) {
    console.error('注册失败:', error)
    message.error(error.message || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await infoStore.loadInfoConfig()
})
</script>

<style scoped>
.login-view {
  min-height: 100vh;
  background: #f5f5f5;
}

.login-navbar {
  height: 60px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: relative;
  z-index: 10;
}

.navbar-content {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.brand-container {
  display: flex;
  align-items: center;
}

.brand-text {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: #262626;
}

.brand-org {
  color: #1890ff;
}

.brand-separator {
  width: 1px;
  height: 20px;
  background: #d9d9d9;
  margin: 0 12px;
}

.brand-main {
  color: #262626;
}

.login-top-action {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-home-btn {
  color: #666;
}

.back-home-btn:hover {
  color: #1890ff;
}

:deep(.auth-text-btn.ant-btn-text) {
  border-radius: 10px;
  color: var(--main-700);
  font-weight: 600;
  border: 1px solid transparent;
}

:deep(.auth-text-btn.ant-btn-text:hover) {
  color: var(--main-800);
  background: var(--main-50);
  border-color: var(--main-100);
}

.login-main {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 60px);
  padding: 24px;
}

.login-card {
  display: flex;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  max-width: 900px;
  width: 100%;
}

.card-side.is-image {
  width: 450px;
  flex-shrink: 0;
}

.card-side.is-form {
  flex: 1;
  padding: 40px;
}

.login-bg-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.form-wrapper {
  max-width: 360px;
  margin: 0 auto;
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.welcome-text {
  color: #8c8c8c;
  font-size: 14px;
  margin-bottom: 8px;
}

.form-title {
  font-size: 24px;
  font-weight: 600;
  color: #262626;
  margin: 0;
}

.login-form {
  width: 100%;
}

:deep(.auth-primary-btn.ant-btn-primary) {
  background: linear-gradient(135deg, var(--main-600), var(--main-500));
  border-color: var(--main-600);
  color: var(--gray-0);
  box-shadow: 0 8px 20px color-mix(in srgb, var(--main-700) 25%, transparent);
}

:deep(.auth-primary-btn.ant-btn-primary:hover),
:deep(.auth-primary-btn.ant-btn-primary:focus) {
  background: linear-gradient(135deg, var(--main-700), var(--main-600));
  border-color: var(--main-700);
  color: var(--gray-0);
}

:deep(.auth-primary-btn.ant-btn-primary:active) {
  background: linear-gradient(135deg, var(--main-800), var(--main-700));
  border-color: var(--main-800);
  color: var(--gray-0);
}

:deep(.auth-primary-btn.ant-btn-primary:disabled),
:deep(.auth-primary-btn.ant-btn-primary[disabled]) {
  background: var(--main-200);
  border-color: var(--main-200);
  color: var(--main-700);
  box-shadow: none;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.login-options a {
  color: var(--main-600);
  cursor: pointer;
}

.login-options a:hover {
  color: var(--main-700);
}

@media (max-width: 768px) {
  .login-card {
    flex-direction: column;
  }

  .card-side.is-image {
    width: 100%;
    height: 200px;
  }

  .card-side.is-form {
    padding: 24px;
  }
}
</style>
