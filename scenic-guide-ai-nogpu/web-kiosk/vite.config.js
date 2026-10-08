import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// no-GPU 版本：TTS-only，无视频引擎。生产构建部署在子路径 /kiosk/ 下
// 移除 crossorigin 属性，避免 nginx 未配置 CORS 头时浏览器泛化
// 脚本错误为 "Script error."，遮蔽真实报错信息。
function removeCrossorigin() {
  return {
    name: 'remove-crossorigin',
    transformIndexHtml(html) {
      return html.replace(/\s+crossorigin(\s*=\s*["'][^"']*["'])?/g, '')
    }
  }
}

export default defineConfig(({ mode }) => ({
  base: mode === 'production' ? '/kiosk/' : '/',
  plugins: [vue(), removeCrossorigin()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  server: {
    port: 5176,  // no-GPU 独立端口，与 GPU 版本 (5174) 隔离
    proxy: {
      // Python AI 服务
      '/api': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // Python AI 静态文件（TTS音频等）
      '/static': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // 图片服务
      '/spot-images': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
    }
  }
}))
