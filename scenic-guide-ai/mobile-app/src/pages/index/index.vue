<template>
  <view class="container">
    <!-- 自定义导航栏 -->
    <view class="nav-bar" :style="{paddingTop: statusBarHeight + 'px'}">
      <view class="nav-content">
        <text class="nav-title">🏔️ 灵山胜境 AI 导游</text>
        <view class="nav-actions">
          <text class="nav-btn" @tap="goHistory">记录</text>
        </view>
      </view>
    </view>

    <!-- 数字人展示区 -->
    <view class="avatar-section">
      <view class="avatar-container" :class="{'speaking': isSpeaking, 'listening': isListening}">
        <!-- 数字人主体 -->
        <view class="avatar-wrapper">
          <image class="avatar-img" :src="avatarImage" mode="aspectFill"/>
          <!-- 说话动画光环 -->
          <view class="speaking-ring" v-if="isSpeaking">
            <view class="ring ring-1"></view>
            <view class="ring ring-2"></view>
            <view class="ring ring-3"></view>
          </view>
          <!-- 倾听动画 -->
          <view class="listening-indicator" v-if="isListening">
            <view v-for="i in 5" :key="i" class="wave-bar" :style="{animationDelay: (i*0.1)+'s'}"></view>
          </view>
        </view>
        <!-- 状态标签 -->
        <view class="status-badge" :class="statusClass">
          <text class="status-text">{{ statusText }}</text>
        </view>
      </view>

      <!-- 当前景点信息卡 -->
      <view class="spot-card" v-if="nearbySpot">
        <view class="spot-card-inner">
          <text class="spot-icon">📍</text>
          <view class="spot-info">
            <text class="spot-name">{{ nearbySpot.name }}</text>
            <text class="spot-dist">距离 {{ nearbySpot.distance }}米</text>
          </view>
          <view class="spot-btn" @tap="triggerSpotGuide(nearbySpot)">
            <text>讲解</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 对话区域 -->
    <scroll-view
      class="chat-area"
      scroll-y
      :scroll-top="scrollTop"
      @scrolltolower="onScrollBottom"
      ref="chatScroll"
    >
      <!-- 欢迎气泡 -->
      <view class="welcome-msg" v-if="messages.length === 0">
        <view class="ai-bubble">
          <text class="bubble-text">👋 您好！我是AI导游小灵，欢迎来到灵山胜境，请问有什么可以帮您的？</text>
          <view class="quick-questions">
            <view class="q-chip" v-for="q in quickQuestions" :key="q" @tap="sendQuickQuestion(q)">
              <text>{{ q }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 消息列表 -->
      <view v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
        <!-- AI消息 -->
        <template v-if="msg.role === 'assistant'">
          <image class="msg-avatar" :src="avatarImage" mode="aspectFill"/>
          <view class="msg-content">
            <view class="bubble ai-bubble">
              <text class="bubble-text" :class="{'typing': msg.typing}">{{ msg.content }}</text>
            </view>
            <!-- 音频播放 -->
            <view class="audio-controls" v-if="msg.audioUrl">
              <view class="play-btn" @tap="playAudio(msg, idx)">
                <text>{{ msg.playing ? '⏸ 暂停' : '▶ 播放' }}</text>
              </view>
            </view>
            <!-- 情感标签 -->
            <view class="emotion-tag" v-if="msg.emotion && msg.emotion !== 'neutral'">
              <text>{{ msg.emotion === 'positive' ? '😊 正面' : '😟 需关注' }}</text>
            </view>
          </view>
        </template>

        <!-- 用户消息 -->
        <template v-if="msg.role === 'user'">
          <view class="msg-content user">
            <view class="bubble user-bubble">
              <text class="bubble-text">{{ msg.content }}</text>
            </view>
            <text class="msg-time">{{ msg.time }}</text>
          </view>
        </template>
      </view>

      <!-- 加载中 -->
      <view class="loading-msg" v-if="isLoading">
        <image class="msg-avatar" :src="avatarImage" mode="aspectFill"/>
        <view class="bubble ai-bubble loading">
          <view class="dot-loader">
            <view class="dot"></view>
            <view class="dot"></view>
            <view class="dot"></view>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 输入工具栏 -->
    <view class="input-bar" :style="{paddingBottom: safeAreaBottom + 'px'}">
      <!-- 语音模式 -->
      <template v-if="inputMode === 'voice'">
        <view class="mode-switch-btn" @tap="switchInputMode('text')">
          <text class="mode-icon">⌨️</text>
        </view>
        <view
          class="voice-btn"
          :class="{'recording': isListening}"
          @touchstart="startRecording"
          @touchend="stopRecording"
          @touchcancel="cancelRecording"
        >
          <text class="voice-btn-text">{{ isListening ? '松开发送' : '按住说话' }}</text>
          <view class="voice-wave" v-if="isListening">
            <view v-for="i in 8" :key="i" class="wave" :style="{height: Math.random()*20+10+'px'}"></view>
          </view>
        </view>
      </template>

      <!-- 文字模式 -->
      <template v-if="inputMode === 'text'">
        <view class="mode-switch-btn" @tap="switchInputMode('voice')">
          <text class="mode-icon">🎤</text>
        </view>
        <input
          class="text-input"
          v-model="inputText"
          placeholder="请输入您的问题..."
          :adjust-position="true"
          @confirm="sendTextMessage"
          confirm-type="send"
        />
        <view class="send-btn" :class="{active: inputText.trim()}" @tap="sendTextMessage">
          <text>发送</text>
        </view>
      </template>
    </view>
  </view>
</template>

<script>
import { chatApi, scenicApi, uploadFile } from '../../utils/api.js'

export default {
  name: 'GuideIndex',
  data() {
    return {
      // 状态
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight || 20,
      safeAreaBottom: 0,
      isSpeaking: false,
      isListening: false,
      isLoading: false,
      inputMode: 'voice',
      inputText: '',
      scrollTop: 999999,

      // 数字人
      avatarImage: '/static/avatar/guide.png',

      // 会话
      sessionId: null,
      deviceId: '',
      messages: [],

      // 景点
      nearbySpot: null,
      currentSpotId: null,

      // 录音
      recorderManager: null,
      recordFilePath: null,
      audioContext: null,
      currentAudio: null,

      // GPS
      gpsTimer: null,

      // 快捷问题
      quickQuestions: [
        '景区开放时间？', '门票多少钱？', '有哪些著名景点？', '怎么去最近景点？'
      ]
    }
  },

  computed: {
    statusText() {
      if (this.isListening) return '正在聆听...'
      if (this.isSpeaking) return '小灵讲解中'
      if (this.isLoading) return '思考中...'
      return '点击说话或输入'
    },
    statusClass() {
      if (this.isListening) return 'listening'
      if (this.isSpeaking) return 'speaking'
      if (this.isLoading) return 'loading'
      return 'idle'
    }
  },

  onLoad() {
    this._initDevice()
    this._initRecorder()
    this._startGPS()
    this._getSystemInfo()
  },

  onUnload() {
    if (this.gpsTimer) clearInterval(this.gpsTimer)
    if (this.recorderManager) this.recorderManager.stop()
  },

  methods: {
    _getSystemInfo() {
      const info = uni.getSystemInfoSync()
      const safeArea = info.safeAreaInsets
      this.safeAreaBottom = safeArea ? safeArea.bottom : 0
    },

    _initDevice() {
      let deviceId = uni.getStorageSync('device_id')
      if (!deviceId) {
        deviceId = 'app_' + Date.now() + '_' + Math.random().toString(36).substr(2, 8)
        uni.setStorageSync('device_id', deviceId)
      }
      this.deviceId = deviceId
      this.sessionId = uni.getStorageSync('current_session_id') || null
    },

    _initRecorder() {
      this.recorderManager = uni.getRecorderManager()
      this.recorderManager.onStop((res) => {
        if (res.tempFilePath && !this._recordCanceled) {
          this.recordFilePath = res.tempFilePath
          this._sendVoiceMessage(res.tempFilePath)
        }
      })
      this.recorderManager.onError((err) => {
        console.error('录音错误', err)
        this.isListening = false
      })
    },

    _startGPS() {
      // 每10秒检测一次位置
      this.gpsTimer = setInterval(() => {
        uni.getLocation({
          type: 'gcj02',
          success: (res) => {
            this._checkNearbySpots(res.latitude, res.longitude)
          },
          fail: () => {}
        })
      }, 10000)

      // 立即获取一次
      uni.getLocation({
        type: 'gcj02',
        success: (res) => this._checkNearbySpots(res.latitude, res.longitude),
        fail: () => {}
      })
    },

    async _checkNearbySpots(lat, lng) {
      try {
        const res = await scenicApi.getNearby(lat, lng, 150)
        if (res.triggered_spots && res.triggered_spots.length > 0) {
          const spot = res.triggered_spots[0]
          // 新景点触发
          if (!this.nearbySpot || this.nearbySpot.id !== spot.id) {
            this.nearbySpot = spot
            if (spot.triggered) {
              this._autoTriggerGuide(spot)
            }
          }
        }
      } catch (e) {}
    },

    _autoTriggerGuide(spot) {
      uni.showToast({
        title: `已进入 ${spot.name}，自动播放讲解`,
        icon: 'none',
        duration: 2000
      })
      setTimeout(() => {
        this.triggerSpotGuide(spot)
      }, 1500)
    },

    async triggerSpotGuide(spot) {
      this.currentSpotId = spot.id
      const message = `请介绍一下${spot.name}的历史文化和特色`
      await this._sendMessage(message, spot.id)
    },

    // 语音录制
    startRecording() {
      this._recordCanceled = false
      uni.authorize({
        scope: 'scope.record',
        success: () => {
          this.isListening = true
          this.recorderManager.start({
            duration: 60000,
            sampleRate: 16000,
            numberOfChannels: 1,
            encodeBitRate: 48000,
            format: 'wav'
          })
        },
        fail: () => {
          uni.showToast({ title: '请授权录音权限', icon: 'none' })
        }
      })
    },

    stopRecording() {
      this.isListening = false
      this.recorderManager.stop()
    },

    cancelRecording() {
      this._recordCanceled = true
      this.isListening = false
      this.recorderManager.stop()
    },

    async _sendVoiceMessage(filePath) {
      // 语音识别后仅填入输入框，由用户确认后手动发送
      try {
        uni.showLoading({ title: '语音识别中...', mask: true })
        const res = await uploadFile({
          url: '/api/voice/transcribe',
          filePath,
          name: 'audio',
          formData: { language: 'zh' }
        })
        uni.hideLoading()

        if (res.text) {
          // 将识别文字放入输入框
          this.inputText = res.text
          // 切换到文字输入模式，方便用户编辑
          this.inputMode = 'text'
          uni.showToast({ title: '识别完成，请确认后发送', icon: 'none', duration: 2000 })
        } else {
          uni.showToast({ title: '未能识别到语音内容', icon: 'none' })
        }
      } catch (e) {
        uni.hideLoading()
        console.error('语音识别失败', e)
        uni.showToast({ title: '语音识别失败，请重试', icon: 'none' })
      }
    },

    sendTextMessage() {
      const text = this.inputText.trim()
      if (!text) return
      this.inputText = ''
      this._sendMessage(text)
    },

    sendQuickQuestion(q) {
      this._sendMessage(q)
    },

    async _sendMessage(text, spotId = null) {
      // 添加用户消息
      this.messages.push({
        role: 'user',
        content: text,
        time: this._now()
      })
      this._scrollToBottom()
      this.isLoading = true

      try {
        const res = await chatApi.sendMessage({
          message: text,
          session_id: this.sessionId,
          device_id: this.deviceId,
          platform: 'app',
          spot_id: spotId || this.currentSpotId,
          generate_audio: true
        })

        await this._handleResponse(res, text)
      } catch (e) {
        console.error('发送失败', e)
        this.messages.push({
          role: 'assistant',
          content: '抱歉，网络出现问题，请稍后重试。',
          time: this._now()
        })
        this.isLoading = false
      }
    },

    async _handleResponse(res, userText) {
      this.sessionId = res.session_id
      uni.setStorageSync('current_session_id', this.sessionId)

      this.isLoading = false

      // 添加AI回复（打字机效果）
      const msgObj = {
        role: 'assistant',
        content: '',
        fullContent: res.answer,
        audioUrl: res.audio_url,
        emotion: res.emotion,
        time: this._now(),
        typing: true,
        playing: false
      }
      this.messages.push(msgObj)
      this._scrollToBottom()

      // 打字机效果
      await this._typewriterEffect(msgObj, res.answer)

      // 自动播放语音
      if (res.audio_url) {
        setTimeout(() => {
          this.playAudio(msgObj, this.messages.length - 1)
        }, 300)
      }
    },

    _typewriterEffect(msgObj, text) {
      return new Promise((resolve) => {
        let i = 0
        const interval = setInterval(() => {
          i++
          msgObj.content = text.substring(0, i)
          if (i >= text.length) {
            msgObj.typing = false
            clearInterval(interval)
            resolve()
          }
        }, 30)
      })
    },

    playAudio(msg, idx) {
      if (this.currentAudio) {
        this.currentAudio.stop()
        // 停止其他播放中的消息
        this.messages.forEach(m => m.playing = false)
      }

      if (msg.playing) {
        msg.playing = false
        this.isSpeaking = false
        return
      }

      const audioUrl = msg.audioUrl
      if (!audioUrl) return

      const BASE_URL = 'http://localhost:8000'
      const fullUrl = audioUrl.startsWith('http') ? audioUrl : BASE_URL + audioUrl

      this.currentAudio = uni.createInnerAudioContext()
      this.currentAudio.src = fullUrl
      this.currentAudio.play()

      msg.playing = true
      this.isSpeaking = true

      this.currentAudio.onEnded(() => {
        msg.playing = false
        this.isSpeaking = false
      })
      this.currentAudio.onError(() => {
        msg.playing = false
        this.isSpeaking = false
      })
    },

    switchInputMode(mode) {
      this.inputMode = mode
    },

    goHistory() {
      uni.switchTab({ url: '/pages/history/history' })
    },

    _scrollToBottom() {
      this.$nextTick(() => {
        this.scrollTop = this.scrollTop + 9999
      })
    },

    _now() {
      const d = new Date()
      return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
    },

    onScrollBottom() {}
  }
}
</script>

<style lang="scss">
.container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #e8f5e9 0%, #f0f7f4 100%);
  overflow: hidden;
}

