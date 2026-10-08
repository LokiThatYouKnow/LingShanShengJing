<template>
  <view class="guide-page">
    <!-- 顶部导航 -->
    <view class="nav-bar">
      <view class="nav-back" @tap="goBack">
        <text class="back-icon">‹</text>
      </view>
      <view class="nav-title">
        <text class="spot-name">{{ spotName }}</text>
        <text class="spot-sub">AI智能讲解</text>
      </view>
      <view class="nav-actions">
        <text class="nav-btn" @tap="shareSpot">分享</text>
      </view>
    </view>

    <!-- 数字人展示区 -->
    <view class="avatar-section">
      <view class="avatar-stage">
        <!-- 背景装饰 -->
        <view class="stage-bg"></view>

        <!-- 数字人视频/动画 -->
        <video
          v-if="avatarVideoUrl"
          :src="avatarVideoUrl"
          class="avatar-video"
          autoplay
          loop
          :muted="false"
          object-fit="contain"
        ></video>
        <view v-else class="avatar-anim">
          <view class="anim-avatar">
            <view class="anim-head">
              <view class="anim-face">
                <view class="anim-eye left" :class="{ blink: blinking }"></view>
                <view class="anim-eye right" :class="{ blink: blinking }"></view>
                <view class="anim-mouth" :class="{ talking: isTalking }"></view>
              </view>
            </view>
            <view class="anim-body"></view>
          </view>
        </view>

        <!-- 音波动效 -->
        <view class="sound-waves" v-if="isTalking">
          <view class="wave-bar" v-for="i in 5" :key="i"></view>
        </view>
      </view>

      <!-- 字幕 -->
      <view class="subtitle-area" v-if="subtitleText">
        <text class="subtitle-text">{{ subtitleText }}</text>
      </view>
    </view>

    <!-- 对话区 -->
    <view class="chat-section">
      <scroll-view
        scroll-y
        class="chat-scroll"
        :scroll-top="scrollTop"
        :scroll-with-animation="true"
        ref="chatRef"
      >
        <!-- 空状态 -->
        <view class="chat-empty" v-if="messages.length === 0">
          <text class="empty-icon">🎙️</text>
          <text class="empty-tip">点击麦克风或输入文字提问</text>
        </view>

        <!-- 消息列表 -->
        <view
          v-for="msg in messages"
          :key="msg.id"
          class="message-item"
          :class="msg.role"
        >
          <view class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</view>
          <view class="msg-bubble">
            <text class="msg-text">{{ msg.content }}</text>
            <text class="msg-time">{{ msg.time }}</text>
          </view>
        </view>

        <!-- 加载中 -->
        <view class="msg-loading" v-if="isLoading">
          <view class="loading-dot" v-for="i in 3" :key="i" :style="{ animationDelay: (i*0.2) + 's' }"></view>
        </view>
      </scroll-view>

      <!-- 快捷问题 -->
      <scroll-view scroll-x class="quick-scroll">
        <view class="quick-list">
          <view
            class="quick-tag"
            v-for="q in quickQuestions"
            :key="q"
            @tap="askQuestion(q)"
          >
            <text>{{ q }}</text>
          </view>
        </view>
      </scroll-view>

      <!-- 输入区 -->
      <view class="input-area">
        <view class="voice-status-bar" v-if="voiceStatus">
          <view class="voice-anim">
            <view class="v-wave" v-for="i in 4" :key="i"></view>
          </view>
          <text class="v-status-text">{{ voiceStatus }}</text>
        </view>

        <view class="input-row">
          <input
            class="text-input"
            v-model="inputText"
            placeholder="输入问题..."
            :disabled="isLoading"
            confirm-type="send"
            @confirm="sendText"
            @focus="onInputFocus"
          />
          <view
            class="voice-btn"
            :class="{ recording: isRecording, loading: isLoading }"
            @touchstart.prevent="startRecording"
            @touchend.prevent="stopRecording"
          >
            <text class="voice-btn-icon">
              {{ isRecording ? '🔴' : isLoading ? '⌛' : '🎤' }}
            </text>
          </view>
          <view class="send-btn" @tap="sendText" v-if="inputText">
            <text class="send-icon">➤</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 景点信息底部卡片 -->
    <view class="spot-info-card" v-if="spotInfo">
      <view class="spot-card-header">
        <text class="spot-icon-big">{{ spotInfo.icon }}</text>
        <view class="spot-card-text">
          <text class="spot-card-name">{{ spotInfo.name }}</text>
          <text class="spot-card-desc">{{ spotInfo.description }}</text>
        </view>
      </view>
      <view class="spot-meta-row">
        <view class="meta-chip">
          <text class="meta-label">开放</text>
          <text class="meta-val">{{ spotInfo.openTime }}</text>
        </view>
        <view class="meta-chip">
          <text class="meta-label">票价</text>
          <text class="meta-val">{{ spotInfo.price }}</text>
        </view>
        <view class="meta-chip">
          <text class="meta-label">距您</text>
          <text class="meta-val">{{ spotInfo.distance }}m</text>
        </view>
      </view>
      <view class="auto-guide-btn" @tap="startAutoGuide">
        <text>🎙️ 开始自动讲解</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      spotName: '灵山大佛',
      spotId: null,
      avatarVideoUrl: '',
      isTalking: false,
      blinking: false,
      isRecording: false,
      isLoading: false,
      inputText: '',
      voiceStatus: '',
      subtitleText: '',
      scrollTop: 0,
      messages: [],
      blinkTimer: null,
      spotInfo: {
        icon: '🗽',
        name: '灵山大佛',
        description: '通高88m，耗铜725吨，灵山胜境核心地标',
        openTime: '08:00-17:00',
        price: '免费',
        distance: 700
      },
      quickQuestions: [
        '请介绍这个景点',
        '有什么历史典故',
        '最佳拍照位置',
        '周边有什么景点',
        '开放时间和票价'
      ],
      recorderManager: null,
      innerAudioContext: null,
      sessionId: ''
    }
  },
  onLoad(options) {
    this.spotId = options.spotId
    this.spotName = options.spotName || '景点讲解'
    this.sessionId = 'guide_' + Date.now()

    // 获取景点信息
    if (options.spotId) {
      this.loadSpotInfo(options.spotId)
    }

    // 自动开始讲解
    setTimeout(() => {
      this.autoIntroduce()
    }, 800)
  },
  onMounted() {
    this.startBlink()
    this.setupRecorder()
  },
  onUnmounted() {
    clearInterval(this.blinkTimer)
    this.innerAudioContext?.destroy()
  },
  methods: {
    startBlink() {
      this.blinkTimer = setInterval(() => {
        this.blinking = true
        setTimeout(() => { this.blinking = false }, 150)
      }, 3000)
    },

    setupRecorder() {
      try {
        this.recorderManager = uni.getRecorderManager()
        this.recorderManager.onStop((res) => {
          this.voiceStatus = '识别中...'
          this.transcribeAudio(res.tempFilePath)
        })
        this.recorderManager.onError((err) => {
          this.voiceStatus = ''
          this.isRecording = false
          uni.showToast({ title: '录音失败', icon: 'none' })
        })
      } catch (e) {}
    },

    loadSpotInfo(spotId) {
      uni.request({
        url: getApp().globalData.apiBase + '/api/scenic/spots/' + spotId,
        success: (res) => {
          if (res.data) {
            this.spotInfo = {
              ...res.data,
              distance: Math.floor(Math.random() * 500 + 50)
            }
            this.spotName = res.data.name
          }
        }
      })
    },

    async autoIntroduce() {
      const intro = `欢迎来到灵山胜境·${this.spotName}！我是您的AI导览助手小灵，请问有什么想了解的吗？`
      await this.speak(intro)
    },

    async startAutoGuide() {
      const query = `请详细介绍${this.spotName}的历史文化背景、主要看点和游览建议`
      await this.processQuery(query)
    },

    async askQuestion(q) {
      await this.processQuery(q)
    },

    async sendText() {
      if (!this.inputText.trim() || this.isLoading) return
      const text = this.inputText.trim()
      this.inputText = ''
      await this.processQuery(text)
    },

    async processQuery(text) {
      this.addMessage('user', text)
      this.scrollToBottom()
      this.isLoading = true

      try {
        const res = await new Promise((resolve, reject) => {
          uni.request({
            url: getApp().globalData.apiBase + '/api/chat/message',
            method: 'POST',
            data: {
              message: text,
              session_id: this.sessionId,
              context: { spot_id: this.spotId, spot_name: this.spotName }
            },
            success: resolve,
            fail: reject,
            timeout: 15000
          })
        })

        const answer = res.data?.answer || res.data?.response || '抱歉，我暂时无法回答这个问题。'
        if (res.data?.avatar_video_url) {
          this.avatarVideoUrl = res.data.avatar_video_url
        }

        this.addMessage('assistant', answer)
        this.scrollToBottom()
        await this.speak(answer)
      } catch (err) {
        this.addMessage('assistant', '网络连接异常，请检查网络后重试。')
        this.scrollToBottom()
      } finally {
        this.isLoading = false
      }
    },

    addMessage(role, content) {
      this.messages.push({
        id: Date.now() + Math.random(),
        role,
        content,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      })
    },

    async speak(text) {
      this.subtitleText = text
      this.isTalking = true

      try {
        const res = await new Promise((resolve, reject) => {
          uni.request({
            url: getApp().globalData.apiBase + '/api/voice/tts',
            method: 'POST',
            data: { text, voice: 'female_1', speed: 1.0 },
            responseType: 'arraybuffer',
            success: resolve,
            fail: reject,
            timeout: 10000
          })
        })

        const base64 = uni.arrayBufferToBase64(res.data)
        const audioCtx = uni.createInnerAudioContext()
        this.innerAudioContext = audioCtx
        // 需要先保存到临时文件
        const fs = uni.getFileSystemManager()
        const tmpPath = `${wx.env.USER_DATA_PATH}/tts_${Date.now()}.mp3`
        fs.writeFile({ filePath: tmpPath, data: res.data, encoding: 'binary' })
        audioCtx.src = tmpPath
        audioCtx.play()
        audioCtx.onEnded(() => {
          this.isTalking = false
          this.subtitleText = ''
        })
      } catch {
        // 仅展示字幕
        const duration = Math.min(text.length * 150, 6000)
        setTimeout(() => {
          this.isTalking = false
          this.subtitleText = ''
        }, duration)
      }
    },

    startRecording() {
      if (this.isRecording) return
      uni.authorize({
        scope: 'scope.record',
        success: () => {
          this.isRecording = true
          this.voiceStatus = '录音中，松开识别...'
          this.recorderManager?.start({
            duration: 30000,
            sampleRate: 16000,
            numberOfChannels: 1,
            encodeBitRate: 96000,
            format: 'mp3'
          })
        },
        fail: () => {
          uni.showToast({ title: '请授权麦克风权限', icon: 'none' })
        }
      })
    },

    stopRecording() {
      if (!this.isRecording) return
      this.isRecording = false
      this.recorderManager?.stop()
    },

    async transcribeAudio(filePath) {
      try {
        const uploadRes = await new Promise((resolve, reject) => {
          uni.uploadFile({
            url: getApp().globalData.apiBase + '/api/voice/transcribe',
            filePath,
            name: 'audio',
            formData: { language: 'zh' },
            success: resolve,
            fail: reject
          })
        })
        const data = JSON.parse(uploadRes.data)
        this.voiceStatus = ''
        if (data.text) {
          // 语音识别后仅填入输入框，由用户确认后手动发送
          this.inputText = data.text
          uni.showToast({ title: '识别完成，请确认后发送', icon: 'none', duration: 2000 })
        } else {
          uni.showToast({ title: '未能识别语音内容', icon: 'none' })
        }
      } catch {
        this.voiceStatus = ''
        uni.showToast({ title: '语音识别失败', icon: 'none' })
      }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        this.scrollTop = 99999
      })
    },

    onInputFocus() {
      this.scrollToBottom()
    },

    goBack() {
      uni.navigateBack()
    },

    shareSpot() {
      uni.share({
        provider: 'weixin',
        scene: 'WXSceneSession',
        type: 0,
        title: `我在${this.spotName}，AI导览超棒！`,
        summary: `正在使用AI智慧导览游览${this.spotName}`
      }).catch(() => {
        uni.showToast({ title: '分享功能需要真机', icon: 'none' })
      })
    }
  }
}
</script>

