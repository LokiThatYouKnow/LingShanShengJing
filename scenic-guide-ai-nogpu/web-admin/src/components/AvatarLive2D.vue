<template>
  <div class="anime-wrapper">
    <!-- 对话气泡 -->
    <div class="speech-bubble" v-if="subtitle && talking">
      <span>{{ subtitle }}</span>
    </div>

    <!-- 思考状态 -->
    <div class="think-bubble" v-if="loading">
      <div class="think-dots"><span></span><span></span><span></span></div>
    </div>

    <!-- 日漫风格人物主体（全身） -->
    <div class="anime-char" :class="{ talking, thinking: loading, idle: !talking && !loading }">

      <!-- 头发（后层） -->
      <div class="a-hair-back" :class="hairStyle" :style="hairBackStyle"></div>

      <!-- 头部 -->
      <div class="a-head-group">
        <!-- 侧发 -->
        <div class="a-hair-side left" :class="hairStyle" :style="hairSideStyle">
          <div class="hair-strand"></div>
          <div class="hair-strand"></div>
          <div class="hair-strand twin-tail-strand" v-if="hairStyle === 'twin-tail'"></div>
        </div>
        <div class="a-hair-side right" :class="hairStyle" :style="hairSideStyle">
          <div class="hair-strand"></div>
          <div class="hair-strand"></div>
          <div class="hair-strand twin-tail-strand" v-if="hairStyle === 'twin-tail'"></div>
        </div>

        <!-- 脸 -->
        <div class="a-face" :style="{ background: faceGradient }">
          <!-- 耳朵 -->
          <div class="a-ear left" :style="{ background: skinColor }"></div>
          <div class="a-ear right" :style="{ background: skinColor }"></div>

          <!-- 眉毛 -->
          <div class="a-brows">
            <div class="a-brow left" :class="{ thinking: loading }" :style="{ background: browColor }"></div>
            <div class="a-brow right" :class="{ thinking: loading }" :style="{ background: browColor }"></div>
          </div>

          <!-- 眼睛 -->
          <div class="a-eyes">
            <!-- 左眼 -->
            <div class="a-eye-wrap left">
              <div class="a-eye" :class="{ blink: blinking }">
                <div class="a-eyeball">
                  <div class="a-eye-base" :style="{ background: skinColor }"></div>
                  <div class="a-iris-wrap">
                    <div class="a-iris" :style="{ background: irisGradient }">
                      <div class="a-pupil"></div>
                      <div class="iris-star"></div>
                    </div>
                  </div>
                  <div class="a-shine"></div>
                  <div class="a-shine2"></div>
                  <div class="a-lash top"></div>
                  <div class="a-lash bottom"></div>
                </div>
              </div>
            </div>
            <!-- 右眼 -->
            <div class="a-eye-wrap right">
              <div class="a-eye" :class="{ blink: blinking }">
                <div class="a-eyeball">
                  <div class="a-eye-base" :style="{ background: skinColor }"></div>
                  <div class="a-iris-wrap">
                    <div class="a-iris" :style="{ background: irisGradient }">
                      <div class="a-pupil"></div>
                      <div class="iris-star"></div>
                    </div>
                  </div>
                  <div class="a-shine"></div>
                  <div class="a-shine2"></div>
                  <div class="a-lash top"></div>
                  <div class="a-lash bottom"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 鼻子 -->
          <div class="a-nose"></div>

          <!-- 嘴 -->
          <div class="a-mouth" :class="{ talking, smile: !talking && !loading }">
            <div class="a-lip-wrap" v-if="!talking">
              <div class="a-upper-lip" :style="{ background: lipColor }"></div>
              <div class="a-lower-lip" :style="{ background: lipLowerColor }"></div>
            </div>
            <div class="a-mouth-open" v-if="talking">
              <div class="a-teeth"></div>
              <div class="a-tongue"></div>
            </div>
          </div>

          <!-- 腮红 -->
          <div class="a-blush left"></div>
          <div class="a-blush right"></div>

          <!-- 下巴 -->
          <div class="a-chin"></div>
        </div>

        <!-- 刘海（前层） -->
        <div class="a-bangs" :class="hairStyle" :style="{ background: hairGradient }">
          <div class="bang-strand c1"></div>
          <div class="bang-strand c2"></div>
          <div class="bang-strand c3"></div>
          <div class="bang-strand c4"></div>
          <div class="bang-strand c5"></div>
          <!-- 发饰 -->
          <div class="a-ornament" v-if="ornament">{{ ornament }}</div>
        </div>
      </div>

      <!-- 颈部 -->
      <div class="a-neck" :style="{ background: skinColor }"></div>

      <!-- 身体/上衣 -->
      <div class="a-torso" :class="clothStyle" :style="{ background: outfitGradient }">
        <!-- 手臂（放在身体内部） -->
        <div class="a-arm left" :style="{ '--skin': skinColor }">
          <div class="a-sleeve" :class="clothStyle" :style="{ background: outfitGradient }"></div>
          <div class="a-forearm" :style="{ background: skinColor }">
            <div class="a-hand" :style="{ background: skinColor }">
              <div class="a-finger" v-for="i in 4" :key="i"></div>
              <div class="a-thumb"></div>
            </div>
          </div>
        </div>
        <div class="a-arm right" :style="{ '--skin': skinColor }">
          <div class="a-sleeve" :class="clothStyle" :style="{ background: outfitGradient }"></div>
          <div class="a-forearm" :style="{ background: skinColor }">
            <div class="a-hand" :style="{ background: skinColor }">
              <div class="a-finger" v-for="i in 4" :key="i"></div>
              <div class="a-thumb"></div>
            </div>
          </div>
        </div>
        <!-- 领口（根据衣服样式变化） -->
        <div class="a-collar" :class="clothStyle" :style="{ borderBottomColor: accentColor }">
          <div class="collar-flap left" :class="clothStyle" :style="{ background: accentColor }"></div>
          <div class="collar-flap right" :class="clothStyle" :style="{ background: accentColor }"></div>
        </div>
        <!-- 衣服细节 -->
        <div class="a-cloth-line" :class="clothStyle"></div>
        <!-- 蝴蝶结 -->
        <div class="a-bow" v-if="hasBow" :style="{ color: bowColor }">{{ bowStyle }}</div>
        <!-- 衣服纹理 -->
        <div class="cloth-pattern" :class="clothStyle"></div>
      </div>

      <!-- 短裙/下装 -->
      <div class="a-skirt" :class="clothStyle" :style="{ background: skirtGradient }">
        <div class="skirt-pleat" v-for="i in 6" :key="i"></div>
        <div class="skirt-waist" :style="{ background: accentColor }"></div>
      </div>

      <!-- 腿部（日漫大腿+小腿+鞋） -->
      <div class="a-legs">
        <!-- 左腿 -->
        <div class="a-leg left">
          <div class="a-thigh" :style="{ background: skinColor }"></div>
          <div class="a-knee" :style="{ background: skinColor }"></div>
          <div class="a-calf" :style="{ background: skinColor }"></div>
          <div class="a-sock" :class="sockStyle" :style="{ background: sockColor }"></div>
          <div class="a-shoe" :class="shoeStyle" :style="{ background: shoeColor }">
            <div class="shoe-bow" v-if="hasBow" :style="{ color: bowColor }">◆</div>
          </div>
        </div>
        <!-- 右腿 -->
        <div class="a-leg right">
          <div class="a-thigh" :style="{ background: skinColor }"></div>
          <div class="a-knee" :style="{ background: skinColor }"></div>
          <div class="a-calf" :style="{ background: skinColor }"></div>
          <div class="a-sock" :class="sockStyle" :style="{ background: sockColor }"></div>
          <div class="a-shoe" :class="shoeStyle" :style="{ background: shoeColor }">
            <div class="shoe-bow" v-if="hasBow" :style="{ color: bowColor }">◆</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 声波指示 -->
    <div class="a-wave" v-if="talking">
      <span v-for="i in 6" :key="i" :style="{ background: irisColor }"></span>
    </div>


    <!-- 底部字幕已移除，统一使用顶部气泡 -->
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  talking: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  blinking: { type: Boolean, default: false },
  subtitle: { type: String, default: '' },
  outfit: { type: Object, default: () => ({
    hairColor: '#7c3aed',
    irisColor: '#8b5cf6',
    skinColor: '#ffe0cc',
    outfitColor: '#e879f9',
    outfitAccent: '#a855f7',
    skirtColor: '#d946ef',
    ornament: '🌸',
    hasBow: true,
    bowColor: '#f472b6',
    sockColor: '#f5f5f5',
    shoeColor: '#581c87',
  })}
})

