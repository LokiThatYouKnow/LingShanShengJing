<template>
  <div class="baidu-map-container" ref="mapContainer">
    <!-- 地图将渲染在此 -->
    <div id="baidu-map-canvas" class="map-canvas" ref="mapCanvas"></div>

    <!-- 未配置API Key时的提示 -->
    <div v-if="!mapLoaded && !loadingFailed" class="map-loading">
      <div class="loading-spinner"></div>
      <span>地图加载中...</span>
    </div>
    <div v-if="loadingFailed" class="map-fallback">
      <div class="fallback-icon">🗺️</div>
      <h3>百度地图未配置</h3>
      <p>请在管理后台填入百度地图 API Key 后使用实景地图功能。</p>
      <div class="ak-hint">
        <span>申请地址：</span>
        <a href="https://lbsyun.baidu.com/apiconsole/key" target="_blank">百度地图开放平台</a>
      </div>
    </div>

    <!-- 景点信息浮窗（自定义，在BMap InfoWindow之外） -->
    <div
      v-if="activeInfoWindow"
      class="spot-info-window"
      :style="infoWindowStyle"
      @click.stop
    >
      <div class="info-header">
        <span class="info-icon">{{ activeInfoWindow.icon }}</span>
        <span class="info-name">{{ activeInfoWindow.name }}</span>
        <button class="info-close" @click="activeInfoWindow = null">✕</button>
      </div>
      <div class="info-desc">{{ activeInfoWindow.description }}</div>
      <div class="info-meta">
        <span>🕐 {{ activeInfoWindow.openTime }}</span>
        <span>💰 {{ activeInfoWindow.price }}</span>
      </div>
      <div class="info-actions">
        <button class="info-guide-btn" @click="$emit('spotClick', activeInfoWindow)">
          🎙️ 开始讲解
        </button>
        <button
          class="info-pano-btn"
          :class="{ loading: panoLoading === activeInfoWindow.id }"
          :disabled="panoLoading === activeInfoWindow.id"
          @click="requestPanorama(activeInfoWindow)"
        >
          {{ panoLoading === activeInfoWindow.id ? '⏳ 检测中...' : '📷 实景查看' }}
        </button>
      </div>
    </div>

    <!-- 全景确认弹窗 -->
    <div v-if="panoConfirmSpot" class="pano-confirm-overlay" @click.self="panoConfirmSpot = null">
      <div class="pano-confirm-dialog">
        <div class="pano-confirm-icon">🏞️</div>
        <h3>{{ panoConfirmSpot.name }}</h3>
        <p>
          附近检测到百度街景覆盖。<br/>
          <span class="pano-hint">将在百度地图中查看该位置的实景照片</span>
        </p>
        <div class="pano-confirm-actions">
          <button class="pano-btn-cancel" @click="panoConfirmSpot = null">取消</button>
          <button class="pano-btn-enter" @click="enterPanorama">📷 查看实景</button>
        </div>
      </div>
    </div>

    <!-- 全景不可用提示 -->
    <div v-if="panoUnavailableMsg" class="pano-unavailable-toast">{{ panoUnavailableMsg }}</div>

    <!-- 地图图例 -->
    <div class="map-legend" v-if="mapLoaded">
      <div class="legend-item">
        <span class="legend-dot route"></span>游览路线
      </div>
      <div class="legend-item">
        <span class="legend-dot spot"></span>景点位置
      </div>
      <div class="legend-hint">点击标记查看详情</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { wgs84ToBd09 } from '../utils/coordTransform.js'

const props = defineProps({
  spots: { type: Array, default: () => [] },
  center: { type: Object, default: () => ({ lng: 120.1075, lat: 31.4200 }) },
  zoom: { type: Number, default: 15 },
  apiKey: { type: String, default: '' }
})

const emit = defineEmits(['spotClick', 'mapReady'])

const mapContainer = ref(null)
const mapCanvas = ref(null)
const mapLoaded = ref(false)
const loadingFailed = ref(false)
const activeInfoWindow = ref(null)
const infoWindowPos = ref({ x: 0, y: 0 })

// 全景相关状态
const panoConfirmSpot = ref(null)
const panoLoading = ref(null)       // 正在检测全景的景点ID
const panoUnavailableMsg = ref('')

let bmapInstance = null
let spotMarkers = []
let panoTargetId = null          // 全景ID
let panoMercatorX = null         // 全景 Mercator X（用于精确定位）
let panoMercatorY = null         // 全景 Mercator Y

