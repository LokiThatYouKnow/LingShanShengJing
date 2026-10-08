<template>
  <div class="real-wrapper">
    <!-- 对话气泡 -->
    <div class="speech-bubble" v-if="subtitle && talking">
      <span>{{ subtitle }}</span>
    </div>

    <!-- 思考状态 -->
    <div class="think-bubble" v-if="loading">
      <div class="think-dots"><span></span><span></span><span></span></div>
    </div>

    <!-- 真人数字人主体 -->
    <div class="real-char" :class="{ talking, loading, idle: !talking && !loading }">

      <!-- 头发层（头顶） -->
      <div class="real-hair-top"></div>

      <!-- 头部 -->
      <div class="real-head">
        <!-- 侧发 -->
        <div class="real-hair-side left"></div>
        <div class="real-hair-side right"></div>

        <!-- 脸 -->
        <div class="real-face">
          <!-- 额头阴影 -->
          <div class="forehead-shade"></div>

          <!-- 眉毛 -->
          <div class="real-brows">
            <div class="real-brow left" :class="{ thinking: loading }"></div>
            <div class="real-brow right" :class="{ thinking: loading }"></div>
          </div>

          <!-- 眼睛 -->
          <div class="real-eyes">
            <!-- 左眼 -->
            <div class="real-eye left" :class="{ blink: blinking }">
              <div class="eye-white">
                <div class="real-iris">
                  <div class="real-pupil"></div>
                  <div class="iris-detail"></div>
                </div>
                <div class="eye-shine"></div>
              </div>
              <div class="eye-lash upper"></div>
            </div>
            <!-- 右眼 -->
            <div class="real-eye right" :class="{ blink: blinking }">
              <div class="eye-white">
                <div class="real-iris">
                  <div class="real-pupil"></div>
                  <div class="iris-detail"></div>
                </div>
                <div class="eye-shine"></div>
              </div>
              <div class="eye-lash upper"></div>
            </div>
          </div>

          <!-- 鼻梁 -->
          <div class="real-nose"></div>

          <!-- 嘴（说话时口型动画） -->
          <div class="real-mouth" :class="{ talking, smile: !talking && !loading }">
            <div class="mouth-shape" v-if="!talking">
              <div class="lip-upper"></div>
              <div class="lip-lower"></div>
            </div>
            <div class="mouth-open" v-if="talking">
              <div class="teeth-row"></div>
              <div class="tongue"></div>
            </div>
          </div>

          <!-- 腮红（自然肤色） -->
          <div class="real-blush left"></div>
          <div class="real-blush right"></div>

          <!-- 下巴 -->
          <div class="chin"></div>
        </div>
      </div>

      <!-- 颈部 -->
      <div class="real-neck"></div>

      <!-- 上身（衬衫+外套） -->
      <div class="real-torso">
        <!-- 衬衫领 -->
        <div class="shirt-collar">
          <div class="collar-left"></div>
          <div class="collar-right"></div>
          <div class="collar-tie">
            <div class="tie-top"></div>
            <div class="tie-knot"></div>
            <div class="tie-body"></div>
          </div>
        </div>
        <!-- 外套主体 -->
        <div class="real-body">
          <!-- 扣子 -->
          <div class="button" v-for="i in 3" :key="i"></div>
          <!-- 口袋 -->
          <div class="pocket left"></div>
          <div class="pocket-card right"></div>
        </div>
        <!-- 肩线 -->
        <div class="shoulder-line left"></div>
        <div class="shoulder-line right"></div>
      </div>

      <!-- 左臂 -->
      <div class="real-arm left">
        <div class="upper-arm"></div>
        <div class="lower-arm">
          <div class="hand">
            <div class="finger-tips">
              <div class="finger" v-for="i in 4" :key="i"></div>
            </div>
            <div class="thumb"></div>
          </div>
        </div>
      </div>

      <!-- 右臂 -->
      <div class="real-arm right">
        <div class="upper-arm"></div>
        <div class="lower-arm">
          <div class="hand">
            <div class="finger-tips">
              <div class="finger" v-for="i in 4" :key="i"></div>
            </div>
            <div class="thumb"></div>
          </div>
        </div>
      </div>

      <!-- 腰带 -->
      <div class="real-belt">
        <div class="belt-buckle"></div>
      </div>

      <!-- 裤子（双腿） -->
      <div class="real-legs">
        <div class="leg left">
          <div class="leg-upper"></div>
          <div class="knee"></div>
          <div class="leg-lower">
            <div class="sock"></div>
            <div class="shoe"></div>
          </div>
        </div>
        <div class="leg right">
          <div class="leg-upper"></div>
          <div class="knee"></div>
          <div class="leg-lower">
            <div class="sock"></div>
            <div class="shoe"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 声波指示 -->
    <div class="wave-bars" v-if="talking">
      <span v-for="i in 12" :key="i" class="wave-bar"></span>
    </div>

    <!-- 字幕 -->
    <div class="real-subtitle" :class="{ visible: subtitle && talking }">
      {{ subtitle }}
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  talking:  { type: Boolean, default: false },
  loading:  { type: Boolean, default: false },
  blinking: { type: Boolean, default: false },
  subtitle: { type: String,  default: '' },
})
</script>

