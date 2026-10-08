<template>
  <transition name="weather-popup">
    <div v-if="visible" class="weather-popup-overlay" @click.self="$emit('close')">
      <div class="weather-popup-card">
        <!-- 关闭按钮 -->
        <button class="close-btn" @click="$emit('close')">✕</button>

        <!-- 加载状态 -->
        <div v-if="!weather || weather._stale && !weather.current" class="loading-state">
          <div class="loading-spinner"></div>
          <span>获取天气数据中...</span>
        </div>

        <template v-else-if="weather && weather.current">
          <!-- ===== 顶部：当前天气大标题 ===== -->
          <div class="weather-hero">
            <div class="hero-left">
              <span class="hero-icon">{{ weather.current.weather_icon }}</span>
              <div class="hero-temp-wrap">
                <span class="hero-temp">{{ weather.current.temp }}°</span>
                <span class="hero-desc">{{ weather.current.weather_text }}</span>
                <span class="hero-feels">体感 {{ weather.current.feels_like }}°</span>
              </div>
            </div>
            <div class="hero-location">
              <span class="location-icon">📍</span>
              <span class="location-text">无锡市 · 灵山胜境</span>
            </div>
          </div>

          <!-- ===== 今日摘要 ===== -->
          <div class="today-summary" v-if="weather.daily && weather.daily.temp_max">
            <div class="summary-item">
              <span class="summary-icon">🌡️</span>
              <span class="summary-val">H:{{ weather.daily.temp_max }}° L:{{ weather.daily.temp_min }}°</span>
            </div>
            <div class="summary-item" v-if="weather.daily.sunrise">
              <span class="summary-icon">🌅</span>
              <span class="summary-val">{{ weather.daily.sunrise }}</span>
            </div>
            <div class="summary-item" v-if="weather.daily.sunset">
              <span class="summary-icon">🌇</span>
              <span class="summary-val">{{ weather.daily.sunset }}</span>
            </div>
            <div class="summary-item" v-if="weather.daily.precipitation_sum > 0">
              <span class="summary-icon">☔</span>
              <span class="summary-val">{{ weather.daily.precipitation_sum }}mm</span>
            </div>
          </div>

          <!-- ===== 逐小时预报 ===== -->
          <div class="hourly-section" v-if="weather.hourly && weather.hourly.length > 0">
            <div class="section-title">逐小时预报</div>
            <div class="hourly-scroll">
              <div
                v-for="(h, idx) in weather.hourly"
                :key="idx"
                class="hourly-item"
                :class="{ now: idx === 0 }"
              >
                <span class="hourly-time">{{ idx === 0 ? '现在' : h.time }}</span>
                <span class="hourly-icon">{{ h.weather_icon }}</span>
                <span class="hourly-temp">{{ h.temp }}°</span>
                <span class="hourly-rain" v-if="h.precip_prob > 0">{{ h.precip_prob }}%</span>
                <span class="hourly-rain dim" v-else>--</span>
              </div>
            </div>
          </div>

          <!-- ===== 详细指标网格 ===== -->
          <div class="detail-grid">
            <div class="detail-item">
              <div class="detail-header">
                <span class="detail-icon">🌡️</span>
                <span class="detail-label">体感温度</span>
              </div>
              <span class="detail-value">{{ weather.current.feels_like }}°</span>
            </div>

            <div class="detail-item">
              <div class="detail-header">
                <span class="detail-icon">💧</span>
                <span class="detail-label">湿度</span>
              </div>
              <span class="detail-value">{{ weather.current.humidity }}%</span>
            </div>

            <div class="detail-item">
              <div class="detail-header">
                <span class="detail-icon">🌬️</span>
                <span class="detail-label">风速风向</span>
              </div>
              <span class="detail-value">
                {{ weather.current.wind_direction_text }}
                <span class="detail-sub">{{ weather.current.wind_speed }} m/s</span>
              </span>
            </div>

            <div class="detail-item">
              <div class="detail-header">
                <span class="detail-icon">👁️</span>
                <span class="detail-label">能见度</span>
              </div>
              <span class="detail-value">{{ visText }}</span>
            </div>

            <div class="detail-item">
              <div class="detail-header">
                <span class="detail-icon">☀️</span>
                <span class="detail-label">紫外线指数</span>
              </div>
              <span class="detail-value">
                {{ weather.current.uv_index }}
                <span class="detail-sub uv-tag" :class="uvClass">{{ weather.current.uv_level }}</span>
              </span>
            </div>

            <div class="detail-item">
              <div class="detail-header">
                <span class="detail-icon">📊</span>
                <span class="detail-label">气压</span>
              </div>
              <span class="detail-value">{{ weather.current.pressure }} hPa</span>
            </div>
          </div>

          <!-- ===== 底部 ===== -->
          <div class="weather-footer">
            <span v-if="weather._stale" class="stale-badge">⚠️ 数据可能过期</span>
            <span class="source" v-else>数据来源: Open-Meteo</span>
            <span class="update-time">{{ updateTimeText }}</span>
          </div>
        </template>

        <!-- 无数据 -->
        <div v-else class="loading-state">
          <span>暂无天气数据</span>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