const infoWindowStyle = computed(() => ({
  left: infoWindowPos.value.x + 'px',
  top: infoWindowPos.value.y + 'px'
}))

/**
 * 动态加载百度地图 JS API 脚本
 */
function loadBaiduMapScript(ak) {
  return new Promise((resolve, reject) => {
    // 检查是否已加载
    if (window.BMap && window.BMap.Map) {
      resolve(window.BMap)
      return
    }

    // 检查是否已有同源脚本在加载
    const existing = document.querySelector('script[src*="api.map.baidu.com"]')
    if (existing) {
      existing.addEventListener('load', () => {
        if (window.BMap) resolve(window.BMap)
        else reject(new Error('百度地图加载失败'))
      })
      existing.addEventListener('error', () => reject(new Error('百度地图脚本加载失败')))
      return
    }

    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/getscript?v=3.0&ak=${ak}&services=Panorama&t=20240701`
    script.onload = () => {
      console.log('[BaiduMap] SDK 加载完成, PanoramaService:', typeof window.BMap?.PanoramaService, 'Panorama:', typeof window.BMap?.Panorama)
      if (window.BMap && window.BMap.Map) {
        resolve(window.BMap)
      } else {
        reject(new Error('百度地图初始化失败'))
      }
    }
    script.onerror = () => reject(new Error('百度地图脚本加载失败'))
    document.head.appendChild(script)
  })
}

/**
 * 初始化地图
 */
async function initMap() {
  if (!props.apiKey) {
    loadingFailed.value = true
    return
  }

  try {
    const BMap = await loadBaiduMapScript(props.apiKey)

    await nextTick()
    if (!mapCanvas.value) return

    // 转换中心坐标到BD-09
    const bdCenter = wgs84ToBd09(props.center.lng, props.center.lat)

    // 创建地图实例
    bmapInstance = new BMap.Map(mapCanvas.value, {
      enableMapClick: true
    })

    const point = new BMap.Point(bdCenter.lng, bdCenter.lat)
    bmapInstance.centerAndZoom(point, props.zoom)
    bmapInstance.enableScrollWheelZoom(true)
    bmapInstance.addControl(new BMap.NavigationControl())
    bmapInstance.addControl(new BMap.ScaleControl())

    // 添加地图类型控件
    bmapInstance.addControl(new BMap.MapTypeControl({
      mapTypes: [BMAP_NORMAL_MAP, BMAP_SATELLITE_MAP]
    }))

    // ===== 注册地图交互事件 =====
    // 拖拽/缩放时关闭信息浮窗
    bmapInstance.addEventListener('dragstart', () => { activeInfoWindow.value = null })
    bmapInstance.addEventListener('zoomstart', () => { activeInfoWindow.value = null })
    // 点击地图空白区域关闭浮窗
    bmapInstance.addEventListener('click', (e) => {
      // 仅当点击的不是 overlay（标记/标签）时才关闭
      if (!e.overlay) {
        activeInfoWindow.value = null
      }
    })

    // ===== 禁用百度地图内置 POI 点击弹窗 =====
    // 方法1: CSS 注入 —— 隐藏百度原生 POI 浮窗
    injectPoiOverrideStyles()
    // 方法2: 取消底图 POI 交互（tilesloaded 后禁用内置标注点击）
    bmapInstance.addEventListener('tilesloaded', disableBuiltinPoiInteraction)

    mapLoaded.value = true
    loadingFailed.value = false

    // 添加景点标记
    addSpotMarkers(BMap)

    // 绘制路线
    drawRoutes(BMap)

    emit('mapReady', bmapInstance)
  } catch (e) {
    console.error('百度地图初始化失败:', e)
    loadingFailed.value = true
  }
}

/**
 * 添加景点标记
 */
function addSpotMarkers(BMap) {
  // 清除旧标记
  spotMarkers.forEach(m => bmapInstance.removeOverlay(m))
  spotMarkers = []

  if (!props.spots || props.spots.length === 0) return

  props.spots.forEach(spot => {
    if (!spot.lng || !spot.lat) return

    // WGS84 → BD09
    const bdCoord = wgs84ToBd09(spot.lng, spot.lat)
    const point = new BMap.Point(bdCoord.lng, bdCoord.lat)

    // 创建自定义标记
    const marker = new BMap.Marker(point, {
      title: spot.name
    })

    // 点击标记显示信息窗口
    marker.addEventListener('click', (e) => {
      e.domEvent?.stopPropagation?.()
      showInfoWindow(spot, point)
    })

    // 添加标签
    const label = new BMap.Label(spot.icon + ' ' + spot.name, {
      position: point,
      offset: new BMap.Size(0, -30)
    })
    label.setStyle({
      color: '#fff',
      fontSize: '12px',
      padding: '4px 10px',
      borderRadius: '16px',
      background: 'rgba(0,0,0,0.7)',
      border: 'none',
      whiteSpace: 'nowrap',
      cursor: 'pointer'
    })
    marker.setLabel(label)

    bmapInstance.addOverlay(marker)
    spotMarkers.push(marker)
  })
}

/**
 * 绘制游览路线
 */
function drawRoutes(BMap) {
  if (!props.spots || props.spots.length < 2) return

  // 主路线：按spots顺序连接
  const routePoints = props.spots
    .filter(s => s.lng && s.lat)
    .map(s => {
      const bdCoord = wgs84ToBd09(s.lng, s.lat)
      return new BMap.Point(bdCoord.lng, bdCoord.lat)
    })

  if (routePoints.length >= 2) {
    const polyline = new BMap.Polyline(routePoints, {
      strokeColor: '#f59e0b',
      strokeWeight: 4,
      strokeOpacity: 0.7,
      strokeStyle: 'dashed'
    })
    bmapInstance.addOverlay(polyline)
  }
}

// ========== 全景实景功能 ==========

/**
 * 请求查看全景 — 先检测覆盖，再弹出确认框
 * getPanoramaByLocation 仅接受 (point, callback) 两个参数，自动返回最近街景点。
 */
function requestPanorama(spot) {
  if (!bmapInstance || !window.BMap) return

  const BMap = window.BMap

  // 检查 PanoramaService 是否可用
  if (typeof BMap.PanoramaService !== 'function') {
    console.error('[全景] BMap.PanoramaService 不可用')
    panoUnavailableMsg.value = '全景服务未加载，请检查百度地图AK'
    setTimeout(() => { panoUnavailableMsg.value = '' }, 4000)
    return
  }

  // WGS84 → BD09
  const bdCoord = wgs84ToBd09(spot.lng, spot.lat)
  const point = new BMap.Point(bdCoord.lng, bdCoord.lat)

  panoLoading.value = spot.id
  console.log('[全景] 检测街景覆盖:', spot.name, '坐标:', bdCoord.lng, bdCoord.lat)

  try {
    const panoService = new BMap.PanoramaService()
    panoService.getPanoramaByLocation(point, (data) => {
      panoLoading.value = null
      console.log('[全景] getPanoramaByLocation 返回:', data)

      if (data && data.id) {
        // 有全景覆盖，弹出确认框
        activeInfoWindow.value = null
        panoConfirmSpot.value = spot
        panoTargetId = data.id
        // 存储全景精确坐标（优先用 Ih/Jh Mercator，用于 @ URL 精确定位）
        panoMercatorX = data.Ih || null
        panoMercatorY = data.Jh || null
        // 兜底：从 position BMap.Point 提取 BD09 坐标并转为 Mercator
        if ((panoMercatorX == null) && data.position && typeof data.position.lng === 'number') {
          panoMercatorX = data.position.lng * 20037508.34 / 180
          panoMercatorY = Math.log(Math.tan((90 + data.position.lat) * Math.PI / 360)) * 6378137
        }
        console.log('[全景] 全景Mercator坐标:', panoMercatorX, panoMercatorY)
      } else {
        // 无全景覆盖
        panoUnavailableMsg.value = `「${spot.name}」附近暂无百度街景覆盖`
        setTimeout(() => { panoUnavailableMsg.value = '' }, 3000)
      }
    })
  } catch (e) {
    panoLoading.value = null
    console.error('[全景] PanoramaService 调用异常:', e)
    panoUnavailableMsg.value = '全景服务异常，请稍后重试'
    setTimeout(() => { panoUnavailableMsg.value = '' }, 3000)
  }
}

/**
 * 进入全景 — 通过后端 CDP 打开百度地图并自动点击"全景"按钮
 * CDP 失败时兜底用 window.open 打开定位页面
 */
function enterPanorama() {
  if (!panoConfirmSpot.value) return

  const spot = panoConfirmSpot.value
  panoConfirmSpot.value = null

  const mx = panoMercatorX
  const my = panoMercatorY
  panoMercatorX = null
  panoMercatorY = null

  const zoom = 20

  // 兜底 URL（CDP 失败时用）
  let fallbackUrl
  if (mx != null && my != null) {
    fallbackUrl = `https://map.baidu.com/@${mx},${my},${zoom}z`
  } else {
    const bdCoord = wgs84ToBd09(spot.lng, spot.lat)
    const mercatorX = bdCoord.lng * 20037508.34 / 180
    const mercatorY = Math.log(Math.tan((90 + bdCoord.lat) * Math.PI / 360)) * 6378137
    fallbackUrl = `https://map.baidu.com/@${mercatorX.toFixed(2)},${mercatorY.toFixed(2)},20z`
  }

  // 通过后端 CDP 打开百度地图 + 自动点击全景按钮
  const body = mx != null && my != null
    ? JSON.stringify({ mercator_x: mx, mercator_y: my, zoom })
    : JSON.stringify({ mercator_x: (spot.lng * 20037508.34 / 180), mercator_y: (Math.log(Math.tan((90 + spot.lat) * Math.PI / 360)) * 6378137), zoom })

  fetch('/api/map/open-panorama', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body
  }).then(r => r.json()).then(data => {
    console.log('[全景] CDP 结果:', data)
    if (!data.success) {
      // CDP 失败，兜底打开定位页面
      console.warn('[全景] CDP 失败，兜底打开:', fallbackUrl)
      window.open(fallbackUrl, '_blank', 'width=1200,height=800')
    }
  }).catch(err => {
    console.warn('[全景] CDP 不可用，兜底打开:', err.message)
    window.open(fallbackUrl, '_blank', 'width=1200,height=800')
  })
}

