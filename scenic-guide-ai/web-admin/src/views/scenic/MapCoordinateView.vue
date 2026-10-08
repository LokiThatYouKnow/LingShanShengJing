<template>
  <div class="coord-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">📍 实景地图坐标点设置</h2>
        <p class="page-subtitle">在地图上拖拽标记设置景点精确位置，保存后同步到前端实景地图</p>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="saveAllCoords" :loading="saving">
          💾 保存全部坐标
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="coord-main">
      <!-- 左侧：百度地图 -->
      <el-col :span="16">
        <el-card shadow="never" class="map-card">
          <div class="map-hint" v-if="!mapLoaded">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <span>正在加载百度地图...</span>
          </div>
          <div ref="mapContainer" class="baidu-map-container" v-show="mapLoaded"></div>
        </el-card>
      </el-col>

      <!-- 右侧：景点列表 & 坐标编辑 -->
      <el-col :span="8">
        <el-card shadow="never" class="spot-list-card">
          <template #header>
            <div class="card-header">
              <span>景点坐标列表 ({{ spots.length }})</span>
              <el-input v-model="search" placeholder="搜索..." size="small" clearable style="width:130px" />
            </div>
          </template>

          <div class="spot-coord-list">
            <div
              v-for="spot in filteredSpots"
              :key="spot.id"
              class="spot-coord-item"
              :class="{ active: activeSpotId === spot.id, changed: spot._changed }"
              @click="focusSpot(spot)"
            >
              <div class="spot-item-header">
                <span class="spot-item-icon">{{ spot.icon }}</span>
                <span class="spot-item-name">{{ spot.name }}</span>
                <el-tag v-if="spot._changed" type="warning" size="small" effect="dark">已修改</el-tag>
                <el-tag v-else-if="spot.lat == null || spot.lng == null" type="info" size="small">未添加</el-tag>
              </div>
              <div class="spot-item-coords">
                <div class="coord-row" v-if="spot.lat != null && spot.lng != null">
                  <span class="coord-label">WGS-84</span>
                  <span class="coord-val">{{ fmt(spot.lat) }}, {{ fmt(spot.lng) }}</span>
                </div>
                <div class="coord-row" v-if="spot._bdLat != null">
                  <span class="coord-label">BD-09</span>
                  <span class="coord-val bd">{{ fmt(spot._bdLat) }}, {{ fmt(spot._bdLng) }}</span>
                </div>
                <div class="coord-row" v-if="spot.lat == null || spot.lng == null">
                  <span class="coord-label" style="color:#e6a23c">尚无坐标，点击下方按钮添加到地图</span>
                </div>
              </div>
              <!-- 未添加坐标：显示添加按钮 -->
              <div class="spot-item-actions" v-if="spot.lat == null || spot.lng == null">
                <el-button size="small" type="success" @click.stop="addNewSpotMarker(spot)">＋ 添加坐标</el-button>
              </div>
              <!-- 已修改：显示保存/撤销 -->
              <div class="spot-item-actions" v-if="spot._changed">
                <el-button size="small" type="primary" @click.stop="saveSpotCoord(spot)">保存</el-button>
                <el-button size="small" @click.stop="revertSpot(spot)">撤销</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
defineOptions({ name: 'MapCoordinateView' })
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import axios from 'axios'
import ttsApi from '@/api'
import { wgs84ToBd09, bd09ToWgs84 } from '@/utils/coordTransform.js'

const api = axios.create({ baseURL: '/api/scenic' })
api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

// ===== 状态 =====
const mapContainer = ref(null)
const mapLoaded = ref(false)
const search = ref('')
const activeSpotId = ref(null)
const saving = ref(false)
const spots = ref([])

let bmap = null
let markers = {}

// ===== 百度地图 AK =====
const BAIDU_AK = ref('')