defineOptions({ name: 'WeatherPopup' })
import { computed } from 'vue'

const props = defineProps({
  weather: { type: Object, default: null },
  visible: { type: Boolean, default: false },
})
defineEmits(['close'])

const visText = computed(() => {
  const v = props.weather?.current?.visibility
  if (v == null) return '--'
  if (v >= 10000) return `${(v / 1000).toFixed(0)} km`
  return `${(v / 1000).toFixed(1)} km`
})

const uvClass = computed(() => {
  const u = props.weather?.current?.uv_index ?? 0
  if (u <= 2) return 'low'
  if (u <= 5) return 'moderate'
  if (u <= 7) return 'high'
  if (u <= 10) return 'vhigh'
  return 'extreme'
})

const updateTimeText = computed(() => {
  const ts = props.weather?.updated_at
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `更新于 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
})
</script>

<style scoped>
.weather-popup-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}

.weather-popup-card {
  position: relative;
  width: 420px; max-width: 90vw; max-height: 90vh;
  overflow-y: auto;
  background: linear-gradient(160deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.95) 40%, rgba(15,23,42,0.95) 100%);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px;
  padding: 28px 24px 20px;
  backdrop-filter: blur(20px);
  box-shadow: 0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05) inset;
  color: #e2e8f0;
}

.close-btn {
  position: absolute; top: 12px; right: 14px;
  width: 32px; height: 32px; border-radius: 50%;
  background: rgba(255,255,255,0.08); border: none; color: rgba(255,255,255,0.6);
  font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.close-btn:hover { background: rgba(255,255,255,0.15); color: #fff; }

/* ── 加载 ── */
.loading-state {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  padding: 60px 0; color: rgba(255,255,255,0.5); font-size: 14px;
}
.loading-spinner {
  width: 36px; height: 36px; border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #60a5fa; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Hero 区 ── */
.weather-hero { margin-bottom: 20px; }
.hero-left { display: flex; align-items: center; gap: 16px; }
.hero-icon { font-size: 56px; line-height: 1; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3)); }
.hero-temp-wrap { display: flex; flex-direction: column; }
.hero-temp {
  font-size: 64px; font-weight: 200; line-height: 1;
  background: linear-gradient(180deg, #fff 0%, #94a3b8 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-desc { font-size: 18px; color: #cbd5e1; margin-top: 2px; }
.hero-feels { font-size: 13px; color: #64748b; margin-top: 2px; }

.hero-location { margin-top: 12px; display: flex; align-items: center; gap: 5px; }
.location-icon { font-size: 13px; }
.location-text { font-size: 13px; color: #94a3b8; font-weight: 500; }

/* ── 今日摘要 ── */
.today-summary {
  display: flex; flex-wrap: wrap; gap: 12px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.04); border-radius: 12px;
  margin-bottom: 20px;
}
.summary-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #94a3b8; }
.summary-icon { font-size: 16px; }
.summary-val { font-weight: 500; color: #cbd5e1; }

/* ── 逐小时预报 ── */
.hourly-section { margin-bottom: 20px; }
.section-title { font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
.hourly-scroll { display: flex; gap: 4px; overflow-x: auto; padding-bottom: 6px; }
.hourly-scroll::-webkit-scrollbar { height: 3px; }
.hourly-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
.hourly-item {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  min-width: 64px; padding: 10px 8px;
  background: rgba(255,255,255,0.03); border-radius: 10px;
  transition: background 0.2s;
}
.hourly-item.now { background: rgba(96,165,250,0.15); }
.hourly-time { font-size: 11px; color: #64748b; font-weight: 500; }
.hourly-icon { font-size: 22px; }
.hourly-temp { font-size: 15px; font-weight: 600; color: #e2e8f0; }
.hourly-rain { font-size: 10px; color: #60a5fa; }
.hourly-rain.dim { color: #334155; }

/* ── 详细指标 2×3 网格 ── */
.detail-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
  margin-bottom: 16px;
}
.detail-item {
  background: rgba(255,255,255,0.04); border-radius: 12px;
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 8px;
}
.detail-header { display: flex; align-items: center; gap: 6px; }
.detail-icon { font-size: 15px; }
.detail-label { font-size: 11px; color: #64748b; font-weight: 500; }
.detail-value { font-size: 20px; font-weight: 600; color: #e2e8f0; display: flex; align-items: baseline; gap: 6px; }
.detail-sub { font-size: 12px; font-weight: 400; color: #64748b; }
.uv-tag {
  font-size: 11px; padding: 1px 7px; border-radius: 10px; font-weight: 500;
}
.uv-tag.low { background: rgba(34,197,94,0.2); color: #4ade80; }
.uv-tag.moderate { background: rgba(234,179,8,0.2); color: #facc15; }
.uv-tag.high { background: rgba(249,115,22,0.2); color: #fb923c; }
.uv-tag.vhigh { background: rgba(239,68,68,0.2); color: #f87171; }
.uv-tag.extreme { background: rgba(168,85,247,0.2); color: #c084fc; }

/* ── 底部 ── */
.weather-footer {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 11px; color: #475569;
}
.stale-badge { color: #f59e0b; }
.update-time { color: #334155; }

/* ── 过渡动画 ── */
.weather-popup-enter-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.weather-popup-leave-active { transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
.weather-popup-enter-from { opacity: 0; }
.weather-popup-enter-from .weather-popup-card { transform: scale(0.9) translateY(20px); opacity: 0; }
.weather-popup-leave-to { opacity: 0; }
.weather-popup-leave-to .weather-popup-card { transform: scale(0.95) translateY(10px); opacity: 0; }

/* ===== 手机端适配 ===== */
@media (max-width: 768px) {
  .weather-popup-card {
    width: 94vw;
    max-width: 94vw;
    max-height: 88vh;
    padding: 20px 16px 16px;
    border-radius: 16px;
  }
  .hero-icon { font-size: 40px; }
  .hero-temp { font-size: 48px; }
  .hero-desc { font-size: 15px; }
  .hero-feels { font-size: 12px; }
  .today-summary { gap: 8px; padding: 10px 12px; }
  .summary-item { font-size: 11px; }
  .detail-grid { gap: 6px; }
  .detail-item { padding: 10px 12px; }
  .detail-value { font-size: 16px; }
  .detail-label { font-size: 10px; }
  .hourly-item { min-width: 52px; padding: 8px 6px; gap: 4px; }
  .hourly-icon { font-size: 18px; }
  .hourly-temp { font-size: 13px; }
  .close-btn { top: 8px; right: 10px; width: 28px; height: 28px; font-size: 12px; }
}
</style>