<style scoped>
.guide-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a1628;
  color: #fff;
  overflow: hidden;
}

.nav-bar {
  display: flex; align-items: center;
  padding: 44rpx 24rpx 16rpx;
  background: rgba(0,0,0,0.3);
}
.nav-back { width: 60rpx; height: 60rpx; display: flex; align-items: center; justify-content: center; }
.back-icon { font-size: 48rpx; color: #fff; font-weight: 300; }
.nav-title { flex: 1; text-align: center; }
.spot-name { display: block; font-size: 32rpx; font-weight: 600; }
.spot-sub { display: block; font-size: 22rpx; color: rgba(255,255,255,0.5); margin-top: 2rpx; }
.nav-actions { width: 80rpx; text-align: right; }
.nav-btn { font-size: 26rpx; color: rgba(255,255,255,0.7); }

.avatar-section {
  flex-shrink: 0;
  height: 380rpx;
  position: relative;
}

.avatar-stage {
  height: 320rpx;
  background: radial-gradient(ellipse at center, rgba(64,120,255,0.2) 0%, transparent 70%);
  display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
}
.stage-bg {
  position: absolute; inset: 0;
  background: radial-gradient(circle at 50% 100%, rgba(64,120,255,0.15), transparent 50%);
}
.avatar-video {
  width: 100%; height: 100%; object-fit: contain;
}
.avatar-anim { position: relative; z-index: 1; }
.anim-avatar { display: flex; flex-direction: column; align-items: center; }
.anim-head {
  width: 120rpx; height: 140rpx; background: #ffd4a8;
  border-radius: 50% 50% 45% 45%;
  display: flex; align-items: center; justify-content: center;
}
.anim-face { position: relative; width: 80rpx; height: 80rpx; }
.anim-eye {
  position: absolute; width: 16rpx; height: 20rpx;
  background: #2d1b00; border-radius: 50%; top: 20rpx;
}
.anim-eye.left { left: 10rpx; }
.anim-eye.right { right: 10rpx; }
.anim-eye.blink { height: 2rpx; top: 30rpx; }
.anim-mouth {
  position: absolute; bottom: 10rpx; left: 50%; transform: translateX(-50%);
  width: 30rpx; height: 10rpx; border-bottom: 3rpx solid #c0392b;
  border-radius: 0 0 50% 50%;
}
.anim-mouth.talking { animation: mobileTalk 0.15s infinite alternate; }
@keyframes mobileTalk { from { height: 6rpx; } to { height: 20rpx; } }
.anim-body {
  width: 100rpx; height: 110rpx; background: #1a6aff;
  border-radius: 10rpx 10rpx 20rpx 20rpx;
}

.sound-waves {
  position: absolute; bottom: 10rpx; left: 50%; transform: translateX(-50%);
  display: flex; align-items: flex-end; gap: 6rpx; height: 50rpx;
}
.wave-bar {
  width: 6rpx; background: rgba(74,222,128,0.8); border-radius: 3rpx;
  animation: waveBounce 0.8s ease-in-out infinite alternate;
}
.wave-bar:nth-child(1) { height: 20rpx; }
.wave-bar:nth-child(2) { height: 36rpx; animation-delay: 0.1s; }
.wave-bar:nth-child(3) { height: 50rpx; animation-delay: 0.2s; }
.wave-bar:nth-child(4) { height: 32rpx; animation-delay: 0.15s; }
.wave-bar:nth-child(5) { height: 18rpx; animation-delay: 0.25s; }
@keyframes waveBounce { to { height: 6rpx; } }

.subtitle-area {
  padding: 12rpx 24rpx;
  background: rgba(0,0,0,0.6); min-height: 70rpx;
  display: flex; align-items: center; justify-content: center;
}
.subtitle-text { font-size: 26rpx; line-height: 1.6; text-align: center; color: #fff; }

.chat-section {
  flex: 1; display: flex; flex-direction: column;
  background: #f5f7fa; overflow: hidden;
  border-radius: 24rpx 24rpx 0 0;
}

.chat-scroll { flex: 1; padding: 20rpx 20rpx 0; }
.chat-empty { padding: 60rpx 0; text-align: center; }
.empty-icon { font-size: 60rpx; display: block; margin-bottom: 12rpx; }
.empty-tip { font-size: 26rpx; color: #aaa; }

.message-item { display: flex; gap: 12rpx; margin-bottom: 20rpx; }
.message-item.user { flex-direction: row-reverse; }
.msg-avatar { font-size: 40rpx; flex-shrink: 0; margin-top: 4rpx; }
.msg-bubble {
  max-width: 75%; padding: 16rpx 20rpx;
  border-radius: 20rpx; background: #fff;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.message-item.user .msg-bubble {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-radius: 20rpx 4rpx 20rpx 20rpx;
}
.message-item.user .msg-text { color: #fff; }
.message-item.user .msg-time { color: rgba(255,255,255,0.5); }
.msg-text { font-size: 28rpx; line-height: 1.6; color: #333; display: block; }
.msg-time { font-size: 20rpx; color: #bbb; margin-top: 6rpx; display: block; }

.msg-loading { display: flex; gap: 10rpx; padding: 16rpx 20rpx; margin-bottom: 20rpx; }
.loading-dot {
  width: 12rpx; height: 12rpx; border-radius: 50%;
  background: #409eff; animation: bounce 0.8s infinite;
}
@keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10rpx); } }

.quick-scroll { flex-shrink: 0; padding: 16rpx 20rpx 0; }
.quick-list { display: flex; gap: 12rpx; white-space: nowrap; }
.quick-tag {
  background: #fff; border: 1rpx solid #e0e0e0;
  border-radius: 32rpx; padding: 10rpx 20rpx;
  font-size: 24rpx; color: #555; white-space: nowrap;
  box-shadow: 0 1rpx 4rpx rgba(0,0,0,0.06);
  flex-shrink: 0;
}
.quick-tag:active { background: #ecf5ff; border-color: #409eff; color: #409eff; }

.input-area { padding: 16rpx 20rpx 34rpx; background: #fff; border-top: 1rpx solid #f0f0f0; }
.voice-status-bar {
  display: flex; align-items: center; justify-content: center; gap: 12rpx;
  padding: 10rpx; background: rgba(74,222,128,0.1);
  border-radius: 12rpx; margin-bottom: 12rpx;
  font-size: 24rpx; color: #67c23a;
}
.voice-anim { display: flex; align-items: center; gap: 4rpx; height: 28rpx; }
.v-wave {
  width: 4rpx; background: #4ade80; border-radius: 2rpx;
  animation: vwAnim 0.6s ease-in-out infinite alternate;
}
.v-wave:nth-child(1) { height: 8rpx; }
.v-wave:nth-child(2) { height: 18rpx; animation-delay: 0.1s; }
.v-wave:nth-child(3) { height: 28rpx; animation-delay: 0.2s; }
.v-wave:nth-child(4) { height: 16rpx; animation-delay: 0.15s; }
@keyframes vwAnim { to { height: 4rpx; } }
.v-status-text { font-size: 24rpx; }

.input-row { display: flex; gap: 12rpx; align-items: center; }
.text-input {
  flex: 1; height: 72rpx; background: #f5f7fa;
  border-radius: 36rpx; padding: 0 24rpx; font-size: 28rpx; color: #333;
}
.voice-btn {
  width: 72rpx; height: 72rpx; border-radius: 36rpx;
  background: #f0f2f5; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.voice-btn.recording { background: rgba(239,68,68,0.15); animation: recordPulse 1s infinite; }
.voice-btn.loading { background: rgba(251,191,36,0.15); }
.voice-btn-icon { font-size: 32rpx; }
@keyframes recordPulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }
.send-btn {
  width: 72rpx; height: 72rpx; border-radius: 36rpx;
  background: #409eff; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.send-icon { font-size: 28rpx; color: #fff; }

.spot-info-card {
  flex-shrink: 0; background: #fff;
  border-top: 1rpx solid #f0f0f0; padding: 20rpx;
}
.spot-card-header { display: flex; gap: 16rpx; align-items: flex-start; margin-bottom: 16rpx; }
.spot-icon-big { font-size: 48rpx; }
.spot-card-name { font-size: 30rpx; font-weight: 600; color: #1a1a1a; display: block; }
.spot-card-desc { font-size: 24rpx; color: #888; margin-top: 4rpx; display: block; }
.spot-meta-row { display: flex; gap: 16rpx; margin-bottom: 16rpx; }
.meta-chip { flex: 1; background: #f5f7fa; border-radius: 8rpx; padding: 10rpx; text-align: center; }
.meta-label { display: block; font-size: 20rpx; color: #888; margin-bottom: 4rpx; }
.meta-val { display: block; font-size: 24rpx; font-weight: 500; color: #333; }
.auto-guide-btn {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-radius: 12rpx; padding: 20rpx; text-align: center;
  color: #fff; font-size: 28rpx; font-weight: 600;
}
.auto-guide-btn:active { opacity: 0.9; }
</style>
