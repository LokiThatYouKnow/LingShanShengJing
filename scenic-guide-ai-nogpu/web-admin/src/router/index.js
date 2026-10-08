import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../views/layout/AdminLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/DashboardView.vue'),
        meta: { title: '数据大屏', icon: 'DataBoard', requiresAuth: true }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/knowledge/KnowledgeView.vue'),
        meta: { title: '知识库管理', icon: 'Document', requiresAuth: true }
      },
      {
        path: 'avatar',
        name: 'Avatar',
        component: () => import('../views/avatar/AvatarView.vue'),
        meta: { title: '数字人配置', icon: 'User', requiresAuth: true }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/analytics/AnalyticsView.vue'),
        meta: { title: '游客分析', icon: 'TrendCharts', requiresAuth: true }
      },
      {
        path: 'scenic',
        name: 'Scenic',
        component: () => import('../views/scenic/ScenicView.vue'),
        meta: { title: '景点管理', icon: 'MapLocation', requiresAuth: true }
      },
      {
        path: 'map-coordinates',
        name: 'MapCoordinates',
        component: () => import('../views/scenic/MapCoordinateView.vue'),
        meta: { title: '坐标点设置', icon: 'Location', requiresAuth: true }
      },
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('../views/UserManageView.vue'),
        meta: { title: '员工管理', icon: 'UserFilled', requiresAuth: true, requiresSuperAdmin: true }
      },
      {
        path: 'complaints',
        name: 'Complaints',
        component: () => import('../views/complaints/ComplaintsView.vue'),
        meta: { title: '投诉与建议', icon: 'ChatDotRound', requiresAuth: true }
      },
      {
        path: 'tourists',
        name: 'Tourists',
        component: () => import('../views/tourists/TouristsView.vue'),
        meta: { title: '游客管理', icon: 'Avatar', requiresAuth: true }
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue')
  }
]

const router = createRouter({
  // import.meta.env.BASE_URL 由 vite base 提供：生产为 '/admin/'，开发为 '/'
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  const role = localStorage.getItem('admin_role')

  if (to.meta.requiresAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (to.name === 'Login' && token) {
    next({ path: '/' })
    return
  }

  // 超管专属路由：普通管理员无权访问
  if (to.meta.requiresSuperAdmin && role !== 'super_admin') {
    next({ path: '/dashboard' })
    return
  }

  next()
})

export default router
