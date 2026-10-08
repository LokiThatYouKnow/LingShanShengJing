/**
 * 数字人MSE流媒体播放器
 * 使用Media Source Extensions实现边推边播
 * 支持音画同步、帧率监控、自动降级
 */

import { ref, onUnmounted, watch, nextTick } from 'vue';
import { DigitalHumanState } from './useDigitalHumanStream.js';

export function useMSERenderer(videoRef, options = {}) {
  const {
    maxBufferSize = 30 * 1024 * 1024, // 30MB缓冲
    onFrameRateChange = () => {},
    onError = () => {},
    onBuffering = () => {}
  } = options;

  const mediaSource = ref(null);
  const sourceBuffer = ref(null);
  const isBuffering = ref(false);
  const currentFrameRate = ref(0);
  const bufferHealth = ref(100); // 缓冲健康度 0-100

  let frameCount = 0;
  let lastFrameTime = 0;
  let frameRateTimer = null;
  let videoElement = null;
  let pendingChunks = [];
  let isAppending = false;

  // 初始化MediaSource
  const init = async () => {
    if (!videoRef.value) {
      console.error('[MSE] Video element not found');
      return false;
    }

    videoElement = videoRef.value;

    try {
      // 创建MediaSource
      mediaSource.value = new MediaSource();
      mediaSource.value.addEventListener('sourceopen', onSourceOpen);
      mediaSource.value.addEventListener('sourceclose', onSourceClose);
      mediaSource.value.addEventListener('sourceended', onSourceEnded);

      // 绑定到video元素
      const url = URL.createObjectURL(mediaSource.value);
      videoElement.src = url;

      // 监听视频事件
      videoElement.addEventListener('waiting', () => {
        isBuffering.value = true;
        onBuffering(true);
      });

      videoElement.addEventListener('playing', () => {
        isBuffering.value = false;
        onBuffering(false);
        startFrameRateMonitor();
      });

      videoElement.addEventListener('pause', () => {
        stopFrameRateMonitor();
      });

      videoElement.addEventListener('error', (e) => {
        console.error('[MSE] Video error:', e);
        onError(e);
      });

      return true;
    } catch (e) {
      console.error('[MSE] Init error:', e);
      onError(e);
      return false;
    }
  };

  // MediaSource打开成功
  const onSourceOpen = () => {
    console.log('[MSE] MediaSource opened');
    
    // 添加视频sourceBuffer
    const mimeCodec = 'video/webm; codecs="vp8,vorbis"';
    
    if (MediaSource.isTypeSupported(mimeCodec)) {
      sourceBuffer.value = mediaSource.value.addSourceBuffer(mimeCodec);
      setupSourceBuffer(sourceBuffer.value);
    } else {
      // 降级：尝试其他格式
      const altMimeCodec = 'video/mp4; codecs="avc1.4D401E,mp4a.40.2"';
      if (MediaSource.isTypeSupported(altMimeCodec)) {
        sourceBuffer.value = mediaSource.value.addSourceBuffer(altMimeCodec);
        setupSourceBuffer(sourceBuffer.value);
      } else {
        console.error('[MSE] No supported codec found');
        onError(new Error('浏览器不支持视频编码'));
      }
    }
  };

  // 配置SourceBuffer
  const setupSourceBuffer = (buffer) => {
    buffer.addEventListener('updateend', onUpdateEnd);
    buffer.addEventListener('error', (e) => {
      console.error('[MSE] SourceBuffer error:', e);
      onError(e);
    });

    // 设置缓冲模式
    buffer.mode = 'sequence'; // 保持顺序播放
  };

  // SourceBuffer更新完成
  const onUpdateEnd = () => {
    isAppending = false;
    
    // 处理队列中的下一个chunk
    if (pendingChunks.length > 0) {
      const nextChunk = pendingChunks.shift();
      appendChunk(nextChunk);
    }

    // 更新缓冲健康度
    updateBufferHealth();
  };

  // 追加视频数据
  const appendChunk = (chunk) => {
    if (!sourceBuffer.value || sourceBuffer.value.updating) {
      pendingChunks.push(chunk);
      return;
    }

    // 过滤空数据
    if (!chunk || chunk.size === 0) return;

    try {
      isAppending = true;
      sourceBuffer.value.appendBuffer(chunk);
    } catch (e) {
      console.error('[MSE] Append error:', e);
      isAppending = false;
      
      // 如果是编码不支持错误，尝试降级
      if (e.name === 'NotSupportedError') {
        handleCodecError();
      } else {
        onError(e);
      }
    }
  };

  // 处理编码不支持错误
  const handleCodecError = () => {
    console.warn('[MSE] Codec error, attempting fallback');
    
    // 尝试移除并重建SourceBuffer
    if (mediaSource.value && sourceBuffer.value) {
      try {
        mediaSource.value.removeSourceBuffer(sourceBuffer.value);
      } catch (e) {
        // 忽略
      }
    }
    
    // 降级为纯音频模式（在后端实现时处理）
    onError(new Error('VIDEO_CODEC_UNSUPPORTED'));
  };

  // 更新缓冲健康度
  const updateBufferHealth = () => {
    if (!videoElement || !mediaSource.value) return;

    const buffered = videoElement.buffered;
    if (buffered.length === 0) {
      bufferHealth.value = 0;
      return;
    }

    const currentTime = videoElement.currentTime;
    const end = buffered.end(buffered.length - 1);
    const aheadTime = end - currentTime;
    
    // 理想缓冲5-10秒
    if (aheadTime < 1) {
      bufferHealth.value = 30; // 危险
    } else if (aheadTime < 3) {
      bufferHealth.value = 60; // 偏低
    } else if (aheadTime > 10) {
      bufferHealth.value = 100; // 健康但可能过多
    } else {
      bufferHealth.value = 80;
    }
  };

  // 帧率监控
  const startFrameRateMonitor = () => {
    if (frameRateTimer) return;

    frameRateTimer = setInterval(() => {
      if (!videoElement) return;

      const now = performance.now();
      const elapsed = now - lastFrameTime;
      
      if (elapsed > 0) {
        currentFrameRate.value = Math.round(1000 / elapsed * frameCount);
      }
      
      frameCount = 0;
      lastFrameTime = now;

      // 帧率低于20fps时通知降级
      if (currentFrameRate.value < 20 && currentFrameRate.value > 0) {
        console.warn(`[MSE] Low frame rate: ${currentFrameRate.value}fps`);
        onFrameRateChange(currentFrameRate.value);
      }
    }, 1000);
  };

  const stopFrameRateMonitor = () => {
    if (frameRateTimer) {
      clearInterval(frameRateTimer);
      frameRateTimer = null;
    }
  };

  // 同步视频时间
  const syncTime = (targetTime) => {
    if (!videoElement) return;

    const drift = Math.abs(videoElement.currentTime - targetTime);
    
    // 偏差超过100ms时修正
    if (drift > 0.1) {
      videoElement.currentTime = targetTime;
      console.log(`[MSE] Sync: ${drift.toFixed(3)}s adjusted`);
    }
  };

  // 播放
  const play = () => {
    if (videoElement && mediaSource.value?.readyState === 'open') {
      videoElement.play().catch(e => {
        console.error('[MSE] Play error:', e);
      });
    }
  };

  // 暂停
  const pause = () => {
    if (videoElement) {
      videoElement.pause();
    }
  };

  // 停止并重置
  const reset = () => {
    pause();
    pendingChunks = [];
    
    // 关闭MediaSource
    if (mediaSource.value) {
      mediaSource.value.endOfStream();
    }

    if (videoElement) {
      videoElement.src = '';
    }

    stopFrameRateMonitor();
  };

  // 清理
  const cleanup = () => {
    reset();
    
    if (mediaSource.value) {
      mediaSource.value.removeEventListener('sourceopen', onSourceOpen);
      mediaSource.value.removeEventListener('sourceclose', onSourceClose);
      mediaSource.value.removeEventListener('sourceended', onSourceEnded);
    }
    
    if (sourceBuffer.value) {
      sourceBuffer.value.removeEventListener('updateend', onUpdateEnd);
    }
  };

  // 事件处理器
  const onSourceClose = () => {
    console.log('[MSE] MediaSource closed');
  };

  const onSourceEnded = () => {
    console.log('[MSE] MediaSource ended');
    stopFrameRateMonitor();
  };

  // 组件卸载
  onUnmounted(() => {
    cleanup();
  });

  return {
    mediaSource,
    sourceBuffer,
    isBuffering,
    currentFrameRate,
    bufferHealth,
    init,
    appendChunk,
    syncTime,
    play,
    pause,
    reset,
    cleanup
  };
}
