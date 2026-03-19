<script setup>
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import { onMounted } from 'vue'

const userStore = useUserStore()
const themeStore = useThemeStore()

onMounted(async () => {
  if (userStore.isLoggedIn) {
    // await agentStore.initialize()
  }
})
</script>
<template>
  <a-config-provider :theme="themeStore.currentTheme" :locale="zhCN">
    <router-view />
  </a-config-provider>
</template>