/* 导航栏 */
.nav-bar {
  background: linear-gradient(135deg, #1a7a4a, #2d9e5f);
  z-index: 100;
}
.nav-content {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
}
.nav-title { color: #fff; font-size: 17px; font-weight: 600; }
.nav-btn { color: rgba(255,255,255,0.9); font-size: 14px; }

/* 数字人区域 */
.avatar-section {
  padding: 16px 20px 8px;
  align-items: center;
  display: flex;
  flex-direction: column;
}
.avatar-container {
  position: relative;
  align-items: center;
  display: flex;
  flex-direction: column;
}
.avatar-wrapper {
  position: relative;
  width: 100px;
  height: 100px;
}
.avatar-img {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 3px solid #fff;
  box-shadow: 0 4px 20px rgba(26,122,74,0.3);
  background: linear-gradient(135deg, #a8d8b0, #5cb85c);
}

/* 说话光环 */
.speaking-ring { position: absolute; top: 0; left: 0; right: 0; bottom: 0; }
.ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid #1a7a4a;
  animation: ripple 1.5s ease-out infinite;
}
.ring-1 { top: -5px; left: -5px; right: -5px; bottom: -5px; }
.ring-2 { top: -12px; left: -12px; right: -12px; bottom: -12px; animation-delay: 0.5s; opacity: 0.6; }
.ring-3 { top: -20px; left: -20px; right: -20px; bottom: -20px; animation-delay: 1s; opacity: 0.3; }
@keyframes ripple {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.3); opacity: 0; }
}