const hairColor = computed(() => props.outfit?.hairColor || '#7c3aed')
const irisColor = computed(() => props.outfit?.irisColor || '#8b5cf6')
const skinColor = computed(() => props.outfit?.skinColor || '#ffe0cc')
const outfitColor = computed(() => props.outfit?.outfitColor || '#e879f9')
const outfitAccent = computed(() => props.outfit?.outfitAccent || '#a855f7')
const skirtColor = computed(() => props.outfit?.skirtColor || '#d946ef')
const ornament = computed(() => props.outfit?.ornament || '🌸')
const hasBow = computed(() => props.outfit?.hasBow ?? true)
const bowStyle = computed(() => props.outfit?.bowStyle || '🎀')
const bowColor = computed(() => props.outfit?.bowColor || '#f472b6')
const sockColor = computed(() => props.outfit?.sockColor || '#f5f5f5')
const shoeColor = computed(() => props.outfit?.shoeColor || '#581c87')

// 样式类型
const hairStyle = computed(() => props.outfit?.hairStyle || 'long-straight')
const clothStyle = computed(() => props.outfit?.clothStyle || 'dress')
const sockStyle = computed(() => props.outfit?.sockStyle || 'long')
const shoeStyle = computed(() => props.outfit?.shoeStyle || 'mary-jane')

function darken(hex, amount) {
  try {
    const num = parseInt(hex.replace('#', ''), 16)
    const r = Math.min(255, Math.max(0, (num >> 16) - amount))
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) - amount))
    const b = Math.min(255, Math.max(0, (num & 0xff) - amount))
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)
  } catch { return hex }
}

const hairGradient = computed(() =>
  `linear-gradient(180deg, ${hairColor.value} 0%, ${darken(hairColor.value, 15)} 100%)`
)
const hairBackStyle = computed(() => ({ background: hairGradient.value }))
const hairSideStyle = computed(() => ({
  background: `linear-gradient(180deg, ${hairColor.value} 0%, ${darken(hairColor.value, 20)} 100%)`
}))
const faceGradient = computed(() =>
  `linear-gradient(180deg, ${skinColor.value} 0%, ${darken(skinColor.value, 5)} 80%, ${darken(skinColor.value, 10)} 100%)`
)
const browColor = computed(() => darken(hairColor.value, 30))
const irisGradient = computed(() =>
  `radial-gradient(circle at 40% 35%, ${irisColor.value} 0%, ${darken(irisColor.value, 20)} 50%, ${darken(irisColor.value, 40)} 100%)`
)
const lipColor = computed(() => '#e06070')
const lipLowerColor = computed(() => '#f08080')
const outfitGradient = computed(() =>
  `linear-gradient(180deg, ${outfitColor.value} 0%, ${darken(outfitColor.value, 12)} 100%)`
)
const accentColor = computed(() => outfitAccent.value)
const skirtGradient = computed(() =>
  `linear-gradient(180deg, ${skirtColor.value} 0%, ${darken(skirtColor.value, 15)} 100%)`
)
</script>