// ===== 加载百度地图 JS =====
function loadBaiduMapScript(ak) {
  return new Promise((resolve, reject) => {
    if (window.BMap) { resolve(); return }
    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/api?v=3.0&ak=${ak}&callback=onBMapLoaded`
    script.onerror = reject
    window.onBMapLoaded = () => resolve()
    document.head.appendChild(script)
  })
}

// ===== 初始化地图 =====
async function initMap() {
  // 获取 AK
  try {
    const data = await ttsApi.get('/config/public')
    BAIDU_AK.value = data?.baidu_map_ak || ''
  } catch {
    BAIDU_AK.value = ''
  }

  if (!BAIDU_AK.value) {
    ElMessage.error('未获取到百度地图AK')
    return
  }

  try {
    await loadBaiduMapScript(BAIDU_AK.value)
  } catch {
    ElMessage.error('百度地图加载失败')
    return
  }

  await nextTick()
  if (!mapContainer.value) return

  bmap = new BMap.Map(mapContainer.value, { enableMapClick: false })
  // 灵山景区中心：所有景点标记的几何中心，确保初始视角覆盖整个景区
  bmap.centerAndZoom(new BMap.Point(120.0945, 31.4275), 16)
  bmap.enableScrollWheelZoom(true)
  bmap.addControl(new BMap.NavigationControl())
  bmap.addControl(new BMap.ScaleControl())

  mapLoaded.value = true
  await nextTick()

  // 加载景点标记
  await fetchSpots()
  placeAllMarkers()
}

// ===== 获取景点 =====
async function fetchSpots() {
  try {
    const { data } = await api.get('/spots')
    const rawSpots = data?.spots || data?.data?.spots || []
    spots.value = rawSpots.map(s => {
      const lat = s.latitude ?? s.lat ?? null
      const lng = s.longitude ?? s.lng ?? null
      let bd = { lng: null, lat: null }
      if (lat != null && lng != null) {
        bd = wgs84ToBd09(lng, lat)
      }
      return {
        id: s.id,
        name: s.name,
        icon: s.icon || '📍',
        category: s.category || '',
        lat: lat,
        lng: lng,
        _origLat: lat,
        _origLng: lng,
        _bdLat: bd.lat,
        _bdLng: bd.lng,
        _changed: false
      }
    })
  } catch (e) {
    ElMessage.error('获取景点列表失败')
  }
}

// ===== 放置所有标记 =====
function placeAllMarkers() {
  if (!bmap) return
  // 清除旧标记
  Object.values(markers).forEach(m => bmap.removeOverlay(m))
  markers = {}

  spots.value.forEach(spot => {
    if (spot._bdLat == null || spot._bdLng == null) return
    const pt = new BMap.Point(spot._bdLng, spot._bdLat)
    const marker = new BMap.Marker(pt, { enableDragging: true })

    // 点击 → 高亮
    marker.addEventListener('click', () => {
      activeSpotId.value = spot.id
      // 打开信息窗
      const infoWindow = new BMap.InfoWindow(
        `<div style="padding:4px 8px;font-size:13px;min-width:120px">
          <strong>${spot.icon} ${spot.name}</strong><br/>
          <span style="color:#888">BD-09: ${spot._bdLng?.toFixed(6)}, ${spot._bdLat?.toFixed(6)}</span><br/>
          <span style="color:#888">WGS-84: ${spot.lng?.toFixed(6)}, ${spot.lat?.toFixed(6)}</span>
        </div>`,
        { width: 240 }
      )
      marker.openInfoWindow(infoWindow)
    })

    // 拖拽结束 → 更新坐标
    marker.addEventListener('dragend', (e) => {
      const bdLng = e.point.lng
      const bdLat = e.point.lat
      const wgs = bd09ToWgs84(bdLng, bdLat)
      spot._bdLng = bdLng
      spot._bdLat = bdLat
      spot.lng = wgs.lng
      spot.lat = wgs.lat
      spot._changed = (Math.abs(wgs.lng - spot._origLng) > 0.00001 || Math.abs(wgs.lat - spot._origLat) > 0.00001)
    })

    bmap.addOverlay(marker)
    markers[spot.id] = marker
  })
}

// ===== 聚焦景点 =====
function focusSpot(spot) {
  activeSpotId.value = spot.id
  if (bmap && spot._bdLat != null) {
    bmap.panTo(new BMap.Point(spot._bdLng, spot._bdLat))
    // 打开信息窗
    if (markers[spot.id]) {
      const infoWindow = new BMap.InfoWindow(
        `<div style="padding:4px 8px;font-size:13px;min-width:120px">
          <strong>${spot.icon} ${spot.name}</strong><br/>
          <span style="color:#888">拖拽标记调整位置</span>
        </div>`,
        { width: 200 }
      )
      markers[spot.id].openInfoWindow(infoWindow)
    }
  }
}

// ===== 为新景点添加默认坐标标记 =====
function addNewSpotMarker(spot) {
  if (!bmap) return
  // 灵山景区默认坐标（WGS-84），加微小随机偏移避免重叠
  const jitter = (Math.random() - 0.5) * 0.002
  const defaultLat = 31.4275 + jitter
  const defaultLng = 120.0945 + jitter
  const bd = wgs84ToBd09(defaultLng, defaultLat)

  // 更新 spot 数据
  spot.lat = roundCoord(defaultLat)
  spot.lng = roundCoord(defaultLng)
  spot._origLat = null  // 原始为空，标记为新添加
  spot._origLng = null
  spot._bdLat = bd.lat
  spot._bdLng = bd.lng
  spot._changed = true

  // 创建可拖拽标记
  const pt = new BMap.Point(bd.lng, bd.lat)
  const marker = new BMap.Marker(pt, { enableDragging: true })

  marker.addEventListener('click', () => {
    activeSpotId.value = spot.id
    const infoWindow = new BMap.InfoWindow(
      `<div style="padding:4px 8px;font-size:13px;min-width:140px">
        <strong>${spot.icon} ${spot.name}</strong><br/>
        <span style="color:#e6a23c">🆕 新增，拖拽校准位置</span><br/>
        <span style="color:#888">BD-09: ${bd.lng.toFixed(6)}, ${bd.lat.toFixed(6)}</span>
      </div>`,
      { width: 240 }
    )
    marker.openInfoWindow(infoWindow)
  })

  marker.addEventListener('dragend', (e) => {
    const bdLng = e.point.lng
    const bdLat = e.point.lat
    const wgs = bd09ToWgs84(bdLng, bdLat)
    spot._bdLng = bdLng
    spot._bdLat = bdLat
    spot.lng = wgs.lng
    spot.lat = wgs.lat
    spot._changed = true
  })

  bmap.addOverlay(marker)
  markers[spot.id] = marker

  // 地图定位到新标记
  bmap.panTo(pt)
  activeSpotId.value = spot.id
  ElMessage.success(`已为「${spot.name}」添加默认坐标，请拖拽校准位置后保存`)
}

// ===== 保存单个景点 =====
async function saveSpotCoord(spot) {
  try {
    await api.put(`/spots/${spot.id}`, {
      latitude: roundCoord(spot.lat),
      longitude: roundCoord(spot.lng)
    })
    spot._origLat = spot.lat
    spot._origLng = spot.lng
    spot._changed = false
    // 更新标记位置
    if (markers[spot.id] && spot._bdLat != null) {
      markers[spot.id].setPosition(new BMap.Point(spot._bdLng, spot._bdLat))
    }
    ElMessage.success(`${spot.name} 坐标已保存`)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  }
}

// ===== 批量保存 =====
async function saveAllCoords() {
  const changed = spots.value.filter(s => s._changed)
  if (changed.length === 0) {
    ElMessage.info('没有需要保存的修改')
    return
  }
  saving.value = true
  let ok = 0, fail = 0
  for (const spot of changed) {
    try {
      await api.put(`/spots/${spot.id}`, {
        latitude: roundCoord(spot.lat),
        longitude: roundCoord(spot.lng)
      })
      spot._origLat = spot.lat
      spot._origLng = spot.lng
      spot._changed = false
      ok++
    } catch {
      fail++
    }
  }
  saving.value = false
  ElMessage.success(`已保存 ${ok} 个${fail > 0 ? `，失败 ${fail} 个` : ''}`)
}

// ===== 撤销 =====
function revertSpot(spot) {
  spot.lat = spot._origLat
  spot.lng = spot._origLng
  spot._changed = false
  // 如果原始坐标为空（新添加后撤销），移除地图标记
  if (spot._origLat == null || spot._origLng == null) {
    spot._bdLat = null
    spot._bdLng = null
    if (markers[spot.id]) {
      bmap?.removeOverlay(markers[spot.id])
      delete markers[spot.id]
    }
    return
  }
  const bd = wgs84ToBd09(spot._origLng, spot._origLat)
  spot._bdLat = bd.lat
  spot._bdLng = bd.lng
  if (markers[spot.id] && spot._bdLat != null) {
    markers[spot.id].setPosition(new BMap.Point(spot._bdLng, spot._bdLat))
  }
}

// ===== 工具 =====
function roundCoord(v) {
  return v == null ? null : Math.round(v * 1000000) / 1000000
}

function fmt(v) {
  return v == null ? '--' : v.toFixed(6)
}

const filteredSpots = computed(() => {
  if (!search.value) return spots.value
  const kw = search.value.toLowerCase()
  return spots.value.filter(s => s.name.toLowerCase().includes(kw))
})

// ===== 生命周期 =====
onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (bmap) {
    bmap.clearOverlays()
    bmap = null
  }
  delete window.onBMapLoaded
})
</script>

<style scoped>
.coord-page { height: 100%; display: flex; flex-direction: column; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-shrink: 0; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { font-size: 13px; color: #888; margin: 4px 0 0 0; }
.header-actions { display: flex; gap: 8px; }

.coord-main { flex: 1; min-height: 0; }
.coord-main .el-row { height: 100%; }
.coord-main .el-col { height: 100%; }

.map-card { height: 100%; }
.map-card :deep(.el-card__body) { height: calc(100% - 58px); padding: 0; position: relative; }

.baidu-map-container {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.map-hint {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #888;
  font-size: 14px;
}

.spot-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.spot-list-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.spot-coord-list {
  height: 100%;
  overflow-y: auto;
  padding: 0 8px;
}
.spot-coord-list::-webkit-scrollbar { width: 4px; }
.spot-coord-list::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 2px; }

.spot-coord-item {
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.spot-coord-item:hover {
  background: #f5f7fa;
  border-color: #e4e7ed;
}
.spot-coord-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}
.spot-coord-item.changed {
  border-color: #e6a23c;
  background: #fef8ee;
}

.spot-item-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.spot-item-icon { font-size: 16px; }
.spot-item-name { font-size: 14px; font-weight: 600; flex: 1; }

.spot-item-coords {
  font-size: 12px;
  color: #666;
}
.coord-row {
  display: flex;
  justify-content: space-between;
  padding: 1px 0;
}
.coord-label {
  color: #999;
  font-weight: 500;
}
.coord-val {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #333;
}
.coord-val.bd {
  color: #909399;
}

.spot-item-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
</style>
