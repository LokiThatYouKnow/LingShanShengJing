/**
 * useDigitalHumanChat.js
 * 数字人对话控制器
 * 整合对话发送 → ASR识别 → 获取回复 → 播放数字人
 */

import { ref, computed } from 'vue';
import axios from 'axios';
import { useDigitalHumanStream, DigitalHumanState } from './useDigitalHumanStream.js';

export function useDigitalHumanChat(options = {}) {
  const {
    // 后端接口地址
    chatUrl = '/api/chat/message',
    asrUrl = '/api/voice/asr',
    // 数字人WebSocket地址
    dhWsUrl = 'ws://localhost:8080/api/digital-human/stream',
    // 自动播放音频
    autoPlayAudio = true
  } = options;

  // 状态
  const isLoading = ref(false);
  const currentQuestion = ref('');
  const currentAnswer = ref('');
  const currentEmotion = ref('neutral');
  const conversationHistory = ref([]);
  const error = ref(null);

  // 创建数字人流控制器
  const dhStream = useDigitalHumanStream({
    wsUrl: dhWsUrl,
    onStateChange: (state) => {
      dhState.value = state;
    },
    onVideoChunk: (chunk) => {
      videoChunks.push(chunk);
      // 通知渲染器
      if (onVideoChunk) {
        onVideoChunk(chunk);
      }
    },
    onSync: (syncData) => {
      // 音画同步
      if (onSync) {
        onSync(syncData);
      }
    },
    onError: (e) => {
      error.value = e;
      console.error('[DH-Chat] Error:', e);
    }
  });

  let videoChunks = [];
  let onVideoChunk = null;
  let onSync = null;

  const dhState = ref(DigitalHumanState.IDLE);

  /**
   * 发送文字问题，获取回复并播放数字人
   */
  const sendMessage = async (text, callbacks = {}) => {
    if (!text || text.trim() === '') {
      return { success: false, error: '问题不能为空' };
    }

    isLoading.value = true;
    error.value = null;
    currentQuestion.value = text;
    videoChunks = [];

    // 设置回调
    onVideoChunk = callbacks.onVideoChunk;
    onSync = callbacks.onSync;

    try {
      // 1. 发送对话请求
      const response = await axios.post(chatUrl, {
        message: text,
        sessionId: getSessionId(),
        history: conversationHistory.value.slice(-10) // 只传最近10条
      });

      const { answer, audioUrl, emotion, sessionId } = response.data;
      
      currentAnswer.value = answer;
      currentEmotion.value = emotion || 'neutral';

      // 2. 添加到对话历史
      conversationHistory.value.push({
        role: 'user',
        content: text,
        timestamp: Date.now()
      });
      conversationHistory.value.push({
        role: 'assistant',
        content: answer,
        audioUrl,
        emotion,
        timestamp: Date.now()
      });

      // 3. 自动播放数字人
      if (autoPlayAudio && audioUrl) {
        await playDigitalHuman({
          text: answer,
          audioUrl,
          emotion: emotion || 'neutral'
        });
      }

      return {
        success: true,
        answer,
        audioUrl,
        emotion
      };

    } catch (e) {
      console.error('[DH-Chat] Send error:', e);
      error.value = e.response?.data?.message || e.message || '请求失败';
      return {
        success: false,
        error: error.value
      };
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * 播放数字人（需要先有音频URL）
   */
  const playDigitalHuman = async (params) => {
    const { text, audioUrl, emotion } = params;

    // 通知开始说话
    dhStream.speak({ text, audioUrl, emotion });

    // 如果有自定义渲染回调，在这里触发
    if (callbacks.onStartSpeaking) {
      callbacks.onStartSpeaking({ text, audioUrl });
    }

    // 预加载音频（用于音画同步）
    await preloadAudio(audioUrl);
  };

  /**
   * 预加载音频并返回Audio元素
   */
  const preloadAudio = (audioUrl) => {
    return new Promise((resolve, reject) => {
      const audio = new Audio();
      
      audio.addEventListener('canplaythrough', () => {
        resolve(audio);
      });
      
      audio.addEventListener('error', (e) => {
        reject(new Error('音频加载失败'));
      });

      // CORS处理：如果跨域，尝试设置
      audio.crossOrigin = 'anonymous';
      audio.src = audioUrl;
      audio.load();
    });
  };

  /**
   * ASR语音识别（上传音频文件）
   */
  const recognizeSpeech = async (audioFile, callbacks = {}) => {
    isLoading.value = true;
    error.value = null;

    try {
      const formData = new FormData();
      formData.append('file', audioFile);

      const response = await axios.post(asrUrl, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 30000 // 30秒超时
      });

      const { text, confidence } = response.data;

      if (callbacks.onResult) {
        callbacks.onResult({ text, confidence });
      }

      return {
        success: true,
        text,
        confidence
      };

    } catch (e) {
      console.error('[DH-Chat] ASR error:', e);
      error.value = e.response?.data?.message || e.message || '识别失败';
      
      if (callbacks.onError) {
        callbacks.onError(error.value);
      }

      return {
        success: false,
        error: error.value
      };
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * 获取/创建会话ID
   */
  const getSessionId = () => {
    let sessionId = localStorage.getItem('dh_session_id');
    if (!sessionId) {
      sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('dh_session_id', sessionId);
    }
    return sessionId;
  };

  /**
   * 清空对话历史
   */
  const clearHistory = () => {
    conversationHistory.value = [];
    localStorage.removeItem('dh_session_id');
  };

  /**
   * 连接数字人流服务
   */
  const connect = () => {
    dhStream.connect();
  };

  /**
   * 断开连接
   */
  const disconnect = () => {
    dhStream.disconnect();
  };

  // 临时回调存储（会在sendMessage时使用）
  let callbacks = {};

  return {
    // 状态
    isLoading,
    currentQuestion,
    currentAnswer,
    currentEmotion,
    conversationHistory,
    error,
    dhState,
    dhStream,

    // 方法
    sendMessage,
    playDigitalHuman,
    recognizeSpeech,
    clearHistory,
    connect,
    disconnect,
    getSessionId
  };
}