// ========== 全景实景功能结束 ==========

/**
 * 显示信息浮窗 — 智能定位，确保在容器可视范围内
 */
function showInfoWindow(spot, point) {
  const container = mapContainer.value
  if (!container) return

  const pixel = bmapInstance.pointToOverlayPixel(point)
  const cw = container.clientWidth
  const ch = container.clientHeight

  // 浮窗尺寸约 260px 宽 × ~280px 高
  const WIN_W = 260
  const WIN_H = 280

  // 默认在标记上方居中
  let left = pixel.x - WIN_W / 2
  let top = pixel.y - WIN_H - 15

  // 边界 clamp：不超出容器
  if (left < 8) left = 8
  if (left + WIN_W > cw - 8) left = cw - WIN_W - 8
  if (top < 8) top = pixel.y + 25  // 放不下就放到标记下方
  if (top + WIN_H > ch - 8) top = ch - WIN_H - 8

  infoWindowPos.value = { x: left, y: top }
  activeInfoWindow.value = spot
}

/**
 * 注入全局 CSS —— 隐藏百度地图内置 POI 弹窗
 * 百度原生浮窗不会触发我们的自定义逻辑，直接屏蔽
 */
function injectPoiOverrideStyles() {
  const styleId = 'baidu-poi-override'
  if (document.getElementById(styleId)) return

  const style = document.createElement('style')
  style.id = styleId
  style.textContent = `
    /* 隐藏百度内置 POI 信息浮窗（地标/商铺点击后的原生弹窗） */
    .BMap_bubble,
    .BMap_pop,
    .BMap_pop>img,
    .BMap_top,
    .BMap_bottom,
    .BMap_center,
    .BMap_Marker.pop {
      display: none !important;
      visibility: hidden !important;
    }
    /* 保留我们自己的 marker 不受影响 */
    .BMap_Marker:not(.pop) {
      visibility: visible !important;
    }
  `
  document.head.appendChild(style)
  console.log('[BaiduMap] 已注入POI弹窗屏蔽样式')
}

