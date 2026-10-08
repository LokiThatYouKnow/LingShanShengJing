<template>
  <div class="chibi-wrapper">
    <!-- 气泡对话框 -->
    <div class="chibi-bubble" v-if="subtitle && talking">
      <span>{{ subtitle }}</span>
    </div>

    <!-- 思考气泡 -->
    <div class="think-bubble" v-if="loading">
      <div class="think-dots">
        <span></span><span></span><span></span>
      </div>
    </div>

    <!-- Q版数字人 -->
    <div class="chibi" :class="{ thinking: loading, talking: talking }">
      <div class="chibi-hair" :style="hairStyle">
        <span class="hair-deco" v-if="outfit.decoration">{{ outfit.decoration }}</span>
      </div>
      <div class="chibi-head">
        <div class="chibi-face">
          <div class="chibi-eyes">
            <div class="eye left" :class="{ blink: blinking }">
              <div class="eye-highlight"></div>
            </div>
            <div class="eye right" :class="{ blink: blinking }">
              <div class="eye-highlight"></div>
            </div>
          </div>
          <div class="blush left"></div>
          <div class="blush right"></div>
          <div class="chibi-mouth" :class="{ talking: talking }"></div>
          <div class="chibi-emotion" v-if="loading && !talking">
            <div class="emotion-dots">...</div>
          </div>
        </div>
      </div>
      <div class="chibi-body" :style="{ background: outfit.outfitBg }">
        <div class="body-collar" :style="{ background: outfit.collarColor }"></div>
      </div>
      <div class="chibi-arm left" :style="{ background: outfit.outfitBg }">
        <div class="arm-hand"></div>
      </div>
      <div class="chibi-arm right" :style="{ background: outfit.outfitBg }">
        <div class="arm-hand"></div>
      </div>
    </div>

    <!-- 漂浮装饰 -->
    <div class="chibi-deco">
      <span class="deco-star" v-for="i in 4" :key="i" :style="{ animationDelay: (i * 0.7) + 's' }">
        {{ ['✨', '⭐', '💫', '🌟'][i-1] }}
      </span>
    </div>

    <!-- 声波 -->
    <div class="sound-wave" v-if="talking">
      <span v-for="i in 7" :key="i" :style="{ animationDelay: (i * 0.1) + 's' }"></span>
    </div>

    <!-- 字幕 -->
    <!-- 底部字幕栏已移除，统一使用顶部气泡 -->
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  outfit: { type: Object, default: () => ({
    hairStyle: 'bun', hairColor: '#3d2000',
    outfitBg: 'linear-gradient(180deg, #7dd3fc 0%, #0284c7 100%)',
    collarColor: '#e0f2fe', decoration: '🌸'
  })},
  talking: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  blinking: { type: Boolean, default: false },
  subtitle: { type: String, default: '' },
})

const hairStyle = computed(() => {
  const color = props.outfit.hairColor || '#3d2000'
  const adjusted = adjustColor(color, -20)
  return {
    background: `linear-gradient(180deg, ${color} 0%, ${adjusted} 100%)`
  }
})

function adjustColor(hex, amount) {
  const num = parseInt((hex || '#3d2000').replace('#', ''), 16)
  const r = Math.min(255, Math.max(0, (num >> 16) + amount))
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + amount))
  const b = Math.min(255, Math.max(0, (num & 0xff) + amount))
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)
}
</script>

