/**
 * AvatarDigitalHuman.vue
 * 数字人播放器主组件
 * 整合MSE流媒体播放、WebSocket信令通道、音画同步、自动降级
 */

<template>
  <div class="avatar-digital-human" :class="{ 'is-fullscreen': fullscreen }">
    <!-- 数字人视频区域 -->
    <div class="avatar-container" ref="containerRef">
      <!-- 视频元素 (隐藏，用作渲染目标) -->
      <video
        ref="videoRef"
        class="avatar-video"
        :class="{ hidden: isFallbackMode }"
        playsinline
        muted
      ></video>

      <!-- 降级模式：纯语音+字幕 -->
      <div v-if="isFallbackMode" class="avatar-fallback">
        <div class="fallback-avatar">
          <svg viewBox="0 0 100 100" class="avatar-icon">
            <circle cx="50" cy="35" r="20" fill="#667eea" />
            <ellipse cx="50" cy="80" rx="30" ry="20" fill="#667eea" />
            <circle cx="43" cy="32" r="3" fill="#fff" />
            <circle cx="57" cy="32" r="3" fill="#fff" />
            <path :d="mouthPath" stroke="#fff" stroke-width="2" fill="none" />
          </svg>
        </div>
        <div class="fallback-subtitle" v-if="subtitle">
          <span
            v-for="(char, i) in subtitleChars"
            :key="i"
            :class="{ highlight: i <= subtitleHighlight }"
          >{{ char }}</span>
        </div>
      </div>

      <!-- 状态指示器 -->
      <div class="avatar-status">
        <span class="status-dot" :class="state"></span>
        <span class="status-text">{{ stateText }}</span>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="avatar-error">
        <span>{{ errorMessage }}</span>
        <button @click="retry" v-if="retryCount < maxRetries">重试 ({{ maxRetries - retryCount }})</button>
      </div>

      <!-- 同步状态（调试用） -->
      <div v-if="showDebug" class="avatar-debug">
        <div>状态: {{ state }}</div>
        <div>帧率: {{ frameRate }}fps</div>
        <div>缓冲: {{ bufferHealth }}%</div>
        <div>延迟: {{ latency }}ms</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useDigitalHumanStream, DigitalHumanState } from '../composables/useDigitalHumanStream.js';
import { useMSERenderer } from '../composables/useMSERenderer.js';

const props = defineProps({
  wsUrl: {
    type: String,
    default: 'ws://localhost:8080/api/digital-human/stream'
  },
  debug: {
    type: Boolean,
    default: false
  },
  autoPlay: {
    type: Boolean,
    default: true
  },
  maxRetries: {
    type: Number,
    default: 3
  }
});

const emit = defineEmits(['stateChange', 'error', 'subtitleUpdate']);

// Refs
const containerRef = ref(null);
const videoRef = ref(null);

// 状态
const state = ref(DigitalHumanState.IDLE);
const subtitle = ref('');
const subtitleHighlight = ref(-1);
const error = ref(null);
const errorMessage = ref('');
const retryCount = ref(0);
const isFallbackMode = ref(false);
const fullscreen = ref(false);
const frameRate = ref(0);
const bufferHealth = ref(100);
const latency = ref(0);

// 字幕计算属性
const subtitleChars = computed(() => subtitle.value.split(''));
const stateText = computed(() => {
  const texts = {
    [DigitalHumanState.IDLE]: '待机',
    [DigitalHumanState.LISTENING]: '倾听中',
    [DigitalHumanState.THINKING]: '思考中',
    [DigitalHumanState.SPEAKING]: '说话中',
    [DigitalHumanState.ERROR]: '连接异常'
  };
  return texts[state.value] || '未知';
});
const showDebug = computed(() => props.debug);

// 字幕动画定时器
let subtitleTimer = null;

// 初始化MSE渲染器
const mseRenderer = useMSERenderer(videoRef, {
  onFrameRateChange: (fps) => {
    frameRate.value = fps;
    // 帧率低于20fps时降级
    if (fps < 20) {
      console.warn('[Avatar] Low FPS, switching to fallback');
      enableFallbackMode();
    }
  },
  onError: (e) => {
    if (e.message === 'VIDEO_CODEC_UNSUPPORTED') {
      enableFallbackMode();
    } else {
      handleError(e);
    }
  },
  onBuffering: (isBuffering) => {
    // 缓冲状态变化
  }
});

// 初始化WebSocket信令通道
const dhStream = useDigitalHumanStream({
  wsUrl: props.wsUrl,
  onStateChange: (newState) => {
    state.value = newState;
    emit('stateChange', newState);
  },
  onVideoChunk: (chunk) => {
    if (!isFallbackMode.value) {
      mseRenderer.appendChunk(chunk);
    }
  },
  onSync: (syncData) => {
    latency.value = dhStream.latency.value;
    mseRenderer.syncTime(syncData.videoTime);
  },
  onError: (e) => {
    handleError(e);
  }
});

// 启用降级模式（纯语音+字幕）
const enableFallbackMode = () => {
  isFallbackMode.value = true;
  mseRenderer.pause();
};