/**
 * 禁用底图内置 POI 的点击交互
 * 百度地图 tilesloaded 后，通过 DOM 层移除内置标注的点击事件
 */
function disableBuiltinPoiInteraction() {
  const canvas = document.getElementById('baidu-map-canvas')
  if (!canvas) return

  // 找到百度内置的标注层，禁用其 pointer-events
  const children = canvas.querySelectorAll('[style*="z-index"]')
  children.forEach(el => {
    // 百度的 POI 标注层通常有特定的 z-index 和 class
    const style = window.getComputedStyle(el)
    const zIndex = parseInt(style.zIndex) || 0
    // overlay 层（我们的标记）z-index 较高，POI 标注层较低
    // 不碰高 z-index 的 overlay 层
    if (zIndex > 0 && zIndex < 3) {
      // 只禁用低层级 POI 元素的点击
      const imgs = el.querySelectorAll('img')
      imgs.forEach(img => {
        if (!img.closest('.BMap_Marker')) {
          img.style.pointerEvents = 'none'
        }
      })
    }
  })
}

// 监听 apiKey 变化（AK 异步获取，可能晚于组件挂载）
watch(() => props.apiKey, (newKey) => {
  if (newKey && !mapLoaded.value && !loadingFailed.value) {
    initMap()
  }
})