<style scoped>
.chibi-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* 气泡对话框 */
.chibi-bubble {
  position: absolute;
  top: -70px; left: 60px;
  background: #fff; color: #333;
  border-radius: 14px; padding: 10px 16px;
  max-width: 200px; font-size: 14px; text-align: center; line-height: 1.5;
  box-shadow: 0 4px 14px rgba(0,0,0,0.15); z-index: 20;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chibi-bubble::after {
  content: ''; position: absolute;
  top: 50%; left: -10px; transform: translateY(-50%);
  border: 10px solid transparent;
  border-right-color: #fff; border-left: none;
}

/* 思考气泡 */
.think-bubble {
  position: absolute; top: -50px; right: -80px;
  background: #fff; color: #333;
  border-radius: 14px; padding: 8px 14px;
  font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 10; white-space: nowrap;
}
.think-bubble::before {
  content: ''; position: absolute;
  bottom: -8px; left: 20px;
  border: 8px solid transparent;
  border-top-color: #fff; border-bottom: none;
}
.think-dots { display: flex; gap: 4px; align-items: center; }
.think-dots span {
  width: 7px; height: 7px; border-radius: 50%;
  background: #60a5fa;
  animation: thinkBounce 1s ease-in-out infinite;
}
.think-dots span:nth-child(2) { animation-delay: 0.15s; background: #818cf8; }
.think-dots span:nth-child(3) { animation-delay: 0.3s; background: #a78bfa; }
@keyframes thinkBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* 数字人本体 */
.chibi {
  display: flex; flex-direction: column; align-items: center;
  position: relative; width: 100px;
  filter: drop-shadow(0 20px 40px rgba(0,0,0,0.35));
}
.chibi.thinking { animation: thinkingBob 1.2s ease-in-out infinite; }
.chibi.thinking .chibi-head { animation: thinkingTilt 2s ease-in-out infinite; }
@keyframes thinkingBob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
@keyframes thinkingTilt {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-3deg); }
  75% { transform: rotate(3deg); }
}
.chibi.talking .chibi-mouth { animation: talkAnim 0.2s infinite alternate; }
@keyframes talkAnim {
  from { height: 5px; width: 18px; }
  to { height: 13px; width: 26px; }
}

.chibi-hair {
  width: 120px; height: 65px;
  border-radius: 60px 60px 20px 20px;
  position: relative; display: flex; align-items: flex-end; justify-content: center;
  z-index: 1; overflow: visible;
}
.hair-deco {
  position: absolute; top: 12px; right: -2px;
  font-size: 22px; z-index: 5;
  animation: accessoryBounce 2s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
}
@keyframes accessoryBounce {
  0%, 100% { transform: translateY(0) rotate(-5deg); }
  50% { transform: translateY(-3px) rotate(5deg); }
}
.chibi-head {
  width: 100px; height: 100px; position: relative; z-index: 2; margin-top: -30px;
}
.chibi-face {
  width: 100%; height: 100%;
  background: linear-gradient(180deg, #ffe0c8 0%, #ffd4b0 60%, #ffcb9a 100%);
  border-radius: 50% 50% 48% 48%; position: relative;
  box-shadow: inset 0 -8px 16px rgba(255,180,120,0.25), 0 6px 20px rgba(255,180,120,0.25);
  animation: breathe 3s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}
.chibi-eyes {
  position: absolute; top: 30px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 24px;
}
.eye {
  width: 22px; height: 26px; background: #3d2000; border-radius: 50%;
  position: relative; overflow: hidden; transition: height 0.1s;
}
.eye.blink { height: 4px; top: 11px; }
.eye-highlight {
  position: absolute; top: 4px; left: 3px;
  width: 10px; height: 10px; background: #fff; border-radius: 50%;
}
.blush {
  position: absolute; bottom: 24px;
  width: 18px; height: 12px;
  background: rgba(255,100,100,0.35); border-radius: 50%; filter: blur(2px);
}
.blush.left { left: 8px; }
.blush.right { right: 8px; }
.chibi-mouth {
  position: absolute; bottom: 18px; left: 50%; transform: translateX(-50%);
  height: 3px; width: 16px;
  background: #c8604a; border-radius: 0 0 8px 8px;
  transition: all 0.2s;
}
.chibi-emotion { position: absolute; top: 8px; right: 8px; }
.emotion-dots {
  font-size: 16px; color: #888; font-weight: bold; letter-spacing: -2px;
  animation: dotsBlink 1s step-end infinite;
}
@keyframes dotsBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
.chibi-body {
  width: 80px; height: 68px; border-radius: 16px 16px 28px 28px;
  position: relative; z-index: 1; margin-top: -4px;
  box-shadow: 0 6px 16px rgba(0,0,0,0.2);
  display: flex; align-items: flex-start; justify-content: center;
}
.body-collar { width: 30px; height: 12px; border-radius: 0 0 15px 15px; margin-top: 0; flex-shrink: 0; }
.chibi-arm {
  position: absolute; width: 28px; height: 55px;
  border-radius: 14px; z-index: 3; top: 125px; transform-origin: top center;
}
.chibi-arm.left { left: -8px; animation: waveLeft 4s ease-in-out infinite; }
.chibi-arm.right { right: -8px; animation: waveRight 4s ease-in-out infinite 0.5s; }
@keyframes waveLeft {
  0%, 100% { transform: rotate(-5deg); }
  50% { transform: rotate(5deg); }
}
@keyframes waveRight {
  0%, 100% { transform: rotate(5deg); }
  50% { transform: rotate(-5deg); }
}
.arm-hand {
  position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%);
  width: 24px; height: 24px;
  background: linear-gradient(180deg, #ffe0c8, #ffd4b0); border-radius: 50%; z-index: 4;
}

/* 漂浮装饰 */
.chibi-deco {
  position: absolute; pointer-events: none; z-index: 10;
  top: -80px; left: -110px; width: 280px;
}
.deco-star {
  position: absolute; font-size: 14px;
  animation: floatStar 3s ease-in-out infinite; opacity: 0.6;
}
.deco-star:nth-child(1) { left: 5%; top: 10px; animation-duration: 2.5s; }
.deco-star:nth-child(2) { right: 5%; top: 0; animation-duration: 3.2s; animation-delay: 0.5s; }
.deco-star:nth-child(3) { left: 0; top: 50px; animation-duration: 2.8s; animation-delay: 1s; }
.deco-star:nth-child(4) { right: 0; top: 45px; animation-duration: 3.5s; animation-delay: 1.5s; }
@keyframes floatStar {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.6; }
  50% { transform: translateY(-8px) rotate(15deg); opacity: 1; }
}

/* 声波 */
.sound-wave {
  margin-top: 8px;
  display: flex; align-items: flex-end; gap: 4px; height: 30px;
}
.sound-wave span {
  width: 4px; background: rgba(74,222,128,0.8); border-radius: 2px;
  animation: soundWave 0.8s ease-in-out infinite alternate;
}
.sound-wave span:nth-child(1) { height: 8px; }
.sound-wave span:nth-child(2) { height: 16px; animation-delay: 0.1s; }
.sound-wave span:nth-child(3) { height: 26px; animation-delay: 0.2s; }
.sound-wave span:nth-child(4) { height: 30px; animation-delay: 0.15s; }
.sound-wave span:nth-child(5) { height: 22px; animation-delay: 0.25s; }
.sound-wave span:nth-child(6) { height: 14px; animation-delay: 0.05s; }
.sound-wave span:nth-child(7) { height: 6px; animation-delay: 0.3s; }
@keyframes soundWave { to { height: 4px; } }


</style>
