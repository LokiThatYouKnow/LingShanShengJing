/**
 * 数字人集成示例 - KioskView中使用
 * 
 * 本文件展示如何在现有的 KioskView.vue 中集成 AvatarDigitalHuman 组件
 * 实际使用时，将以下代码复制到对应的 Vue 组件中即可
 */

<template>
  <div class="kiosk-page">
    <!-- 顶部区域 -->
    <header class="kiosk-header">
      <h1>景区AI导览</h1>
      <div class="header-info">
        <span>{{ currentTime }}</span>
        <span>{{ weather }}</span>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="kiosk-main">
      <!-- 左侧：数字人 -->
      <section class="avatar-section">
        <!-- 数字人播放器（新增） -->
        <AvatarDigitalHuman
          ref="avatarRef"
          ws-url="ws://localhost:8080/api/digital-human/stream"
          :debug="isDev"
          @state-change="onAvatarStateChange"
          @error="onAvatarError"
        />
        
        <!-- 数字人状态字幕 -->
        <div class="avatar-subtitle" v-if="avatarSubtitle">
          {{ avatarSubtitle }}
        </div>
      </section>

      <!-- 右侧：交互区 -->
      <section class="interaction-section">
        <!-- 语音输入区 -->
        <div class="voice-input">
          <button 
            class="voice-btn"
            :class="{ recording: isRecording }"
            @mousedown="startRecording"
            @mouseup="stopRecording"
            @mouseleave="stopRecording"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
            <span>{{ isRecording ? '松开结束' : '按住说话' }}</span>
          </button>
        </div>

        <!-- 文本输入区 -->
        <div class="text-input">
          <el-input
            v-model="questionText"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="或输入您的问题..."
            @keyup.enter.ctrl="sendQuestion"
          />
          <el-button 
            type="primary" 
            :loading="isSending"
            :disabled="!questionText.trim()"
            @click="sendQuestion"
          >
            提问
          </el-button>
        </div>

        <!-- 对话历史 -->
        <div class="chat-history">
          <div 
            v-for="(msg, i) in chatHistory" 
            :key="i"
            class="chat-message"
            :class="msg.role"
          >
            <div class="message-content">{{ msg.content }}</div>
            <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>

        <!-- 快捷问题 -->
        <div class="quick-questions">
          <el-tag
            v-for="q in quickQuestions"
            :key="q"
            @click="sendQuestion(q)"
          >
            {{ q }}
          </el-tag>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
// 引入数字人组件
import AvatarDigitalHuman from '@/components/avatar/AvatarDigitalHuman.vue';
// 引入对话控制器
import { useDigitalHumanChat } from '@/composables/useDigitalHumanChat.js';

const avatarRef = ref(null);
const questionText = ref('');
const isSending = ref(false);
const isRecording = ref(false);
const isDev = ref(true); // 生产环境设为 false
const avatarSubtitle = ref('');
const chatHistory = ref([]);
const currentTime = ref('');
const weather = ref('');

// 快捷问题
const quickQuestions = [
  '景点开放时间',
  '门票价格',
  '推荐游览路线',
  '附近餐饮',
  '停车场位置'
];

// 初始化数字人对话控制器
const chat = useDigitalHumanChat({
  chatUrl: '/api/chat/message',
  asrUrl: '/api/voice/asr',
  dhWsUrl: 'ws://localhost:8080/api/digital-human/stream',
  autoPlayAudio: true
});

// 发送问题
const sendQuestion = async (text) => {
  const q = text || questionText.value.trim();
  if (!q) return;

  isSending.value = true;
  
  try {
    const result = await chat.sendMessage(q, {
      onStartSpeaking: ({ text }) => {
        avatarSubtitle.value = text;
      }
    });

    if (result.success) {
      // 添加到对话历史
      chatHistory.value.push({
        role: 'user',
        content: q,
        timestamp: Date.now()
      });
      
      chatHistory.value.push({
        role: 'assistant',
        content: result.answer,
        timestamp: Date.now()
      });

      // 清空输入
      questionText.value = '';
    } else {
      ElMessage.error(result.error || '发送失败');
    }
  } catch (e) {
    ElMessage.error('网络错误');
  } finally {
    isSending.value = false;
  }
};

// 录音相关（简化版，需要接入实际ASR）
const startRecording = () => {
  isRecording.value = true;
  // TODO: 调用 MediaRecorder API 开始录音
  console.log('开始录音...');
};

const stopRecording = async () => {
  if (!isRecording.value) return;
  isRecording.value = false;
  
  // TODO: 停止录音并获取 audioBlob
  // const audioBlob = await stopAndGetAudio();
  // await chat.recognizeSpeech(audioBlob, {
  //   onResult: ({ text }) => {
  //     sendQuestion(text);
  //   }
  // });
};

// 数字人状态变化
const onAvatarStateChange = (state) => {
  console.log('数字人状态:', state);
  
  switch (state) {
    case 'listening':
      avatarSubtitle.value = '我在听，请说...';
      break;
    case 'thinking':
      avatarSubtitle.value = '让我想想...';
      break;
    case 'speaking':
      // 字幕由组件内部管理
      break;
    case 'error':
      ElMessage.warning('数字人服务异常，已切换到降级模式');
      break;
  }
};

// 数字人错误处理
const onAvatarError = (error) => {
  console.error('数字人错误:', error);
};

// 格式化时间
const formatTime = (timestamp) => {
  const d = new Date(timestamp);
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
};

// 更新时间
onMounted(() => {
  // 连接数字人服务
  chat.connect();
  
  // 定时更新时钟
  setInterval(() => {
    const now = new Date();
    currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }, 1000);
});
</script>

<style scoped>
/* 基础布局（简化版） */
.kiosk-page {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0f0f23;
  color: #fff;
}

.kiosk-header {
  padding: 20px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255,255,255,0.05);
}

.kiosk-main {
  flex: 1;
  display: flex;
  gap: 40px;
  padding: 20px 40px;
  overflow: hidden;
}

/* 数字人区域 */
.avatar-section {
  flex: 1;
  position: relative;
}

.avatar-subtitle {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.7);
  padding: 12px 24px;
  border-radius: 8px;
  max-width: 80%;
  text-align: center;
}

/* 交互区域 */
.interaction-section {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 语音按钮 */
.voice-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  transition: all 0.3s;
}

.voice-btn:active,
.voice-btn.recording {
  transform: scale(0.98);
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.voice-btn svg {
  width: 24px;
  height: 24px;
}

/* 文字输入 */
.text-input {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 对话历史 */
.chat-history {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.chat-message.user {
  align-self: flex-end;
  background: #667eea;
}

.chat-message.assistant {
  align-self: flex-start;
  background: rgba(255,255,255,0.1);
}

/* 快捷问题 */
.quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-questions .el-tag {
  cursor: pointer;
}
</style>