<style scoped>
.anime-wrapper {
  display: flex; flex-direction: column; align-items: center;
  position: relative;
  filter: drop-shadow(0 20px 40px rgba(0,0,0,0.35));
}
.speech-bubble {
  position: absolute; top: -60px; left: 70px;
  background: linear-gradient(135deg, #fff 0%, #f8f0ff 100%);
  color: #333; border-radius: 18px; padding: 10px 18px;
  max-width: 320px; font-size: 14px; text-align: center; line-height: 1.5;
  box-shadow: 0 6px 20px rgba(139,92,246,0.2); z-index: 20;
  border: 1px solid rgba(139,92,246,0.15);
  word-break: break-all;
}
.speech-bubble::after {
  content: ''; position: absolute;
  top: 50%; left: -10px; transform: translateY(-50%);
  border: 8px solid transparent;
  border-right-color: #fff; border-left: none;
}
.think-bubble {
  position: absolute; top: -45px; right: -65px;
  background: #fff; border-radius: 14px; padding: 8px 14px;
  box-shadow: 0 4px 12px rgba(139,92,246,0.15); z-index: 10;
}
.think-dots { display: flex; gap: 4px; align-items: center; }
.think-dots span {
  width: 7px; height: 7px; border-radius: 50%;
  background: #8b5cf6; animation: tBounce 1s ease-in-out infinite;
}
.think-dots span:nth-child(2) { animation-delay: 0.15s; background: #a78bfa; }
.think-dots span:nth-child(3) { animation-delay: 0.3s; background: #c4b5fd; }
@keyframes tBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}
.anime-char {
  position: relative;
  display: flex; flex-direction: column; align-items: center;
}
.a-hair-back {
  position: absolute;
  top: -5px; left: 50%; transform: translateX(-50%);
  width: 135px; height: 175px;
  border-radius: 68px 68px 35px 35px;
  z-index: 0;
  box-shadow: inset -8px 0 20px rgba(0,0,0,0.1);
}
.a-head-group {
  position: relative;
  width: 145px; height: 165px;
  z-index: 4;
  animation: animeIdle 4s ease-in-out infinite;
}
@keyframes animeIdle {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-4px) rotate(0.8deg); }
  75% { transform: translateY(-2px) rotate(-0.8deg); }
}
.anime-char.thinking .a-head-group {
  animation: animeThink 2s ease-in-out infinite;
}
@keyframes animeThink {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  35% { transform: translateY(-7px) rotate(-3deg); }
  65% { transform: translateY(-5px) rotate(3deg); }
}
.a-face {
  position: absolute; top: 22px; left: 50%; transform: translateX(-50%);
  width: 112px; height: 132px;
  border-radius: 50% 50% 46% 46%;
  box-shadow:
    inset 0 -12px 20px rgba(200,140,80,0.15),
    inset 0 4px 12px rgba(255,220,180,0.2),
    0 4px 14px rgba(0,0,0,0.2);
  z-index: 2; overflow: hidden;
}
.a-ear {
  position: absolute; top: 58px;
  width: 16px; height: 20px; border-radius: 50%; z-index: 1;
}
.a-ear.left { left: -7px; }
.a-ear.right { right: -7px; }
.a-brows {
  position: absolute; top: 26px; left: 50%; transform: translateX(-50%);
  width: 86px; display: flex; justify-content: space-between;
}
.a-brow {
  width: 28px; height: 4px; border-radius: 2px;
  transform: rotate(-8deg); transition: transform 0.3s;
}
.a-brow.right { transform: rotate(8deg); }
.a-brow.thinking { transform: rotate(-16deg) translateY(-2px); }
.a-brow.right.thinking { transform: rotate(16deg) translateY(-2px); }
.a-eyes {
  position: absolute; top: 40px; left: 50%; transform: translateX(-50%);
  width: 92px; display: flex; justify-content: space-between;
}
.a-eye-wrap { position: relative; width: 38px; }
.a-eye {
  width: 38px; height: 28px; position: relative;
  transition: height 0.1s;
}
.a-eye.blink { height: 5px; }
.a-eyeball {
  width: 38px; height: 28px;
  border-radius: 50% 50% 42% 42%;
  overflow: hidden; position: relative;
  border: 1.5px solid rgba(0,0,0,0.1);
}
.a-eye.blink .a-eyeball { border-radius: 50%; }
.a-eye-base { position: absolute; inset: 0; border-radius: inherit; }
.a-iris-wrap {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
}
.a-iris {
  width: 20px; height: 22px; border-radius: 50%;
  position: relative; overflow: hidden;
}
.a-pupil {
  position: absolute; width: 9px; height: 10px;
  background: #0a0510; border-radius: 50%;
  top: 50%; left: 50%; transform: translate(-50%, -50%);
}
.iris-star {
  position: absolute; inset: 0; border-radius: 50%;
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.2) 0%, transparent 50%),
    repeating-conic-gradient(from 0deg, transparent 0deg 36deg, rgba(255,255,255,0.06) 36deg 40deg);
}
.a-shine {
  position: absolute; width: 9px; height: 9px;
  background: rgba(255,255,255,0.92); border-radius: 50%;
  top: 20%; left: 20%;
  box-shadow: 0 0 3px rgba(255,255,255,0.5);
}
.a-shine2 {
  position: absolute; width: 5px; height: 5px;
  background: rgba(255,255,255,0.7); border-radius: 50%;
  bottom: 22%; right: 22%;
}
.a-lash.top {
  position: absolute; top: -3px; left: 50%; transform: translateX(-50%);
  width: 40px; height: 6px;
  border-top: 2.5px solid rgba(40,20,60,0.85);
  border-radius: 50% 50% 0 0;
}
.a-lash.bottom {
  position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%);
  width: 30px; height: 4px;
  border-bottom: 2px solid rgba(40,20,60,0.3);
  border-radius: 0 0 50% 50%;
}
.a-nose {
  position: absolute; top: 78px; left: 50%; transform: translateX(-50%);
  width: 8px; height: 5px;
  border-bottom: 2px solid rgba(180,100,60,0.35);
  border-radius: 0 0 50% 50%;
}
.a-mouth {
  position: absolute; bottom: 22px; left: 50%; transform: translateX(-50%);
  width: 28px; display: flex; flex-direction: column; align-items: center;
}
.a-lip-wrap { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.a-upper-lip { width: 26px; height: 5px; border-radius: 50% 50% 0 0; }
.a-lower-lip { width: 24px; height: 7px; border-radius: 0 0 50% 50%; }
.a-mouth-open {
  width: 20px; display: flex; flex-direction: column; align-items: center;
  animation: aMouth 0.15s ease-in-out infinite alternate;
}
@keyframes aMouth { from { height: 5px; } to { height: 14px; } }
.a-teeth { width: 16px; height: 5px; background: #f8f8f0; border-radius: 2px; flex-shrink: 0; }
.a-tongue { width: 10px; height: 5px; background: #e07070; border-radius: 0 0 50% 50%; flex-shrink: 0; }
.a-mouth.smile .a-lower-lip { border-radius: 0 0 60% 60%; }
.a-blush {
  position: absolute; bottom: 36px;
  width: 22px; height: 12px;
  background: rgba(255,130,130,0.3); border-radius: 50%; filter: blur(3px);
}
.a-blush.left { left: 7px; }
.a-blush.right { right: 7px; }
.a-chin {
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 70px; height: 10px;
  background: linear-gradient(180deg, transparent 0%, rgba(200,150,100,0.08) 100%);
  border-radius: 0 0 50% 50%;
}
.a-bangs {
  position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
  width: 130px; height: 65px;
  border-radius: 65px 65px 0 0;
  z-index: 6; overflow: visible;
}
.bang-strand {
  position: absolute; border-radius: 0 0 50% 50%;
  transform-origin: top center;
}
.c1 { width: 38px; height: 55px; top: 0; left: 10%; transform: rotate(-5deg); }
.c2 { width: 32px; height: 65px; top: 0; left: 30%; }
.c3 { width: 28px; height: 50px; top: 0; left: 50%; transform: translateX(-50%); }
.c4 { width: 32px; height: 62px; top: 0; right: 30%; }
.c5 { width: 38px; height: 55px; top: 0; right: 10%; transform: rotate(5deg); }
.a-ornament {
  position: absolute; top: 2px; right: 8px;
  font-size: 22px; z-index: 8;
  animation: ornBounce 2.5s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
}
@keyframes ornBounce {
  0%, 100% { transform: translateY(0) rotate(-5deg); }
  50% { transform: translateY(-4px) rotate(5deg); }
}
.a-neck {
  width: 34px; height: 30px;
  margin-top: -8px; z-index: 1;
  border-radius: 0 0 10px 10px;
}
.a-torso {
  width: 115px; height: 105px;
  border-radius: 20px 20px 0 0;
  position: relative; z-index: 2; margin-top: -4px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  animation: torsoBreath 4s ease-in-out infinite;
  display: flex; flex-direction: column; align-items: center;
}
@keyframes torsoBreath {
  0%, 100% { transform: scaleX(1); }
  50% { transform: scaleX(1.008); }
}
.a-collar {
  position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  width: 55px; height: 30px; display: flex; border-bottom: 2px solid;
}
.collar-flap { width: 50%; height: 100%; }
.collar-flap.left { border-radius: 0 0 0 20px; }
.collar-flap.right { border-radius: 0 0 20px 0; }
.a-cloth-line {
  position: absolute; top: 30px; left: 50%; transform: translateX(-50%);
  width: 1px; height: 50px;
  background: rgba(0,0,0,0.08);
}
.a-bow {
  position: absolute; top: 22px;
  font-size: 26px;
  animation: bowWave 3s ease-in-out infinite;
}
@keyframes bowWave {
  0%, 100% { transform: rotate(0deg) scale(1); }
  50% { transform: rotate(8deg) scale(1.05); }
}
.cloth-pattern {
  position: absolute; bottom: 0; left: 0; right: 0; height: 18px;
  background: rgba(0,0,0,0.08);
}
.a-arm {
  position: absolute; top: 18px;
  display: flex; flex-direction: column; align-items: center;
  z-index: 3; transform-origin: top center;  /* 手臂在腿部前面 */
}
.a-arm.left { left: -15px; animation: armL 4s ease-in-out infinite; }
.a-arm.right { right: -15px; animation: armR 4s ease-in-out infinite 0.5s; }
@keyframes armL {
  0%, 100% { transform: rotate(-5deg); }
  50% { transform: rotate(5deg); }
}
@keyframes armR {
  0%, 100% { transform: rotate(5deg); }
  50% { transform: rotate(-5deg); }
}
.a-sleeve { width: 30px; height: 50px; border-radius: 15px; }
.a-forearm {
  width: 26px; height: 50px;
  border-radius: 0 0 13px 13px;
  position: relative; margin-top: -4px;
}
.a-hand {
  position: absolute; bottom: -10px; left: 50%; transform: translateX(-50%);
  width: 24px; height: 26px;
  border-radius: 50% 50% 40% 40%;
  display: flex; justify-content: center; align-items: flex-end;
  padding: 2px; gap: 2px;
}
.a-finger { width: 4px; height: 9px; border-radius: 2px; }
.a-thumb { position: absolute; left: -5px; top: 4px; width: 8px; height: 10px; border-radius: 50%; }
.a-skirt {
  width: 130px; min-height: 70px;
  border-radius: 0 0 35px 35px;
  position: relative; overflow: hidden;
  margin-top: -2px; z-index: 1;  /* 裙子在手臂后面 */
  display: flex; align-items: flex-end; justify-content: center;
  animation: skirtSway 4s ease-in-out infinite;
}
@keyframes skirtSway {
  0%, 100% { transform: skewX(0deg); }
  25% { transform: skewX(1.5deg); }
  75% { transform: skewX(-1.5deg); }
}
.skirt-pleat {
  position: absolute; bottom: 0; width: 22px; height: 100%;
  background: rgba(255,255,255,0.08);
  border-left: 1px solid rgba(255,255,255,0.12);
}
.skirt-pleat:nth-child(1) { left: 0%; }
.skirt-pleat:nth-child(2) { left: 16%; }
.skirt-pleat:nth-child(3) { left: 33%; }
.skirt-pleat:nth-child(4) { left: 50%; }
.skirt-pleat:nth-child(5) { left: 66%; }
.skirt-pleat:nth-child(6) { left: 83%; }
.skirt-waist {
  position: absolute; top: 0; left: 0; right: 0; height: 10px;
  border-radius: 0 0 10px 10px;
}
.a-legs {
  display: flex; gap: 8px;
  position: relative; z-index: 1;
}
.a-leg { display: flex; flex-direction: column; align-items: center; }
.a-leg.left { animation: legAL 4s ease-in-out infinite; }
.a-leg.right { animation: legAR 4s ease-in-out infinite 0.5s; }
@keyframes legAL {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(0.5deg); }
}
@keyframes legAR {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(-0.5deg); }
}
.a-thigh {
  width: 48px; height: 72px;
  border-radius: 0 0 10px 10px;
  position: relative;
}
.a-thigh::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0;
  height: 6px; background: rgba(0,0,0,0.06);
  border-radius: 0 0 6px 6px;
}
.a-knee {
  width: 44px; height: 14px; position: relative;
}
.a-knee::after {
  content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%);
  width: 10px; height: 6px;
  background: rgba(255,255,255,0.1); border-radius: 50%;
}
.a-calf { width: 40px; height: 72px; }
.a-sock { width: 38px; height: 50px; border-radius: 0 0 4px 4px; }
.a-shoe {
  width: 46px; height: 22px;
  border-radius: 6px 14px 4px 4px;
  position: relative;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.shoe-bow { position: absolute; top: 3px; left: 50%; transform: translateX(-50%); font-size: 10px; }
.a-wave {
  margin-top: 10px; display: flex; align-items: flex-end;
  gap: 4px; height: 26px;
}
.a-wave span {
  width: 4px; border-radius: 2px;
  animation: aWave 0.7s ease-in-out infinite alternate;
}
.a-wave span:nth-child(1) { height: 8px; }
.a-wave span:nth-child(2) { height: 18px; animation-delay: 0.1s; }
.a-wave span:nth-child(3) { height: 26px; animation-delay: 0.2s; }
.a-wave span:nth-child(4) { height: 16px; animation-delay: 0.15s; }
.a-wave span:nth-child(5) { height: 22px; animation-delay: 0.25s; }
.a-wave span:nth-child(6) { height: 10px; animation-delay: 0.05s; }
@keyframes aWave { to { height: 4px; } }

/* ===================== 头发样式 ===================== */
.a-hair-back.short { height: 80px; }
.a-hair-back.curly {
  height: 160px;
  border-radius: 70px 70px 30px 30px;
}

/* 长直发 - 默认样式 */
.a-hair-back.long-straight {
  height: 220px;
  border-radius: 68px 68px 25px 25px;
}

/* 马尾 - 在头部后方 */
.a-hair-back.ponytail {
  height: 120px;
  border-radius: 68px 68px 30px 30px;
}

/* 双马尾 - 从两侧垂下 */
.a-hair-back.twin-tail {
  height: 100px;
  width: 160px;
  margin-left: -25px;
  border-radius: 60px 60px 30px 30px;
}

/* 双辫子 */
.a-hair-back.twin-braids {
  height: 90px;
  width: 150px;
  margin-left: -20px;
  border-radius: 65px 65px 25px 25px;
}

/* 波浪发 */
.a-hair-back.wavy {
  height: 200px;
  border-radius: 70px 70px 40px 40px;
}

/* 不对称/姬发式 */
.a-hair-back.asymmetrical {
  height: 180px;
  border-radius: 68px 68px 20px 45px;
}

/* ===================== 侧发马尾样式 ===================== */
/* 基础侧发 - 垂在两侧 */
.a-hair-side {
  position: absolute; top: 55px;
  width: 22px; height: 110px;
  border-radius: 11px;
  z-index: 5; overflow: visible;
}
.a-hair-side.left { left: -4px; transform-origin: top center; animation: sideWave 3s ease-in-out infinite; }
.a-hair-side.right { right: -4px; transform-origin: top center; animation: sideWave 3s ease-in-out infinite 0.5s; }
@keyframes sideWave {
  0%, 100% { transform: rotate(2deg); }
  50% { transform: rotate(-2deg); }
}

/* 双马尾 - 侧发变成马尾，垂到身体两侧 */
.a-hair-side.twin-tail {
  width: 45px;
  height: 200px;
  top: 40px;
  border-radius: 22px 22px 18px 18px;
  z-index: 1;
  animation: twinTailSwing 3s ease-in-out infinite;
}
.a-hair-side.twin-tail.left { 
  left: -18px;
}
.a-hair-side.twin-tail.right { 
  right: -18px;
  animation-delay: 0.5s;
}
@keyframes twinTailSwing {
  0%, 100% { transform: rotate(5deg); }
  50% { transform: rotate(-8deg); }
}
/* 双马尾的刘海稍小 */
.a-hair-side.twin-tail .c1, .a-hair-side.twin-tail .c5 { height: 50px; width: 35px; }
.a-hair-side.twin-tail .c2, .a-hair-side.twin-tail .c4 { height: 55px; width: 30px; }
.a-hair-side.twin-tail .c3 { height: 48px; width: 25px; }

/* 低马尾 - 侧发向下延伸 */
.a-hair-side.ponytail {
  width: 35px;
  height: 160px;
  top: 45px;
  border-radius: 17px 17px 12px 12px;
  z-index: 1;
  animation: ponySwing 3.5s ease-in-out infinite;
}
.a-hair-side.ponytail.left { left: -12px; }
.a-hair-side.ponytail.right { 
  right: -12px;
  animation-delay: 0.4s;
}
@keyframes ponySwing {
  0%, 100% { transform: rotate(3deg); }
  50% { transform: rotate(-5deg); }
}

/* 双辫子 - 侧发变成两条辫子 */
.a-hair-side.twin-braids {
  width: 30px;
  height: 180px;
  top: 42px;
  border-radius: 15px;
  z-index: 1;
  animation: braidSwing 2.5s ease-in-out infinite;
}
.a-hair-side.twin-braids.left { left: -10px; }
.a-hair-side.twin-braids.right { 
  right: -10px;
  animation-delay: 0.3s;
}
@keyframes braidSwing {
  0%, 100% { transform: rotate(2deg); }
  50% { transform: rotate(-4deg); }
}

/* 卷发 - 侧发更蓬松 */
.a-hair-side.curly {
  width: 30px;
  height: 130px;
  border-radius: 15px;
}

/* 波浪发 - 侧发有弧度 */
.a-hair-side.wavy {
  width: 28px;
  height: 125px;
  border-radius: 14px;
  transform: rotate(3deg);
}
.a-hair-side.wavy.right { transform: rotate(-3deg); }

/* 短发 - 侧发短 */
.a-hair-side.short {
  height: 50px;
  width: 18px;
}

/* 不对称 - 侧发一边长一边短 */
.a-hair-side.asymmetrical {
  height: 90px;
}
.a-hair-side.asymmetrical.right {
  height: 60px;
}

/* 长直发 - 侧发长而直 */
.a-hair-side.long-straight {
  height: 130px;
  width: 24px;
}

/* 隐藏其他发型的侧发细节 */
.hair-strand {
  position: absolute; left: 4px;
  width: 3px; height: 40px;
  background: rgba(0,0,0,0.08); border-radius: 2px;
}
.hair-strand:nth-child(1) { top: 20px; }
.hair-strand:nth-child(2) { top: 55px; height: 30px; }

/* 刘海样式 */
.a-bangs.short { height: 50px; border-radius: 50px 50px 0 0; }
.a-bangs.short .c1, .a-bangs.short .c5 { height: 40px; }
.a-bangs.short .c2, .a-bangs.short .c4 { height: 45px; }
.a-bangs.short .c3 { height: 35px; }

.a-bangs.wavy .c1, .a-bangs.wavy .c5 {
  border-radius: 0 0 50% 50%;
  transform: rotate(-8deg);
}
.a-bangs.wavy .c2, .a-bangs.wavy .c4 {
  height: 70px;
  border-radius: 0 0 40% 40%;
}
.a-bangs.wavy .c3 { height: 55px; }

.a-bangs.curly .c1, .a-bangs.curly .c5 {
  height: 70px;
  border-radius: 0 0 60% 60%;
  transform: rotate(-10deg);
}
.a-bangs.curly .c2, .a-bangs.curly .c4 {
  height: 80px;
  border-radius: 0 0 50% 50%;
}
.a-bangs.curly .c3 { height: 65px; }

.a-bangs.asymmetrical {
  width: 140px;
  height: 75px;
}
.a-bangs.asymmetrical .c1 { height: 70px; left: 5%; transform: rotate(-15deg); }
.a-bangs.asymmetrical .c2 { height: 65px; left: 25%; }
.a-bangs.asymmetrical .c3 { height: 55px; }
.a-bangs.asymmetrical .c4, .a-bangs.asymmetrical .c5 { display: none; }

.a-bangs.twin-tail .c1, .a-bangs.twin-tail .c5 { height: 50px; width: 35px; }
.a-bangs.twin-tail .c2, .a-bangs.twin-tail .c4 { height: 55px; width: 30px; }
.a-bangs.twin-tail .c3 { height: 48px; width: 25px; }

.a-bangs.ponytail { width: 125px; }
.a-bangs.ponytail .c1 { height: 50px; left: 8%; }
.a-bangs.ponytail .c2 { height: 45px; left: 30%; }
.a-bangs.ponytail .c3 { height: 42px; }
.a-bangs.ponytail .c4 { height: 48px; right: 30%; }
.a-bangs.ponytail .c5 { height: 52px; right: 8%; }

.a-bangs.twin-braids {
  width: 135px;
  border-radius: 67px 67px 20px 20px;
}
.a-bangs.twin-braids .c1, .a-bangs.twin-braids .c5 { height: 48px; width: 34px; }
.a-bangs.twin-braids .c2, .a-bangs.twin-braids .c4 { height: 42px; width: 28px; }
.a-bangs.twin-braids .c3 { height: 40px; width: 24px; }

/* 侧发双马尾装饰 */
.hair-strand.twin-tail-strand {
  display: block;
  width: 8px;
  height: 30px;
  background: rgba(0,0,0,0.12);
  border-radius: 4px;
  position: absolute;
  bottom: 5px;
  left: 50%;
  transform: translateX(-50%) rotate(-15deg);
}

/* ===================== 衣服样式 ===================== */
/* JK制服 */
.a-torso.jk {
  border-radius: 18px 18px 0 0;
}
.a-torso.jk .a-collar {
  width: 70px;
  height: 35px;
  border-bottom: none;
}
.a-torso.jk .collar-flap {
  width: 50%;
  height: 100%;
  clip-path: polygon(0 0, 100% 0, 80% 100%, 20% 100%);
}
.a-torso.jk .collar-flap.left {
  clip-path: polygon(0 0, 100% 0, 80% 100%, 20% 100%);
}
.a-torso.jk .collar-flap.right {
  clip-path: polygon(0 0, 100% 0, 80% 100%, 20% 100%);
}
.a-torso.jk .a-cloth-line {
  top: 25px;
  width: 50px;
  height: 60px;
  border-left: 1px solid rgba(0,0,0,0.1);
  border-right: 1px solid rgba(0,0,0,0.1);
}
.a-torso.jk .cloth-pattern {
  display: none;
}

/* 护士服 */
.a-torso.nurse {
  border-radius: 20px 20px 0 0;
}
.a-torso.nurse .a-collar {
  width: 60px;
  height: 20px;
  border-radius: 0 0 30px 30px;
  border: none;
  background: linear-gradient(180deg, #60a5fa 0%, #3b82f6 100%);
}
.a-torso.nurse .collar-flap {
  display: none;
}
.a-torso.nurse .a-cloth-line {
  display: none;
}
.a-torso.nurse .cloth-pattern {
  display: none;
}

/* 精灵装 */
.a-torso.elf {
  border-radius: 20px 20px 0 0;
  box-shadow: 0 4px 20px rgba(74, 222, 128, 0.3);
}
.a-torso.elf .a-collar {
  width: 45px;
  height: 25px;
  border: none;
  border-radius: 0 0 50% 50%;
  overflow: hidden;
}
.a-torso.elf .collar-flap { display: none; }
.a-torso.elf .a-cloth-line { top: 25px; width: 40px; height: 40px; }
.a-torso.elf .cloth-pattern {
  background: linear-gradient(180deg, rgba(255,255,255,0.2) 0%, transparent 100%);
}

/* 婚纱 - 优雅的桃心领礼服 */
.a-torso.wedding {
  width: 110px;
  border-radius: 15px 15px 0 0;
  box-shadow: 0 4px 25px rgba(255,255,255,0.4);
  background: linear-gradient(180deg, #ffffff 0%, #f8f8f8 50%, #f0f0f0 100%) !important;
}
/* 桃心领 - 用伪元素创建 */
.a-torso.wedding::before {
  content: '';
  position: absolute;
  top: -5px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 35px;
  background: linear-gradient(180deg, #ffe4ec 0%, #fff5f8 100%);
  border-radius: 0 0 50% 50%;
  clip-path: polygon(0 0, 100% 0, 100% 60%, 50% 100%, 0 60%);
}
.a-torso.wedding .a-collar {
  width: 0;
  height: 0;
  border: none;
  display: none;
}
.a-torso.wedding .collar-flap { display: none; }
.a-torso.wedding .a-cloth-line { 
  display: block;
  top: 20px;
  width: 2px;
  height: 60px;
  background: linear-gradient(180deg, #e8d0d8 0%, transparent 100%);
}
.a-torso.wedding .cloth-pattern {
  height: 20px;
  background: linear-gradient(180deg, rgba(255,200,220,0.3) 0%, rgba(255,255,255,0.8) 100%);
}

/* 哥特 */
.a-torso.gothic {
  border-radius: 15px 15px 0 0;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.a-torso.gothic .a-collar {
  width: 55px;
  height: 28px;
  border: none;
  background: #374151;
}
.a-torso.gothic .collar-flap { display: none; }
.a-torso.gothic .a-cloth-line { top: 28px; width: 50px; height: 55px; background: rgba(0,0,0,0.15); }
.a-torso.gothic .cloth-pattern {
  background: rgba(0,0,0,0.1);
}

/* 运动服 */
.a-torso.sports {
  border-radius: 25px 25px 0 0;
  box-shadow: 0 4px 16px rgba(251, 146, 60, 0.3);
}
.a-torso.sports .a-collar {
  width: 65px;
  height: 22px;
  border: none;
  border-radius: 0 0 32px 32px;
  background: linear-gradient(180deg, #fb923c 0%, #ea580c 100%);
}
.a-torso.sports .collar-flap { display: none; }
.a-torso.sports .a-cloth-line { display: none; }
.a-torso.sports .cloth-pattern {
  height: 15px;
  background: linear-gradient(180deg, rgba(255,255,255,0.3) 0%, transparent 100%);
}

/* 水手服 */
.a-torso.sailor {
  border-radius: 18px 18px 0 0;
  box-shadow: 0 4px 16px rgba(34, 211, 238, 0.3);
}
.a-torso.sailor .a-collar {
  width: 80px;
  height: 30px;
  border: none;
  border-bottom: 3px solid #06b6d4;
}
.a-torso.sailor .collar-flap {
  width: 50%;
  height: 100%;
  background: linear-gradient(180deg, #22d3ee 0%, #06b6d4 100%);
  clip-path: polygon(0 0, 100% 0, 90% 100%, 10% 100%);
}
.a-torso.sailor .collar-flap.left { clip-path: polygon(0 0, 100% 0, 90% 100%, 10% 100%); }
.a-torso.sailor .collar-flap.right { clip-path: polygon(0 0, 100% 0, 90% 100%, 10% 100%); }
.a-torso.sailor .a-cloth-line { top: 30px; width: 45px; height: 50px; }
.a-torso.sailor .cloth-pattern { display: none; }

/* 短裙样式 */
.a-skirt.jk {
  height: 85px;
  width: 135px;
  border-radius: 0 0 40px 40px;
}
.a-skirt.nurse {
  height: 65px;
  width: 120px;
  border-radius: 0 0 30px 30px;
}
.a-skirt.elf {
  height: 90px;
  width: 140px;
  border-radius: 0 0 50px 50px;
  box-shadow: 0 4px 20px rgba(74, 222, 128, 0.2);
}
.a-skirt.wedding {
  height: 120px;
  width: 180px;
  border-radius: 0 0 90px 90px;
  margin-left: -25px;
  box-shadow: 0 4px 30px rgba(255,255,255,0.5);
}
.a-skirt.gothic {
  height: 75px;
  width: 125px;
  border-radius: 0 0 20px 20px;
}
.a-skirt.sports {
  height: 70px;
  width: 130px;
  border-radius: 0 0 35px 35px;
}
.a-skirt.sailor {
  height: 80px;
  width: 130px;
  border-radius: 0 0 40px 40px;
}

/* 袖子样式 */
.a-sleeve.nurse {
  width: 35px;
  height: 45px;
  border-radius: 12px 12px 15px 15px;
}
.a-sleeve.elf {
  width: 28px;
  height: 55px;
  border-radius: 14px;
}
.a-sleeve.wedding {
  width: 40px;
  height: 60px;
  border-radius: 20px 20px 15px 15px;
  background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(248,240,245,0.9) 100%) !important;
  box-shadow: 0 2px 10px rgba(255,200,220,0.3);
}
.a-sleeve.sports {
  width: 38px;
  height: 40px;
  border-radius: 20px 20px 12px 12px;
}

/* ===================== 袜子样式 ===================== */
.a-sock.long { height: 50px; border-radius: 0 0 4px 4px; }
.a-sock.short { height: 20px; border-radius: 0 0 3px 3px; }
.a-sock.knee-high { height: 80px; border-radius: 0 0 6px 6px; }
.a-sock.bubbly {
  height: 35px;
  border-radius: 0 0 50% 50%;
}
.a-sock.striped {
  height: 50px;
  background: repeating-linear-gradient(
    0deg,
    var(--sock-color, #93c5fd) 0px,
    var(--sock-color, #93c5fd) 8px,
    #ffffff 8px,
    #ffffff 12px
  ) !important;
}
.a-sock.mesh {
  height: 50px;
  background: repeating-linear-gradient(
    45deg,
    var(--sock-color, #a1a1aa) 1px,
    transparent 1px,
    transparent 6px
  ) !important;
}

/* ===================== 鞋子样式 ===================== */
.a-shoe.mary-jane {
  width: 46px;
  height: 22px;
  border-radius: 6px 14px 4px 4px;
}
.a-shoe.heels {
  width: 40px;
  height: 28px;
  border-radius: 4px 12px 2px 2px;
  clip-path: polygon(0 0, 70% 0, 100% 100%, 0 100%);
}
.a-shoe.heels::after {
  content: '';
  position: absolute;
  bottom: -12px;
  right: 5px;
  width: 6px;
  height: 12px;
  background: inherit;
  border-radius: 2px;
}
.a-shoe.canvas {
  width: 48px;
  height: 20px;
  border-radius: 8px 8px 6px 6px;
}
.a-shoe.canvas::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 6px;
  background: #ffffff;
  border-radius: 0 0 6px 6px;
}
.a-shoe.boots {
  width: 44px;
  height: 45px;
  border-radius: 6px 8px 4px 4px;
  margin-bottom: -10px;
}
.a-shoe.boots::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 10px;
  background: rgba(255,255,255,0.1);
  border-radius: 6px 8px 0 0;
}
.a-shoe.sneakers {
  width: 52px;
  height: 24px;
  border-radius: 10px 16px 6px 6px;
  background: linear-gradient(180deg, var(--shoe-color, #f8fafc) 70%, #ffffff 70%) !important;
}
.a-shoe.loafers {
  width: 44px;
  height: 20px;
  border-radius: 10px 10px 4px 4px;
}
.a-shoe.loafers::before {
  content: '';
  position: absolute;
  top: 5px;
  left: 50%;
  transform: translateX(-50%);
  width: 15px;
  height: 8px;
  background: rgba(0,0,0,0.2);
  border-radius: 4px;
}
</style>
