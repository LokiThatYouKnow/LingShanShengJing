/**
 * 数字人WebSocket信令通道
 * 负责与后端数字人服务建立连接，接收视频流和控制指令
 */

import { ref, onUnmounted } from 'vue';

export const DigitalHumanState = {
  IDLE: 'idle',           // 空闲
  LISTENING: 'listening',  // 倾听中
  THINKING: 'thinking',    // 思考中
  SPEAKING: 'speaking',    // 说话中
  ERROR: 'error'          // 错误
};

export function useDigitalHumanStream(options = {}) {
  const {
    wsUrl = 'ws://localhost:8080/api/digital-human/stream',
    onStateChange = () => {},
    onVideoChunk = () => {},
    onSync = () => {},
    onError = () => {}
  } = options;

  const state = ref(DigitalHumanState.IDLE);
  const currentVideoTime = ref(0);
  const latency = ref(0);
  const retryCount = ref(0);
  const maxRetries = 3;

  let ws = null;
  let reconnectTimer = null;
  let pingTimer = null;
  let lastSyncTime = 0;

  // 连接WebSocket
  const connect = () => {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[DH-WS] Connected');
        retryCount.value = 0;
        onStateChange(DigitalHumanState.IDLE);
        
        // 启动心跳
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          }
        }, 5000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleMessage(msg);
        } catch (e) {
          // 二进制数据（视频流）
          onVideoChunk(event.data);
        }
      };

      ws.onerror = (error) => {
        console.error('[DH-WS] Error:', error);
        onError(error);
      };

      ws.onclose = () => {
        console.log('[DH-WS] Disconnected');
        cleanup();
        handleReconnect();
      };
    } catch (e) {
      console.error('[DH-WS] Connect error:', e);
      onError(e);
      handleReconnect();
    }
  };

  // 处理消息
  const handleMessage = (msg) => {
    switch (msg.type) {
      case 'state':
        state.value = msg.state;
        onStateChange(msg.state);
        break;

      case 'sync':
        // 音画同步时间戳
        const serverTime = msg.timestamp;
        const clientTime = Date.now();
        latency.value = clientTime - serverTime;
        currentVideoTime.value = msg.videoTime;
        lastSyncTime = clientTime;
        onSync(msg);
        break;

      case 'pong':
        // 心跳响应
        latency.value = Date.now() - msg.echo;
        break;

      case 'error':
        console.error('[DH-WS] Server error:', msg.message);
        onError(new Error(msg.message));
        break;

      case 'end':
        // 播放结束
        state.value = DigitalHumanState.IDLE;
        onStateChange(DigitalHumanState.IDLE);
        break;

      default:
        console.log('[DH-WS] Unknown message:', msg.type);
    }
  };

  // 发送消息
  const send = (data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  };

  // 请求开始说话（携带文本和音频URL）
  const speak = (params) => {
    const { text, audioUrl, emotion = 'neutral' } = params;
    send({
      type: 'speak',
      text,
      audioUrl,
      emotion,
      clientTime: Date.now()
    });
    state.value = DigitalHumanState.SPEAKING;
    onStateChange(DigitalHumanState.SPEAKING);
  };

  // 请求倾听状态
  const listening = () => {
    send({ type: 'listening' });
    state.value = DigitalHumanState.LISTENING;
    onStateChange(DigitalHumanState.LISTENING);
  };

  // 请求思考状态
  const thinking = () => {
    send({ type: 'thinking' });
    state.value = DigitalHumanState.THINKING;
    onStateChange(DigitalHumanState.THINKING);
  };

  // 断开连接
  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    cleanup();
    if (ws) {
      ws.close();
      ws = null;
    }
    state.value = DigitalHumanState.IDLE;
  };

  // 清理定时器
  const cleanup = () => {
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
  };

  // 重连逻辑
  const handleReconnect = () => {
    if (retryCount.value >= maxRetries) {
      console.log('[DH-WS] Max retries reached, give up');
      state.value = DigitalHumanState.ERROR;
      onStateChange(DigitalHumanState.ERROR);
      onError(new Error('连接失败'));
      return;
    }

    retryCount.value++;
    console.log(`[DH-WS] Reconnecting... (${retryCount.value}/${maxRetries})`);
    
    reconnectTimer = setTimeout(() => {
      connect();
    }, 1000 * retryCount.value); // 指数退避
  };

  // 组件卸载时清理
  onUnmounted(() => {
    disconnect();
  });

  return {
    state,
    currentVideoTime,
    latency,
    retryCount,
    connect,
    disconnect,
    speak,
    listening,
    thinking,
    send
  };
}