// 监听 spots 变化
watch(() => props.spots, (newSpots) => {
  if (mapLoaded.value && bmapInstance && window.BMap) {
    addSpotMarkers(window.BMap)
    drawRoutes(window.BMap)
  }
}, { deep: true })

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (bmapInstance) {
    bmapInstance.clearOverlays()
    bmapInstance = null
  }
  spotMarkers = []
})
</script>

<style scoped>
.baidu-map-container {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: #0f172a;
}

.map-canvas {
  width: 100%;
  height: 100%;
}

.map-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.9);
  z-index: 10;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(148, 163, 184, 0.3);
  border-top-color: #fbbf24;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.map-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.95);
  z-index: 10;
}

.fallback-icon {
  font-size: 48px;
}

.map-fallback h3 {
  color: #e2e8f0;
  margin: 0;
  font-size: 16px;
}

.map-fallback p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  max-width: 280px;
}

.ak-hint {
  font-size: 12px;
  color: #64748b;
}

.ak-hint a {
  color: #60a5fa;
  text-decoration: underline;
}

/* 自定义信息浮窗 */
.spot-info-window {
  position: absolute;
  z-index: 100;
  width: 260px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 12px;
  padding: 14px;
  color: #e2e8f0;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.info-icon {
  font-size: 20px;
}

.info-name {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  color: #fbbf24;
}

.info-close {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
}

.info-desc {
  font-size: 12px;
  line-height: 1.6;
  color: #cbd5e1;
  margin-bottom: 8px;
}

.info-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 10px;
}

.info-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-guide-btn {
  width: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.info-guide-btn:hover {
  opacity: 0.9;
}

/* 实景查看按钮 */
.info-pano-btn {
  width: 100%;
  padding: 8px;
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.info-pano-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.35);
  border-color: rgba(96, 165, 250, 0.7);
}

.info-pano-btn.loading {
  opacity: 0.6;
  cursor: wait;
}

/* 全景确认弹窗 */
.pano-confirm-overlay {
  position: absolute;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.pano-confirm-dialog {
  width: 320px;
  background: rgba(15, 23, 42, 0.97);
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  color: #e2e8f0;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
}

.pano-confirm-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.pano-confirm-dialog h3 {
  font-size: 18px;
  color: #fbbf24;
  margin: 0 0 8px 0;
}

.pano-confirm-dialog p {
  font-size: 13px;
  line-height: 1.7;
  color: #cbd5e1;
  margin: 0 0 20px 0;
}

.pano-hint {
  font-size: 11px;
  color: #64748b;
}

.pano-confirm-actions {
  display: flex;
  gap: 10px;
}

.pano-btn-cancel,
.pano-btn-enter {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}

.pano-btn-cancel {
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
}

.pano-btn-cancel:hover {
  background: rgba(148, 163, 184, 0.35);
}

.pano-btn-enter {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
}

.pano-btn-enter:hover {
  opacity: 0.9;
}


/* 全景不可用提示 */
.pano-unavailable-toast {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 160;
  padding: 10px 24px;
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  backdrop-filter: blur(4px);
  animation: toastFadeOut 3s ease forwards;
  pointer-events: none;
}

@keyframes toastFadeOut {
  0%, 70% { opacity: 1; transform: translateX(-50%) translateY(0); }
  100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
}


/* 地图图例 */
.map-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  z-index: 50;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.spot {
  background: #3b82f6;
  box-shadow: 0 0 6px rgba(59, 130, 246, 0.5);
}

.legend-dot.route {
  width: 16px;
  height: 3px;
  background: #f59e0b;
  border-radius: 2px;
}

.legend-hint {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}
</style>
