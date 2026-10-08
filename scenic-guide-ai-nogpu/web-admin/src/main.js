import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElIcons from '@element-plus/icons-vue'
import router from './router'
import App from './App.vue'
import './styles/global.css'

// ===== 子路径部署适配 =====
// 生产环境部署在 /admin/ 下。所有以 "/" 开头的 fetch 请求（如 /tts-api、/sadtalker-api）
// 自动加上部署基路径，使其变成 /admin/tts-api 等，交给容器 nginx 按命名空间转发。
// 开发环境 BASE_URL 为 '/'，此处不做任何改动。
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

const app = createApp(App)

// 注册所有图标
Object.entries(ElIcons).forEach(([name, comp]) => {
  app.component(name, comp)
})

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
