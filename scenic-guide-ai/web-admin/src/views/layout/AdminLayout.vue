<template>
  <el-container class="admin-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo-area">
        <div class="logo-icon">🏔️</div>
        <transition name="fade-text">
          <span v-if="!isCollapsed" class="logo-text">景区智慧导览</span>
        </transition>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        background-color="#001529"
        text-color="rgba(255,255,255,0.65)"
        active-text-color="#409eff"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>数据大屏</template>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Document /></el-icon>
          <template #title>知识库管理</template>
        </el-menu-item>
        <el-menu-item index="/avatar">
          <el-icon><User /></el-icon>
          <template #title>数字人配置</template>
        </el-menu-item>
        <el-menu-item index="/analytics">
          <el-icon><TrendCharts /></el-icon>
          <template #title>游客分析</template>
        </el-menu-item>
        <el-menu-item index="/scenic">
          <el-icon><MapLocation /></el-icon>
          <template #title>景点管理</template>
        </el-menu-item>
        <el-menu-item index="/map-coordinates">
          <el-icon><Location /></el-icon>
          <template #title>坐标点设置</template>
        </el-menu-item>
        <!-- 仅超级管理员可见 -->
        <el-menu-item v-if="isSuperAdmin" index="/users">
          <el-icon><UserFilled /></el-icon>
          <template #title>员工管理</template>
        </el-menu-item>
        <el-menu-item index="/complaints">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>投诉与建议</template>
        </el-menu-item>
        <el-menu-item index="/tourists">
          <el-icon><Avatar /></el-icon>
          <template #title>游客管理</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <button class="collapse-btn" @click="isCollapsed = !isCollapsed">
          <el-icon><ArrowLeft v-if="!isCollapsed" /><ArrowRight v-else /></el-icon>
        </button>
      </div>
    </el-aside>

    <!-- 右侧主区 -->
    <el-container class="main-container">
      <!-- 顶部栏 -->
      <el-header class="admin-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-badge :value="alertCount" :hidden="alertCount === 0">
            <el-button circle :icon="Bell" @click="showAlerts = true" />
          </el-badge>
          <el-divider direction="vertical" />
          <el-tag v-if="isSuperAdmin" type="danger" size="small" class="role-tag">超管</el-tag>
          <el-tag v-else type="info" size="small" class="role-tag">管理员</el-tag>
          <span class="admin-name">{{ adminUsername || '管理员' }}</span>
          <el-avatar :size="32" src="" class="admin-avatar">{{ (adminUsername || 'A')[0].toUpperCase() }}</el-avatar>
          <el-button text @click="logout">退出</el-button>
        </div>
      </el-header>

      <!-- 主内容（keep-alive 缓存各板块状态） -->
      <el-main class="admin-main">
        <router-view v-slot="{ Component }">
          <keep-alive :include="['DashboardView','AvatarView','AnalyticsView','KnowledgeView','ScenicView','MapCoordinateView','UserManageView','ComplaintsView','TouristsView']">
            <component :is="Component" :key="$route.path" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Bell, ArrowLeft, ArrowRight, DataBoard, Document,
  User, TrendCharts, MapLocation, Location, UserFilled, ChatDotRound, Avatar
} from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const route = useRoute()
const router = useRouter()
const isCollapsed = ref(false)
const showAlerts = ref(false)
const alertCount = ref(0)

// 从 localStorage 读取角色和用户名（登录时写入）
const adminRole = ref(localStorage.getItem('admin_role') || '')
const adminUsername = ref(localStorage.getItem('admin_username') || '')
const isSuperAdmin = computed(() => adminRole.value === 'super_admin')

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => {
  const map = {
    '/dashboard': '数据大屏',
    '/knowledge': '知识库管理',
    '/avatar': '数字人配置',
    '/analytics': '游客分析',
    '/scenic': '景点管理',
    '/map-coordinates': '坐标点设置',
    '/users': '员工管理',
    '/complaints': '投诉与建议',
    '/tourists': '游客管理'
  }
  return map[route.path] || '首页'
})

// 挂载时验证 token 有效性，并刷新角色信息
onMounted(async () => {
  const token = localStorage.getItem('admin_token')
  if (!token) {
    router.replace('/login')
    return
  }
  try {
    const res = await adminApi.getMe()
    const me = res?.data || res
    if (me?.role) {
      adminRole.value = me.role
      localStorage.setItem('admin_role', me.role)
    }
    if (me?.username) {
      adminUsername.value = me.username
      localStorage.setItem('admin_username', me.username)
    }
    // 如果当前是普通管理员却试图访问员工管理页，踢回首页
    if (!isSuperAdmin.value && route.path === '/users') {
      router.replace('/dashboard')
    }
  } catch (err) {
    console.error('[Auth] token 校验失败:', err?.response?.status || '网络错误')
    // 只有 sbApi（Spring Boot）返回的 401 才清除 token
    // Python 后端接口的 401 不影响管理员登录状态
    if (err?.response?.status === 401) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_role')
      localStorage.removeItem('admin_username')
      router.replace('/login')
    }
  }
})

function logout() {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('python_token')
  localStorage.removeItem('admin_role')
  localStorage.removeItem('admin_username')
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.admin-layout { height: 100vh; overflow: hidden; }

.sidebar {
  background: #001529;
  transition: width 0.25s ease;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 2px 0 8px rgba(0,0,0,0.15);
}

.logo-area {
  height: 60px;
  display: flex; align-items: center; gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  overflow: hidden; white-space: nowrap;
}
.logo-icon { font-size: 24px; flex-shrink: 0; }
.logo-text { color: #fff; font-size: 16px; font-weight: 700; }
.fade-text-enter-active, .fade-text-leave-active { transition: opacity 0.2s; }
.fade-text-enter-from, .fade-text-leave-to { opacity: 0; }

.sidebar-menu { border-right: none; flex: 1; overflow-y: auto; }
.sidebar-menu::-webkit-scrollbar { display: none; }

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
  display: flex; justify-content: flex-end;
}
.collapse-btn {
  background: rgba(255,255,255,0.08); border: none; color: rgba(255,255,255,0.65);
  width: 32px; height: 32px; border-radius: 6px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 14px;
}
.collapse-btn:hover { background: rgba(255,255,255,0.15); }

.main-container { overflow: hidden; }

.admin-header {
  height: 60px !important;
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.header-right { display: flex; align-items: center; gap: 12px; }
.role-tag { flex-shrink: 0; }
.admin-name { font-size: 14px; color: #333; }
.admin-avatar { background: #409eff; color: #fff; font-weight: 600; flex-shrink: 0; }

.admin-main {
  background: #f0f2f5;
  overflow-y: auto;
  padding: 20px;
  height: calc(100vh - 60px);
}
.admin-main::-webkit-scrollbar { width: 6px; }
.admin-main::-webkit-scrollbar-track { background: #f0f2f5; }
.admin-main::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 3px; }
</style>
