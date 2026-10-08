import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import KioskView from './views/KioskView.vue'

// ===== 子路径部署适配 =====
// 生产环境部署在 /kiosk/ 下。所有以 "/" 开头的 fetch 请求（如 /api、/avatar、/generate-opening）
// 自动加上部署基路径 → /kiosk/api 等，交给容器 nginx 按命名空间转发。
// 开发环境 BASE_URL 为 '/'，此处不改动。<img>/<video> 的资源路径（/spot-images、/sadtalker-videos）
// 不是 fetch，保持根路径，由宿主 nginx 直接转发到对应后端。
const __BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
if (__BASE) {
  const __origFetch = window.fetch.bind(window)
  window.fetch = (input, init) => {
    if (typeof input === 'string' && input.startsWith('/') && !input.startsWith('//') && !input.startsWith(__BASE + '/')) {
      input = __BASE + input
    }
    return __origFetch(input, init)
  }
}

// 全局错误处理器
let __errorCount = 0
window.addEventListener('error', (event) => {
  __errorCount++
  // 捕获所有可诊断的字段
  const parts = []
  parts.push(`#${__errorCount} type=${event.type}`)
  if (event.message) parts.push(`message="${event.message}"`)
  if (event.filename) parts.push(`file="${event.filename}"`)
  if (event.lineno != null) parts.push(`line=${event.lineno}:${event.colno}`)
  if (event.error) {
    parts.push(`error.name=${event.error.name}`)
    parts.push(`error.message=${event.error.message}`)
    parts.push(`stack=${event.error.stack?.substring(0, 500)}`)
  }
  if (event.target) {
    const t = event.target
    parts.push(`target.tag=${t.tagName || '?'}`)
    if (t.src) parts.push(`target.src=${t.src}`)
    if (t.outerHTML) parts.push(`target.html=${t.outerHTML.substring(0, 200)}`)
  }
  // 仅忽略无法诊断的跨域 Script error（连续出现时静默）
  if (event.message === 'Script error.' && !event.filename && !event.error) {
    if (__errorCount <= 3) {
      console.warn('[Kiosk] 检测到跨域脚本错误（已静默），可能是第三方资源加载失败')
    }
    return // 不展示红色横幅
  }
  showError('window.error: ' + parts.join(' | '))
})
window.addEventListener('unhandledrejection', (event) => {
  showError('Promise rejection: ' + (event.reason?.stack || event.reason))
})
function showError(msg) {
  console.error('[调试]', msg)
  const div = document.getElementById('__debug_error__') || document.createElement('div')
  div.id = '__debug_error__'
  div.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#ff4444;color:#fff;padding:16px;z-index:99999;font-size:13px;white-space:pre-wrap;max-height:60vh;overflow:auto;'
  div.textContent += msg + '\n---\n'
  document.body.appendChild(div)
}

const router = createRouter({
  // import.meta.env.BASE_URL：生产为 '/kiosk/'，开发为 '/'
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: KioskView },
    { path: '/kiosk', component: KioskView }
  ]
})

const pinia = createPinia()
const app = createApp(App)

// Vue内部错误也捕获
app.config.errorHandler = (err, vm, info) => {
  showError(`Vue Error [${info}]: ${err?.stack || err}`)
}
app.config.warnHandler = (msg, vm, trace) => {
  console.warn('[Vue Warn]', msg, trace)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
