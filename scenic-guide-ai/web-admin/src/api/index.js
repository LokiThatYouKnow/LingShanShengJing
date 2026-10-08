import axios from 'axios'

// 子路径部署基路径：生产为 '/admin'，开发为 ''（根路径）
const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')

const api = axios.create({
  baseURL: BASE + '/tts-api',  // 代理到 Python 后端(8000)；/admin/api 代理到 SpringBoot(8080)
  timeout: 30000
})

// 用于调用非 /api 前缀的外部服务（如 SadTalker、TTS）
const rawApi = axios.create({
  baseURL: BASE,   // 生产下 '/sadtalker-api/...' → '/admin/sadtalker-api/...'
  timeout: 30000
})

// ========== 统一的 401 处理 ==========
// 任何需要认证的 API 返回 401 时，清除 token 并跳转登录页
function handleAuthError(error) {
  if (error.response?.status === 401) {
    // 仅对需要认证的请求（带了 token 的）才触发跳转
    const hadToken = error.config?.headers?.['Authorization']
    if (hadToken) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('python_token')
      const loginPath = BASE + '/login'
    if (window.location.pathname !== loginPath) {
      window.location.href = loginPath
    }
    }
  }
}

// 请求拦截（api）—— 使用 python_token（Python 后端的 JWT，与 Spring Boot 的 admin_token 独立）
api.interceptors.request.use(config => {
  const token = localStorage.getItem('python_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

// 响应拦截（api）
api.interceptors.response.use(
  response => response.data,
  error => {
    handleAuthError(error)
    return Promise.reject(error)
  }
)

// 响应拦截（rawApi）——同样处理 401
rawApi.interceptors.response.use(
  response => response.data,
  error => {
    handleAuthError(error)
    return Promise.reject(error)
  }
)

// 专门用来调用 Spring Boot 的 axios 实例（/admin/api 代理到 8080）
const sbApi = axios.create({
  baseURL: BASE + '/api',
  timeout: 30000
})
// 请求拦截 - 带 token
sbApi.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})
// 响应拦截
sbApi.interceptors.response.use(
  response => response.data,
  error => {
    handleAuthError(error)
    return Promise.reject(error)
  }
)

export const adminApi = {
  // ===== 认证（Python 后端，OAuth2PasswordRequestForm）=====
  // Python 后端使用 OAuth2PasswordRequestForm（form-urlencoded），不是 JSON
  login: (username, password) => api.post('/admin/auth/login',
    new URLSearchParams({ username, password }).toString(),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  ),
  getMe: () => api.get('/admin/auth/me'),
  loginPython: (username, password) => api.post('/admin/auth/login',
    new URLSearchParams({ username, password }).toString(),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  ),

  // ===== 员工管理（仅超管，Python 后端 JWT）=====
  getUsers: () => api.get('/admin/users/list'),
  createUser: (data) => api.post('/admin/users/create', data),
  updateUser: (id, data) => api.put(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  resetPassword: (id, password) => api.post(`/admin/users/${id}/reset-password`, { password }),

  // ===== 知识库 =====
  // 后端路由: GET /admin/knowledge/list, POST /admin/knowledge/upload, DELETE /admin/knowledge/{id}
  getDocuments: (params) => api.get('/admin/knowledge/list', { params }),
  uploadDocument: (formData) => api.post('/admin/knowledge/upload', formData, {
    // 不设 Content-Type，让浏览器自动加 boundary
  }),
  deleteDocument: (id) => api.delete(`/admin/knowledge/${id}`),
  addTextKnowledge: (data) => api.post('/admin/knowledge/text', null, { params: data }),
  searchTest: (data) => api.post('/admin/knowledge/search-test', null, { params: data }),
  reindexDocument: (id) => api.post(`/admin/knowledge/${id}/reindex`),
  getDocumentContent: (id) => api.get(`/admin/knowledge/${id}/content`),

  // ===== FAQ =====
  // 后端路由: GET /admin/faq/list, POST /admin/faq/create, PUT /admin/faq/{id}, DELETE /admin/faq/{id}
  getFaqs: (params) => api.get('/admin/faq/list', { params }),
  saveFaq: (data) => api.post('/admin/faq/create', data),
  updateFaq: (id, data) => api.put(`/admin/faq/${id}`, data),
  deleteFaq: (id) => api.delete(`/admin/faq/${id}`),

  // ===== 数字人配置 =====
  // 后端路由: GET /admin/avatar/list, PUT /admin/avatar/{id}
  getAvatarConfig: () => api.get('/admin/avatar/list'),
  updateAvatar: (id, data) => api.put(`/admin/avatar/${id}`, data),
  uploadAvatarImage: (id, formData) => api.post(`/admin/avatar/${id}/upload-image`, formData, {
    // 不设 Content-Type，让浏览器自动加 boundary
  }),
  // 兼容旧调用 saveAvatarConfig -> 保存到第一个数字人(id=1)
  saveAvatarConfig: (data) => api.put('/admin/avatar/1', data),

  // ===== 数字人形象变更（调用 SadTalker 服务）======
  // 注意：使用 rawApi（无 baseURL），因为 SadTalker 路由以 /sadtalker-api 开头，不是 /api
  // 上传形象图片
  uploadAvatarImageForChange: (formData) => rawApi.post('/sadtalker-api/avatar/upload-image', formData, {
    // 不设 Content-Type，让浏览器自动加 boundary
  }),
  // 确认形象变更并批量生成视频（所有已开启引擎的开场白 + SadTalker 待机视频）
  // 耗时估算：单个引擎 ~30s~15min，全引擎 ~15min+，超时设为 1 小时
  confirmAvatarChange: (formData) => api.post('/admin/avatar/confirm-change', formData, {
    // 不设 Content-Type，让浏览器自动加 boundary,
    timeout: 60 * 60 * 1000  // 1 小时
  }),
  // 获取当前形象
  getCurrentAvatar: () => rawApi.get('/sadtalker-api/avatar/current'),
  // 获取 SadTalker 服务状态
  getAvatarStatus: () => rawApi.get('/sadtalker-api/status'),

  // ===== 数据分析 =====
  // 后端路由: /admin/analytics/overview, /admin/analytics/emotion-trend, /admin/analytics/hot-questions, /admin/analytics/daily-stats
  getDashboard: (params) => api.get('/admin/analytics/overview', { params }),
  getEmotionTrend: (params) => api.get('/admin/analytics/emotion-trend', { params }),
  getHotQuestions: (params) => api.get('/admin/analytics/hot-questions', { params }),
  getDailyStats: (params) => api.get('/admin/analytics/daily-stats', { params }),
  // 新增的分析接口
  getHourlyDistribution: (params) => api.get('/admin/analytics/hourly-distribution', { params }),
  getRecentMessages: (params) => api.get('/admin/analytics/recent-messages', { params }),
  // 兼容旧调用名
  getSentimentTrend: (params) => api.get('/admin/analytics/emotion-trend', { params }),
  getChatLogs: (params) => api.get('/admin/analytics/daily-stats', { params }),
  exportReport: (params) => api.get('/admin/analytics/daily-stats', { params, responseType: 'blob' }),

  // ===== 评论管理 =====
  getReviews: (params) => api.get('/admin/reviews/list', { params }),
  deleteReview: (id) => api.delete(`/admin/reviews/${id}`),

  // ===== 投诉建议管理 =====
  getComplaints: (params) => api.get('/admin/complaints/list', { params }),
  updateComplaint: (id, data) => api.post(`/admin/complaints/${id}/update`, data),
  deleteComplaint: (id) => api.delete(`/admin/complaints/${id}`),
  getComplaintsAnalytics: (params) => api.get('/admin/complaints/analytics', { params }),

  // ===== 游客管理 =====
  getTourists: (params) => api.get('/admin/tourists/list', { params }),
  toggleTouristStatus: (id) => api.put(`/admin/tourists/${id}`),
  deleteTourist: (id) => api.delete(`/admin/tourists/${id}`),

  // ===== 引擎开关管理 =====
  getEngineConfig: () => api.get('/admin/avatar/engine-config'),
  toggleEngine: (data) => api.post('/admin/avatar/engine-toggle', data),

  // ===== 视频设置（多引擎） =====
  getCurrentAvatarUuid: () => api.get('/admin/avatar/current-uuid'),
  getOpeningVideoStatus: () => api.get('/admin/avatar/opening-video-status'),
  // 视频生成耗时较长，超时设为 5 分钟
  generateOpeningVideo: (data) => api.post('/admin/avatar/generate-opening-video', data, { timeout: 5 * 60 * 1000 }),
  // SadTalker 待机视频批量生成（约需 5~10 分钟）
  generateIdleVideos: (data) => api.post('/admin/avatar/generate-idle-videos', data, { timeout: 15 * 60 * 1000 }),

  // ===== 引擎基础形象照片 =====
  getEngineBasePhotos: () => api.get('/admin/avatar/engine-base-photos'),
  uploadEngineBasePhoto: (formData) => api.post('/admin/avatar/engine-base-photo', formData, {
    // 不设 Content-Type，让浏览器自动加 boundary
  }),

  // ===== 系统能力检测 =====
  getSystemCapabilities: () => api.get('/system/capabilities'),

  // ===== AI 图像生成（豆包 Seedream） =====
  getAiImageConfig: () => api.get('/admin/ai-image/config'),
  generateAiImage: (data) => api.post('/admin/ai-image/generate', data, { timeout: 2 * 60 * 1000 }),
  updateAiImageToken: (data) => api.post('/admin/ai-image/token', data),
}

export default api