/* 倾听波形 */
.listening-indicator {
  position: absolute;
  bottom: -20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 3px;
  align-items: flex-end;
}
.wave-bar {
  width: 4px;
  height: 15px;
  background: #1a7a4a;
  border-radius: 2px;
  animation: wave-dance 0.5s ease-in-out infinite alternate;
}
@keyframes wave-dance {
  0% { height: 5px; }
  100% { height: 20px; }
}

/* 状态徽章 */
.status-badge {
  margin-top: 12px;
  padding: 4px 14px;
  border-radius: 20px;
  &.idle { background: rgba(26,122,74,0.1); }
  &.speaking { background: rgba(26,122,74,0.2); }
  &.listening { background: rgba(255,100,50,0.15); }
  &.loading { background: rgba(100,100,255,0.1); }
}
.status-text { font-size: 12px; color: #1a7a4a; }

/* 景点卡片 */
.spot-card {
  width: 100%;
  margin-top: 12px;
  background: #fff;
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.spot-card-inner { display: flex; align-items: center; gap: 10px; }
.spot-icon { font-size: 22px; }
.spot-info { flex: 1; }
.spot-name { font-size: 15px; font-weight: 600; color: #333; display: block; }
.spot-dist { font-size: 12px; color: #999; margin-top: 2px; display: block; }
.spot-btn {
  background: #1a7a4a;
  padding: 6px 14px;
  border-radius: 20px;
  text { color: #fff; font-size: 13px; }
}

/* 聊天区域 */
.chat-area {
  flex: 1;
  padding: 12px 14px;
  overflow: hidden;
}
.welcome-msg { padding: 8px 0; }
.msg-row {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-end;
  &.user { flex-direction: row-reverse; }
}
.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  margin: 0 8px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #a8d8b0, #5cb85c);
}
.msg-content { max-width: 72%; &.user { align-items: flex-end; display: flex; flex-direction: column; } }
.bubble {
  padding: 10px 14px;
  border-radius: 18px;
  max-width: 100%;
}
.ai-bubble {
  background: #fff;
  border-radius: 4px 18px 18px 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.user-bubble {
  background: linear-gradient(135deg, #1a7a4a, #2d9e5f);
  border-radius: 18px 4px 18px 18px;
}
.bubble-text {
  font-size: 15px;
  line-height: 1.6;
  color: #333;
  .user-bubble & { color: #fff; }
}
.msg-time { font-size: 11px; color: #ccc; margin-top: 4px; }
.audio-controls { margin-top: 6px; }
.play-btn {
  display: inline-flex;
  background: rgba(26,122,74,0.1);
  padding: 4px 12px;
  border-radius: 20px;
  text { font-size: 13px; color: #1a7a4a; }
}
.emotion-tag {
  margin-top: 4px;
  text { font-size: 11px; color: #999; }
}
.quick-questions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.q-chip {
  background: rgba(26,122,74,0.1);
  padding: 6px 12px;
  border-radius: 16px;
  text { font-size: 13px; color: #1a7a4a; }
}

/* 加载中 */
.loading-msg { display: flex; align-items: center; margin-bottom: 12px; }
.loading { padding: 12px 16px; }
.dot-loader { display: flex; gap: 6px; }
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #1a7a4a; opacity: 0.5;
  animation: dot-bounce 1s ease-in-out infinite;
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}
@keyframes dot-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); opacity: 1; }
}

/* 输入栏 */
.input-bar {
  background: #fff;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 -1px 0 rgba(0,0,0,0.06);
}
.mode-switch-btn {
  width: 44px; height: 44px; border-radius: 50%;
  background: rgba(26,122,74,0.1);
  display: flex; align-items: center; justify-content: center;
}
.mode-icon { font-size: 20px; }

/* 语音按钮 */
.voice-btn {
  flex: 1; height: 46px;
  background: linear-gradient(135deg, #1a7a4a, #2d9e5f);
  border-radius: 23px;
  display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
  transition: all 0.2s;
  &.recording {
    background: linear-gradient(135deg, #e74c3c, #c0392b);
    transform: scale(1.02);
  }
}
.voice-btn-text { color: #fff; font-size: 16px; font-weight: 500; z-index: 1; }
.voice-wave {
  position: absolute; bottom: 0; left: 0; right: 0;
  display: flex; align-items: flex-end; justify-content: center; gap: 2px;
  height: 30px; opacity: 0.4;
}
.wave {
  width: 3px; background: #fff; border-radius: 2px;
  animation: wave 0.5s ease infinite alternate;
}
@keyframes wave { 0% { height: 3px; } 100% { height: 20px; } }

/* 文字输入 */
.text-input {
  flex: 1; height: 44px;
  background: #f5f5f5; border-radius: 22px;
  padding: 0 16px; font-size: 15px; color: #333;
}
.send-btn {
  padding: 10px 18px; border-radius: 22px;
  background: #ccc; transition: all 0.2s;
  text { color: #fff; font-size: 15px; }
  &.active { background: linear-gradient(135deg, #1a7a4a, #2d9e5f); }
}
</style>
