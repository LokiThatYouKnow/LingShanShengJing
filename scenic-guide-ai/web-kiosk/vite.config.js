import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// base: 生产构建部署在子路径 /kiosk/ 下（dp.lucky4u.online/kiosk），
// 本地开发仍用根路径 '/'，dev 代理与运行不受影响。
export default defineConfig(({ mode }) => ({
  base: mode === 'production' ? '/kiosk/' : '/',
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  server: {
    port: 5174,
    proxy: {
      // Python AI 服务（Voice TTS/STT, Chat, Scenic, Scene分析等）
      // 注意：这些接口在 Python FastAPI 后端(8000)注册，前端统一调用 /api/*
      '/api': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // Python AI 静态文件（TTS音频等）
      '/static': {
        target: 'http://localhost:8016',
        changeOrigin: true
      },
      // Python AI 服务 (Voice TTS/STT, Chat, SadTalker等)
      '/voice': {
        target: 'http://localhost:8016',
        changeOrigin: true,
        rewrite: (path) => '/api' + path
      },
      '/chat': {
        target: 'http://localhost:8016',
        changeOrigin: true,
        rewrite: (path) => '/api' + path
      },
      // 预生成数字人视频（Python 后端托管，独立于各引擎服务）
      // 注意：必须放在 /sadtalker 前面，否则 /sadtalker 会抢先匹配 /sadtalker-videos 路径
      '/sadtalker-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      '/musetalk-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      '/wav2lip-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      // 引擎基础照片（avatars 静态目录，待机视频缺失时降级显示）
      '/sadtalker-avatars': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      '/musetalk-avatars': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      '/wav2lip-avatars': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      // 对话生成的视频专用目录
      '/dialogue-videos': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      '/sadtalker': {
        target: 'http://localhost:8016',
        changeOrigin: true,
        rewrite: (path) => '/api' + path
      },
      // 图片服务（Python 后端直接挂载 d:/TalkingV2/图片 目录）
      '/spot-images': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
      // SadTalker 视频输出（仅开发时使用，需 SadTalker 服务在线）
      '/output': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // SadTalker 视频生成接口
      '/idle-videos': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/generate-idle': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/generate-opening': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // AI换装接口（头像上传/确认/当前头像）
      '/avatar': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/avatar-images': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // MuseTalk 和 Wav2Lip 服务代理
      '/musetalk-api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/musetalk-api/, '')
      },
      '/wav2lip-api': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/wav2lip-api/, '')
      },
    }
  }
}))
