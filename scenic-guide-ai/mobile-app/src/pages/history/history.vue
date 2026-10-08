<template>
  <view class="page">
    <view class="header">
      <text class="title">💬 历史对话记录</text>
    </view>

    <view v-if="sessions.length === 0" class="empty">
      <text class="empty-icon">📭</text>
      <text class="empty-text">暂无历史记录</text>
    </view>

    <view v-for="s in sessions" :key="s.session_id" class="session-card" @tap="openSession(s.session_id)">
      <view class="session-header">
        <text class="session-time">{{ formatTime(s.start_time) }}</text>
        <text class="session-platform">{{ platformLabel(s.platform) }}</text>
      </view>
      <text class="session-count">共 {{ s.message_count }} 条对话</text>
    </view>

    <!-- 会话详情弹窗 -->
    <view class="detail-modal" v-if="detailVisible">
      <view class="modal-mask" @tap="detailVisible = false"></view>
      <view class="modal-body">
        <view class="modal-header">
          <text class="modal-title">对话详情</text>
          <text class="modal-close" @tap="detailVisible = false">✕</text>
        </view>
        <scroll-view class="modal-scroll" scroll-y>
          <view v-for="(msg, i) in detailMessages" :key="i" class="d-msg" :class="msg.role">
            <text class="d-role">{{ msg.role === 'user' ? '您' : '小灵' }}</text>
            <text class="d-content">{{ msg.content }}</text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script>
import { chatApi } from '../../utils/api.js'
export default {
  data() {
    return { sessions: [], detailVisible: false, detailMessages: [] }
  },
  async onShow() {
    const deviceId = uni.getStorageSync('device_id')
    if (deviceId) {
      try {
        const res = await chatApi.getSessions(deviceId)
        this.sessions = res.sessions || []
      } catch (e) {}
    }
  },
  methods: {
    async openSession(sessionId) {
      try {
        const res = await chatApi.getHistory(sessionId)
        this.detailMessages = res.messages || []
        this.detailVisible = true
      } catch (e) {}
    },
    formatTime(t) {
      if (!t) return ''
      return t.replace('T', ' ').substring(0, 16)
    },
    platformLabel(p) {
      const m = { app: '📱 手机', kiosk: '🖥 大屏', web: '💻 网页' }
      return m[p] || p
    }
  }
}
</script>

<style lang="scss">
.page { padding: 16px; background: #f0f7f4; min-height: 100vh; }
.header { padding: 20px 0 16px; }
.title { font-size: 22px; font-weight: 700; color: #1a7a4a; }
.empty { display: flex; flex-direction: column; align-items: center; padding: 60px 0; }
.empty-icon { font-size: 48px; }
.empty-text { font-size: 14px; color: #ccc; margin-top: 12px; }
.session-card {
  background: #fff; border-radius: 14px; padding: 16px; margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.session-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.session-time { font-size: 14px; color: #333; font-weight: 500; }
.session-platform { font-size: 12px; color: #999; }
.session-count { font-size: 13px; color: #666; }
.detail-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000; }
.modal-mask { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); }
.modal-body {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: #fff; border-radius: 20px 20px 0 0;
  max-height: 70vh; display: flex; flex-direction: column;
}
.modal-header {
  padding: 16px 20px; display: flex; justify-content: space-between;
  border-bottom: 1px solid #f0f0f0;
}
.modal-title { font-size: 16px; font-weight: 600; }
.modal-close { font-size: 18px; color: #999; }
.modal-scroll { flex: 1; padding: 16px 20px; }
.d-msg { margin-bottom: 16px; &.user { text-align: right; } }
.d-role { display: block; font-size: 12px; color: #999; margin-bottom: 4px; }
.d-content {
  display: inline-block; max-width: 80%; padding: 10px 14px; border-radius: 12px;
  font-size: 14px; line-height: 1.6;
  .user & { background: linear-gradient(135deg, #1a7a4a, #2d9e5f); color: #fff; }
  .assistant & { background: #f5f5f5; color: #333; }
}
</style>
