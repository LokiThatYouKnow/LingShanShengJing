<template>
  <div v-if="checking" style="height:100vh;display:flex;align-items:center;justify-content:center;font-size:16px;color:#999;">
    正在验证身份...
  </div>
  <router-view v-else />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { adminApi } from '@/api'

// BASE 用于硬跳转（window.location.href），ROUTE_LOGIN 用于 Vue Router 路由匹配
// createWebHistory('/admin/') 下 route.path 不含 base 前缀（如 /login，不是 /admin/login）
const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
const FULL_LOGIN_PATH = BASE + '/login'   // 完整 URL 路径，给 window.location.href 用
const ROUTE_LOGIN = '/login'              // Vue Router 路径（不含 base），给 route.path 比较用

const router = useRouter()
const route = useRoute()
const checking = ref(true)

onMounted(async () => {
  const token = localStorage.getItem('admin_token')
  const isLoginPage = route.path === ROUTE_LOGIN

  if (!token && !isLoginPage) {
    // 没有 token，直接跳登录
    router.replace(ROUTE_LOGIN + '?redirect=' + encodeURIComponent(route.fullPath))
    checking.value = false
    return
  }

  if (token && !isLoginPage) {
    // 有 token，向后端验证是否有效
    try {
      await adminApi.getMe()
      checking.value = false
    } catch (err) {
      // 只有 Spring Boot 返回 401 时才踢到登录页
      // 网络错误或其他状态码不清除 token（避免误踢）
      console.error('[App] token 校验失败:', err?.response?.status || '网络错误')
      if (err?.response?.status === 401) {
        localStorage.removeItem('admin_token')
        localStorage.removeItem('python_token')
        router.replace(ROUTE_LOGIN + '?redirect=' + encodeURIComponent(route.fullPath))
      }
      checking.value = false
    }
  } else {
    checking.value = false
  }
})
</script>

<style>
html, body, #app {
  height: 100%;
  overflow: hidden;
}
</style>