<style scoped>
/* ===== 整体包裹 ===== */
.real-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* 对话气泡 */
.speech-bubble {
  position: absolute; top: -62px; left: 60px;
  background: linear-gradient(135deg, #fff 0%, #f5f5f5 100%);
  color: #333; border-radius: 16px; padding: 10px 18px;
  max-width: 320px; font-size: 14px; text-align: center; line-height: 1.5;
  box-shadow: 0 6px 20px rgba(0,0,0,0.2); z-index: 20;
  border: 1px solid rgba(0,0,0,0.08);
  word-break: break-all;
}
.speech-bubble::after {
  content: ''; position: absolute;
  top: 50%; left: -10px; transform: translateY(-50%);
  border: 8px solid transparent;
  border-right-color: #fff; border-left: none;
}

/* 思考气泡 */
.think-bubble {
  position: absolute; top: -48px; right: -60px;
  background: #fff; border-radius: 14px; padding: 8px 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10;
}
.think-dots { display: flex; gap: 4px; align-items: center; }
.think-dots span {
  width: 7px; height: 7px; border-radius: 50%;
  background: #555; animation: tBounce 1s ease-in-out infinite;
}
.think-dots span:nth-child(2) { animation-delay: 0.15s; background: #777; }
.think-dots span:nth-child(3) { animation-delay: 0.3s; background: #999; }
@keyframes tBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* ===== 主体 ===== */
.real-char {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: realIdle 4s ease-in-out infinite;
}
@keyframes realIdle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
.real-char.loading { animation: realThink 2s ease-in-out infinite; }
@keyframes realThink {
  0%, 100% { transform: translateY(0); }
  40% { transform: translateY(-5px) rotate(-1deg); }
  70% { transform: translateY(-3px) rotate(1deg); }
}

/* ===== 头发层（头顶） ===== */
.real-hair-top {
  width: 130px; height: 70px;
  background: linear-gradient(180deg, #1a0f08 0%, #2c1810 40%, #1a0f08 100%);
  border-radius: 65px 65px 20px 20px;
  position: relative; z-index: 5;
  box-shadow: inset 0 -5px 15px rgba(0,0,0,0.3), 0 2px 8px rgba(0,0,0,0.4);
}
.real-hair-top::before {
  content: ''; position: absolute;
  top: 10px; left: 50%; transform: translateX(-50%);
  width: 100px; height: 40px;
  background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, transparent 100%);
  border-radius: 50px 50px 0 0;
}

/* ===== 头部 ===== */
.real-head {
  position: relative;
  width: 120px;
  margin-top: -10px;
  z-index: 4;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 侧发 */
.real-hair-side {
  position: absolute; top: 20px;
  width: 18px; height: 90px;
  background: linear-gradient(180deg, #1a0f08 0%, #2c1810 50%, #1a0f08 100%);
  border-radius: 0 0 9px 9px;
  z-index: 6;
}
.real-hair-side.left { left: 0; }
.real-hair-side.right { right: 0; }

/* 脸 */
.real-face {
  width: 108px; height: 135px;
  background: linear-gradient(180deg, #f5e0cc 0%, #eccfb8 50%, #e0c0a4 100%);
  border-radius: 50% 50% 46% 46%;
  position: relative;
  box-shadow:
    inset 0 -15px 25px rgba(160,100,60,0.12),
    inset 0 5px 15px rgba(255,220,190,0.2),
    0 4px 16px rgba(0,0,0,0.25);
  z-index: 3;
  overflow: hidden;
}

/* 额头阴影 */
.forehead-shade {
  position: absolute; top: 0; left: 0; right: 0;
  height: 18px;
  background: linear-gradient(180deg, rgba(0,0,0,0.04) 0%, transparent 100%);
  border-radius: 50% 50% 0 0;
}

/* 眉毛 */
.real-brows {
  position: absolute; top: 26px; left: 50%; transform: translateX(-50%);
  width: 84px; display: flex; justify-content: space-between;
}
.real-brow {
  width: 28px; height: 4px;
  background: linear-gradient(90deg, #2c1810, #3a2010);
  border-radius: 2px;
  transform: rotate(-6deg);
  transition: transform 0.3s;
}
.real-brow.right { transform: rotate(6deg); }
.real-brow.thinking { transform: rotate(-12deg) translateY(-2px); }
.real-brow.right.thinking { transform: rotate(12deg) translateY(-2px); }

/* 眼睛 */
.real-eyes {
  position: absolute; top: 40px; left: 50%; transform: translateX(-50%);
  width: 84px; display: flex; justify-content: space-between;
}
.real-eye {
  width: 34px; height: 22px;
  position: relative;
  transition: height 0.1s;
}
.real-eye.blink { height: 4px; }

.eye-white {
  width: 34px; height: 22px;
  background: #fff;
  border-radius: 50% 50% 45% 45%;
  overflow: hidden;
  border: 1px solid rgba(0,0,0,0.08);
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.real-eye.blink .eye-white { border-radius: 50%; }

.real-iris {
  width: 18px; height: 18px;
  background: radial-gradient(circle at 40% 35%,
    #5c3317 0%,
    #3d2210 40%,
    #1a0f08 70%,
    #0a0500 100%);
  border-radius: 50%;
  position: relative;
  display: flex; align-items: center; justify-content: center;
}
.real-pupil {
  width: 8px; height: 9px;
  background: radial-gradient(circle, #000 60%, #0a0a0a 100%);
  border-radius: 50%;
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
}
.iris-detail {
  position: absolute; inset: 0;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15) 0%, transparent 50%),
    repeating-conic-gradient(from 0deg, transparent 0deg 30deg, rgba(80,40,10,0.15) 30deg 32deg);
}
.eye-shine {
  position: absolute; width: 6px; height: 6px;
  background: rgba(255,255,255,0.85); border-radius: 50%;
  top: 22%; left: 22%;
  box-shadow: 0 0 2px rgba(255,255,255,0.5);
}
.eye-lash.upper {
  position: absolute; top: -2px; left: 50%; transform: translateX(-50%);
  width: 36px; height: 5px;
  border-top: 2.5px solid #1a0f08;
  border-radius: 50% 50% 0 0;
}

/* 鼻梁 */
.real-nose {
  position: absolute; top: 68px; left: 50%; transform: translateX(-50%);
  width: 10px; height: 14px;
  border-bottom: 2px solid rgba(160,100,60,0.3);
  border-radius: 0 0 50% 50%;
  background: linear-gradient(180deg, transparent 0%, rgba(160,100,60,0.1) 100%);
}

/* 嘴 */
.real-mouth {
  position: absolute; bottom: 22px; left: 50%; transform: translateX(-50%);
  width: 30px; display: flex; flex-direction: column; align-items: center;
}
.mouth-shape {
  display: flex; flex-direction: column; align-items: center; gap: 1px;
}
.lip-upper {
  width: 26px; height: 5px;
  background: linear-gradient(90deg, #c07060, #d08070, #c07060);
  border-radius: 50% 50% 0 0;
}
.lip-lower {
  width: 24px; height: 6px;
  background: linear-gradient(90deg, #d08880, #e09090, #d08880);
  border-radius: 0 0 50% 50%;
}
.mouth-open {
  width: 22px; display: flex; flex-direction: column; align-items: center;
  animation: mouthSync 0.15s ease-in-out infinite alternate;
}
@keyframes mouthSync {
  from { height: 6px; }
  to { height: 16px; }
}
.teeth-row {
  width: 18px; height: 5px;
  background: #f8f8f0; border-radius: 2px;
  flex-shrink: 0;
}
.tongue {
  width: 12px; height: 5px;
  background: #e07070; border-radius: 0 0 50% 50%;
  flex-shrink: 0;
}
.real-mouth.smile .lip-lower { border-radius: 0 0 60% 60%; transform: scaleY(1.1); }

/* 腮红 */
.real-blush {
  position: absolute; bottom: 36px;
  width: 18px; height: 10px;
  background: rgba(240,140,120,0.25); border-radius: 50%;
  filter: blur(4px);
}
.real-blush.left { left: 6px; }
.real-blush.right { right: 6px; }

/* 下巴 */
.chin {
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 80px; height: 12px;
  background: linear-gradient(180deg, transparent 0%, rgba(200,150,110,0.1) 100%);
  border-radius: 0 0 50% 50%;
}

/* ===== 颈部 ===== */
.real-neck {
  width: 36px; height: 32px;
  background: linear-gradient(180deg, #eccfb8, #e0c0a4);
  margin-top: -8px; z-index: 2;
  position: relative;
}
.real-neck::after {
  content: ''; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 28px; height: 6px;
  background: rgba(0,0,0,0.08); border-radius: 0 0 50% 50%;
}

/* ===== 上身 ===== */
.real-torso {
  display: flex; flex-direction: column; align-items: center;
  position: relative; z-index: 2;
}

/* 衬衫领 */
.shirt-collar {
  position: relative; display: flex; justify-content: center;
  z-index: 3; margin-bottom: -4px;
}
.collar-left, .collar-right {
  width: 30px; height: 28px;
  background: #f0f0ee;
  clip-path: polygon(0 0, 100% 30%, 60% 100%, 0 100%);
}
.collar-right {
  clip-path: polygon(0 30%, 100% 0, 100% 100%, 40% 100%);
}
.collar-tie {
  position: absolute; top: 0; display: flex; flex-direction: column; align-items: center;
}
.tie-top {
  width: 8px; height: 8px;
  background: #8b1a1a;
  clip-path: polygon(20% 0, 80% 0, 100% 100%, 0 100%);
}
.tie-knot {
  width: 10px; height: 8px;
  background: #a02020;
  border-radius: 2px; margin-top: -2px;
}
.tie-body {
  width: 14px; height: 40px;
  background: linear-gradient(180deg, #8b1a1a, #6b1010);
  clip-path: polygon(10% 0, 90% 0, 100% 100%, 0 100%);
  margin-top: -1px;
}

/* 外套主体 */
.real-body {
  width: 130px; height: 110px;
  background: linear-gradient(180deg, #1e2535 0%, #2c3545 60%, #1e2535 100%);
  border-radius: 8px 8px 0 0;
  position: relative;
  box-shadow: 0 4px 20px rgba(0,0,0,0.35);
  display: flex; flex-direction: column; align-items: center;
  animation: bodyBreath 4s ease-in-out infinite;
}
@keyframes bodyBreath {
  0%, 100% { transform: scaleX(1); }
  50% { transform: scaleX(1.003); }
}

.button {
  width: 8px; height: 8px; border-radius: 50%;
  background: linear-gradient(135deg, #c0c0b8, #909090);
  box-shadow: inset 0 1px 2px rgba(255,255,255,0.3), 0 1px 2px rgba(0,0,0,0.3);
  margin-top: 20px;
}
.button:nth-child(1) { margin-top: 18px; }
.button:nth-child(2) { margin-top: 16px; }
.button:nth-child(3) { margin-top: 14px; }

.pocket {
  position: absolute; left: 12px; top: 55px;
  width: 28px; height: 22px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 0 0 4px 4px;
  background: rgba(0,0,0,0.08);
}
.pocket-card {
  position: absolute; right: 14px; top: 22px;
  width: 20px; height: 14px;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 2px;
  background: rgba(255,255,255,0.04);
}
.shoulder-line {
  position: absolute; top: 0;
  width: 30px; height: 3px;
  background: rgba(255,255,255,0.06);
  border-radius: 0 0 4px 4px;
}
.shoulder-line.left { left: 0; }
.shoulder-line.right { right: 0; }

/* ===== 手臂 ===== */
.real-arm {
  position: absolute; top: 195px;
  display: flex; flex-direction: column; align-items: center;
  z-index: 1;
  transform-origin: top center;
}
.real-arm.left {
  left: 4px;
  animation: armStill 4s ease-in-out infinite;
}
.real-arm.right {
  right: 4px;
  animation: armStill 4s ease-in-out infinite 0.3s;
}
@keyframes armStill {
  0%, 100% { transform: rotate(-2deg); }
  50% { transform: rotate(2deg); }
}

.upper-arm {
  width: 28px; height: 55px;
  background: linear-gradient(180deg, #1e2535, #2c3545);
  border-radius: 8px;
}
.lower-arm {
  width: 26px; height: 50px;
  background: linear-gradient(180deg, #1e2535 0%, #e0c0a4 55%);
  border-radius: 0 0 8px 8px;
  position: relative;
}
.hand {
  position: absolute; bottom: -10px; left: 50%; transform: translateX(-50%);
  width: 24px; height: 26px;
  background: linear-gradient(135deg, #eccfb8, #e0c0a4);
  border-radius: 50% 50% 40% 40%;
  display: flex; justify-content: center; align-items: flex-end; padding: 2px;
}
.finger-tips { display: flex; gap: 2px; }
.finger {
  width: 4px; height: 9px;
  background: linear-gradient(180deg, #e8ccb8, #d8bca8);
  border-radius: 2px;
}
.thumb {
  position: absolute; left: -5px; top: 4px;
  width: 8px; height: 10px;
  background: linear-gradient(135deg, #eccfb8, #e0c0a4);
  border-radius: 50% 50% 40% 40%;
  transform: rotate(-20deg);
}

/* ===== 腰带 ===== */
.real-belt {
  width: 128px; height: 14px;
  background: linear-gradient(180deg, #1a1208, #2c1c0a);
  border-radius: 0 0 4px 4px;
  display: flex; align-items: center; justify-content: center;
  margin-top: -2px; z-index: 3;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
.belt-buckle {
  width: 20px; height: 10px;
  background: linear-gradient(135deg, #d4af37, #c09020);
  border-radius: 3px;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

/* ===== 裤子+双腿 ===== */
.real-legs {
  display: flex; gap: 6px;
  position: relative; z-index: 1;
}
.leg {
  display: flex; flex-direction: column; align-items: center;
  position: relative;
}
.leg.left { animation: legIdleL 4s ease-in-out infinite; }
.leg.right { animation: legIdleR 4s ease-in-out infinite 0.5s; }
@keyframes legIdleL {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(0.5deg); }
}
@keyframes legIdleR {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(-0.5deg); }
}

.leg-upper {
  width: 52px; height: 70px;
  background: linear-gradient(180deg, #1e2535 0%, #2c3545 100%);
  border-radius: 0 0 4px 4px;
  position: relative;
}
.leg-upper::before {
  content: ''; position: absolute;
  top: 0; left: 0; right: 0;
  height: 8px;
  background: rgba(255,255,255,0.04);
}

.knee {
  width: 48px; height: 16px;
  background: linear-gradient(180deg, #1e2535, #2c3545);
  border-radius: 0;
  position: relative;
}

.leg-lower {
  display: flex; flex-direction: column; align-items: center;
}
.sock {
  width: 46px; height: 65px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 60%, #f0f0f0 100%);
  border-radius: 0 0 4px 4px;
}
.shoe {
  width: 50px; height: 22px;
  background: linear-gradient(180deg, #1a1a1a, #0a0a0a);
  border-radius: 4px 12px 4px 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  position: relative;
}
.shoe::after {
  content: ''; position: absolute;
  bottom: 0; left: 0; right: 0; height: 4px;
  background: rgba(255,255,255,0.04);
  border-radius: 0 0 4px 4px;
}

/* ===== 声波 ===== */
.wave-bars {
  margin-top: 10px; display: flex; align-items: flex-end;
  gap: 3px; height: 28px;
}
.wave-bar {
  width: 4px; border-radius: 2px;
  background: linear-gradient(180deg, #555, #333);
  animation: wbAnim 0.5s ease-in-out infinite alternate;
}
.wave-bar:nth-child(odd) { animation-delay: 0.1s; }
.wave-bar:nth-child(3n) { animation-delay: 0.2s; }
@keyframes wbAnim {
  from { height: 5px; }
  to { height: 26px; }
}

/* 字幕 */
.real-subtitle {
  margin-top: 10px; min-height: 40px;
  background: rgba(0,0,0,0.72); backdrop-filter: blur(8px);
  border-radius: 12px; padding: 8px 18px;
  font-size: 15px; text-align: center; line-height: 1.6;
  color: #f0f0f0;
  opacity: 0; transition: opacity 0.3s;
  max-width: 100%; width: fit-content;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  word-break: break-all;
}
.real-subtitle.visible { opacity: 1; }
</style>