// 处理错误
const handleError = (e) => {
  error.value = true;
  errorMessage.value = e.message || '连接失败';
  emit('error', e);
  retryCount.value++;

  if (retryCount.value >= props.maxRetries) {
    // 3次重试后启用降级模式
    console.log('[Avatar] Max retries, enabling fallback mode');
    enableFallbackMode();
    error.value = false;
  }
};

// 重试
const retry = () => {
  error.value = false;
  retryCount.value = 0;
  dhStream.disconnect();
  dhStream.connect();
};

// 开始说话（对外暴露）
const speak = (params) => {
  const { text, audioUrl, emotion } = params;
  
  // 设置字幕并启动动画
  startSubtitle(text);
  
  // 发送信令
  dhStream.speak({ text, audioUrl, emotion });
  
  // MSE模式下播放视频
  if (!isFallbackMode.value) {
    mseRenderer.play();
  }
};

// 字幕动画
const startSubtitle = (text) => {
  // 清除之前的定时器
  if (subtitleTimer) {
    clearInterval(subtitleTimer);
  }

  subtitle.value = text;
  subtitleHighlight.value = -1;
  
  // 逐字高亮动画
  const chars = text.split('');
  let index = 0;
  
  // 根据字数控制速度（平均每个字200-400ms）
  const delay = Math.max(100, Math.min(400, 10000 / chars.length));
  
  subtitleTimer = setInterval(() => {
    if (index < chars.length) {
      subtitleHighlight.value = index;
      index++;
      emit('subtitleUpdate', { current: index, total: chars.length });
    } else {
      clearInterval(subtitleTimer);
      subtitleTimer = null;
    }
  }, delay);
};

// 倾听状态
const setListening = () => {
  dhStream.listening();
};

// 思考状态
const setThinking = () => {
  dhStream.thinking();
};

// 切换全屏
const toggleFullscreen = () => {
  if (!containerRef.value) return;
  
  if (!document.fullscreenElement) {
    containerRef.value.requestFullscreen?.() || 
    containerRef.value.webkitRequestFullscreen?.();
    fullscreen.value = true;
  } else {
    document.exitFullscreen?.() || 
    document.webkitExitFullscreen?.();
    fullscreen.value = false;
  }
};

// 口型SVG路径（降级模式用）
const mouthPath = computed(() => {
  // 根据说话状态改变嘴型
  if (state.value === DigitalHumanState.SPEAKING) {
    // 张嘴
    return 'M 40 50 Q 50 58 60 50';
  } else if (state.value === DigitalHumanState.THINKING) {
    // 小张嘴
    return 'M 42 52 Q 50 54 58 52';
  }
  // 闭嘴
  return 'M 42 52 Q 50 52 58 52';
});

// 生命周期
onMounted(async () => {
  await nextTick();
  
  // 初始化MSE
  await mseRenderer.init();
  
  // 连接WebSocket
  if (props.autoPlay) {
    dhStream.connect();
  }
});

onUnmounted(() => {
  if (subtitleTimer) {
    clearInterval(subtitleTimer);
  }
  dhStream.disconnect();
  mseRenderer.cleanup();
});

// 暴露方法给父组件
defineExpose({
  speak,
  setListening,
  setThinking,
  retry,
  enableFallbackMode,
  toggleFullscreen
});
</script>

<style scoped>
.avatar-digital-human {
  width: 100%;
  height: 100%;
  position: relative;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  overflow: hidden;
}

.avatar-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.avatar-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.avatar-video.hidden {
  display: none;
}

/* 降级模式 */
.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.fallback-avatar {
  width: 200px;
  height: 200px;
  margin-bottom: 40px;
}

.avatar-icon {
  width: 100%;
  height: 100%;
}

.fallback-subtitle {
  max-width: 80%;
  text-align: center;
  font-size: 1.2rem;
  color: #fff;
  line-height: 1.8;
  background: rgba(0, 0, 0, 0.6);
  padding: 16px 24px;
  border-radius: 8px;
}

.fallback-subtitle span {
  transition: color 0.1s;
  color: rgba(255, 255, 255, 0.4);
}

.fallback-subtitle span.highlight {
  color: #fff;
  text-shadow: 0 0 10px rgba(102, 126, 234, 0.8);
}

/* 状态指示器 */
.avatar-status {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 20px;
  font-size: 0.85rem;
  color: #fff;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.status-dot.idle { background: #666; }
.status-dot.listening { background: #4ade80; animation: pulse 1s infinite; }
.status-dot.thinking { background: #facc15; animation: pulse 1.5s infinite; }
.status-dot.speaking { background: #60a5fa; animation: pulse 0.5s infinite; }
.status-dot.error { background: #f87171; }

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

/* 错误提示 */
.avatar-error {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  padding: 12px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.9rem;
}

.avatar-error button {
  background: #fff;
  color: #ef4444;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

/* 调试信息 */
.avatar-debug {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.7);
  color: #4ade80;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-family: monospace;
  line-height: 1.6;
}
</style>
