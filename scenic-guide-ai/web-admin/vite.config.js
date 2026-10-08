import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// base: 生产构建部署在子路径 /admin/ 下（dp.lucky4u.online/admin），
// 本地开发仍用根路径 '/'，这样 dev 代理和运行都不受影响。
export default defineConfig(({ mode }) => ({
  base: mode === 'production' ? '/admin/' : '/',
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  server: {
    port: 5175,
    proxy: {
      // 景点 & 配置 API → Python 后端
      '/api/scenic': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      '/api/config': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // 管理后台全部接口 → Python 后端
      '/api/admin': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // 景点图片（Python 后端直接挂载本地图片目录）
      '/spot-images': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      // SadTalker 服务代理
      '/sadtalker-api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/sadtalker-api/, '')
      },
      // MuseTalk 服务代理 (端口 8003)
      '/musetalk-api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/musetalk-api/, '')
      },
      // Wav2Lip 服务代理 (端口 8004)
      '/wav2lip-api': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/wav2lip-api/, '')
      },
      // SadTalker 上传的头像静态文件
      '/avatar-images': {
        target: 'http://localhost:8001',
        changeOrigin: true
      },
      // 已生成的待机视频（由 Python 后端托管）
      '/sadtalker-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // MuseTalk 视频输出
      '/musetalk-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // Wav2Lip 视频输出
      '/wav2lip-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // 引擎基础照片（avatars 静态目录）
      '/sadtalker-avatars': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      '/musetalk-avatars': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      '/wav2lip-avatars': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // Python TTS/AI 服务代理（统一入口）
      '/tts-api': {
        target: 'http://localhost:8016',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/tts-api/, '/api')
      }
    }
  }
}))
