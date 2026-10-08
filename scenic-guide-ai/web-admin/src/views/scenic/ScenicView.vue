<template>
  <div class="scenic-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">📍 景点管理</h2>
        <p class="page-subtitle">管理景区各景点信息、GPS坐标与讲解内容</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAdd">新增景点</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>景点列表</span>
              <el-input v-model="search" placeholder="搜索景点..." :prefix-icon="Search" style="width:200px" clearable />
            </div>
          </template>
          <el-table :data="filteredSpots" stripe highlight-current-row @current-change="selectSpot" v-loading="loading">
            <el-table-column label="景点" min-width="200">
              <template #default="{ row }">
                <div class="spot-info">
                  <span class="spot-emoji">{{ row.icon }}</span>
                  <div>
                    <div class="spot-name-text">{{ row.name }}</div>
                    <div class="spot-category">{{ row.category }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="open_time" label="开放时间" width="140" />
            <el-table-column prop="price" label="票价" width="80" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_open ? 'success' : 'danger'" size="small">
                  {{ row.is_open ? '开放' : '关闭' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="editSpot(row)">编辑</el-button>
                <el-button text type="danger" size="small" @click="deleteSpot(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="10">
        <!-- 景点详情卡片 -->
        <el-card v-if="selectedSpot" style="margin-bottom:12px">
          <template #header>
            <div class="card-header">
              <span>{{ selectedSpot.icon }} {{ selectedSpot.name }}</span>
              <el-switch v-model="selectedSpot.is_open" active-text="开放" inactive-text="关闭" size="small" />
            </div>
          </template>
          <div class="spot-image-section">
            <div class="section-label">景点图片</div>
            <div class="spot-image-preview" v-if="spotImageUrls.length > 0">
              <img
                v-for="(imgUrl, idx) in spotImageUrls"
                :key="idx"
                :src="imgUrl"
                :alt="selectedSpot.name"
                class="spot-preview-image"
              />
            </div>
            <div v-else class="spot-image-empty">
              <span style="font-size:32px">🖼️</span>
              <span>暂无图片，点击编辑上传</span>
            </div>
            <el-upload
              :key="'upload-' + (selectedSpot?.id || 0)"
              accept="image/*"
              :show-file-list="false"
              :http-request="customUpload"
              :before-upload="beforeImageUpload"
              style="margin-top:8px"
            >
              <el-button size="small" type="primary" plain :loading="uploading">📷 替换图片</el-button>
            </el-upload>
          </div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="分类">{{ selectedSpot.category }}</el-descriptions-item>
            <el-descriptions-item label="开放时间">{{ selectedSpot.open_time }}</el-descriptions-item>
            <el-descriptions-item label="票价">{{ selectedSpot.price }}</el-descriptions-item>
            <el-descriptions-item label="GPS坐标">{{ selectedSpot.lat }}, {{ selectedSpot.lng }}</el-descriptions-item>
            <el-descriptions-item label="触发半径">{{ selectedSpot.trigger_radius }}米</el-descriptions-item>
          </el-descriptions>
          <div class="spot-desc-section">
            <div class="section-label">景点简介</div>
            <p class="spot-desc-text">{{ selectedSpot.description }}</p>
          </div>
          <div class="spot-desc-section">
            <div class="section-label">AI讲解词</div>
            <p class="spot-desc-text">{{ selectedSpot.guide_text }}</p>
          </div>
        </el-card>
        <el-card v-else style="margin-bottom:12px">
          <el-empty description="点击左侧景点查看详情" />
        </el-card>

        <!-- 📍 坐标管理卡片 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📍 坐标管理</span>
              <div style="display:flex;gap:8px;align-items:center">
                <span v-if="coordDirtyCount > 0" style="font-size:12px;color:#e6a23c">
                  {{ coordDirtyCount }} 处未保存
                </span>
                <el-button
                  type="primary"
                  size="small"
                  :disabled="coordDirtyCount === 0"
                  :loading="coordSaving"
                  @click="saveAllCoords"
                >
                  💾 保存全部坐标
                </el-button>
              </div>
            </div>
          </template>
          <div style="max-height:420px;overflow-y:auto">
            <div
              v-for="spot in spots"
              :key="'coord-' + spot.id"
              class="coord-row"
              :class="{ 'coord-modified': coordEdits[spot.id]?.modified }"
            >
              <span class="coord-icon">{{ spot.icon }}</span>
              <span class="coord-name">{{ spot.name }}</span>
              <template v-if="coordEdits[spot.id]?.hasCoord">
                <el-input
                  v-model="coordEdits[spot.id].lat"
                  size="small"
                  style="width:78px"
                  placeholder="纬度"
                  @input="onCoordChange(spot.id)"
                />
                <span style="color:#999;font-size:11px">,</span>
                <el-input
                  v-model="coordEdits[spot.id].lng"
                  size="small"
                  style="width:78px"
                  placeholder="经度"
                  @input="onCoordChange(spot.id)"
                />
              </template>
              <template v-else>
                <span class="coord-status-na">未添加</span>
                <el-button
                  size="small"
                  type="success"
                  plain
                  @click="addCoord(spot.id)"
                >＋ 添加</el-button>
              </template>
            </div>
            <el-empty v-if="spots.length === 0" description="暂无景点" :image-size="40" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑景点' : '新增景点'" width="780px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <!-- 第一行：名称 + 图标（图标加宽） -->
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="景点名称" prop="name">
              <el-input v-model="form.name" placeholder="输入景点名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="图标" prop="icon">
              <el-select v-model="form.icon" style="width:100%" filterable placeholder="选择图标">
                <el-option v-for="e in emojiOptions" :key="e.value" :label="e.label" :value="e.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <!-- 第二行：分类 + 开放时间 + 票价 -->
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="分类">
              <el-select v-model="form.category" style="width:100%" placeholder="选择分类">
                <el-option label="自然景观" value="自然景观" />
                <el-option label="人文景观" value="人文景观" />
                <el-option label="休闲娱乐" value="休闲娱乐" />
                <el-option label="餐饮服务" value="餐饮服务" />
                <el-option label="基础设施" value="基础设施" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="开放时间">
              <el-input v-model="form.open_time" placeholder="例：08:00-17:30" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="票价">
              <el-input v-model="form.price" placeholder="例：免费 或 ¥20" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="景点简介">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="景点简介，展示给游客的简要说明" />
        </el-form-item>
        <el-form-item label="AI讲解词">
          <el-input v-model="form.guide_text" type="textarea" :rows="4" placeholder="用于AI数字人讲解的详细内容" />
        </el-form-item>
        <el-form-item label="景点图片">
          <div style="display:flex;flex-direction:column;gap:8px;width:100%">
            <el-upload
              accept="image/*"
              :show-file-list="false"
              :http-request="handleDialogUpload"
              :before-upload="beforeImageUpload"
            >
              <el-button type="primary" plain :loading="dialogUploading">
                📷 {{ dialogImageFile ? '更换图片' : '选择图片' }}
              </el-button>
            </el-upload>
            <div v-if="dialogImagePreview" style="position:relative;display:inline-block;width:200px">
              <img :src="dialogImagePreview" style="width:200px;height:120px;object-fit:cover;border-radius:8px;border:1px solid #e0e0e0" />
              <el-button
                circle
                size="small"
                type="danger"
                style="position:absolute;top:-8px;right:-8px"
                @click="clearDialogImage"
              >✕</el-button>
            </div>
            <span v-if="isEdit && !dialogImageFile" style="font-size:12px;color:#999">
              留空则不修改已有图片
            </span>
          </div>
        </el-form-item>
        <el-form-item label="开放状态">
          <el-switch v-model="form.is_open" active-text="开放" inactive-text="关闭" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSpot">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import axios from 'axios'

const api = axios.create({ baseURL: (import.meta.env.BASE_URL || '/').replace(/\/$/, '') + '/api/scenic' })
// 携带管理员令牌（与 sbApi 一致），否则 Spring Boot 会拒绝景点增删改查请求
api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

const search = ref('')
const showDialog = ref(false)
const isEdit = ref(false)
const selectedSpot = ref(null)
const formRef = ref(null)
const loading = ref(false)

// 图标下拉选项 — 按景点类型分类
const emojiOptions = [
  // 入口 & 门楼
  { label: '🚪 入口/大门', value: '🚪' },
  { label: '⛩ 牌坊/门楼', value: '⛩' },
  { label: '🏛 建筑/照壁', value: '🏛' },
  // 山 & 观景
  { label: '🏔️ 山峰', value: '🏔️' },
  { label: '⛰ 山景', value: '⛰' },
  { label: '🔭 观景台', value: '🔭' },
  { label: '🌄 日出观景', value: '🌄' },
  { label: '🌅 日落观景', value: '🌅' },
  // 水景
  { label: '🌊 海/湖景', value: '🌊' },
  { label: '💧 瀑布/水滴', value: '💧' },
  { label: '⛲ 喷泉', value: '⛲' },
  { label: '🏖️ 沙滩/河滩', value: '🏖️' },
  // 建筑 & 宗教
  { label: '🏯 城堡/宫殿', value: '🏯' },
  { label: '🛕 寺庙', value: '🛕' },
  { label: '🙏 佛像/朝圣', value: '🙏' },
  { label: '📿 佛珠/宗教', value: '📿' },
  { label: '🪷 莲花/佛教', value: '🪷' },
  { label: '🕌 清真寺', value: '🕌' },
  { label: '⛪ 教堂', value: '⛪' },
  // 桥梁 & 步道
  { label: '🌉 桥梁', value: '🌉' },
  { label: '🌳 林荫步道', value: '🌳' },
  { label: '🛤️ 步道/古道', value: '🛤️' },
  { label: '🎋 竹林/园林', value: '🎋' },
  // 雕塑 & 石刻
  { label: '🗿 雕塑/石刻', value: '🗿' },
  { label: '🗼 塔/柱', value: '🗼' },
  { label: '🗽 纪念碑', value: '🗽' },
  // 文化 & 演艺
  { label: '🎭 演艺/文化', value: '🎭' },
  { label: '🎨 艺术/壁画', value: '🎨' },
  { label: '🎪 演出/活动', value: '🎪' },
  { label: '🏺 文物/博物', value: '🏺' },
  // 自然 & 动植物
  { label: '🌲 森林/古树', value: '🌲' },
  { label: '🌸 花卉/花园', value: '🌸' },
  { label: '🌿 湿地/草原', value: '🌿' },
  { label: '🦚 孔雀/动物', value: '🦚' },
  { label: '🐉 龙/神兽', value: '🐉' },
  { label: '🐟 鱼/水族', value: '🐟' },
  // 休闲 & 服务
  { label: '😄 休闲/娱乐', value: '😄' },
  { label: '👣 足迹/朝圣路', value: '👣' },
  { label: '🍵 茶馆/休憩', value: '🍵' },
  { label: '🍜 餐饮/美食', value: '🍜' },
  { label: '🛍️ 购物/文创', value: '🛍️' },
  { label: '🏕️ 露营/户外', value: '🏕️' },
  // 古迹 & 遗址
  { label: '🏚️ 遗址/古迹', value: '🏚️' },
  { label: '🪦 墓碑/碑刻', value: '🪦' },
  { label: '📜 古卷/典籍', value: '📜' },
  // 通用
  { label: '📍 地点/其他', value: '📍' },
  { label: '⭐ 热门景点', value: '⭐' },
  { label: '❤️ 推荐', value: '❤️' },
]

const form = ref({
  name: '', icon: '🏔️', category: '自然景观',
  lat: '', lng: '', open_time: '08:00-17:30',
  price: '免费', trigger_radius: 100,
  description: '', guide_text: '', is_open: true
})

const rules = {
  name: [{ required: true, message: '请输入景点名称', trigger: 'blur' }],
  lat: [{ required: true, message: '请输入纬度', trigger: 'blur' }],
  lng: [{ required: true, message: '请输入经度', trigger: 'blur' }]
}

const spots = ref([])
const uploading = ref(false)

// ===== 对话框内图片上传（新增/编辑景点时使用） =====
const dialogImageFile = ref(null)       // 用户选择的文件对象
const dialogImagePreview = ref('')      // 本地预览 URL
const dialogUploading = ref(false)      // 上传中状态

function handleDialogUpload(options) {
  const { file } = options
  // 不真正上传，只暂存文件和生成预览
  dialogImageFile.value = file
  dialogImagePreview.value = URL.createObjectURL(file)
}

function clearDialogImage() {
  if (dialogImagePreview.value) {
    URL.revokeObjectURL(dialogImagePreview.value)
  }
  dialogImageFile.value = null
  dialogImagePreview.value = ''
}

// ═══════════════════════════════════════════════════════
// 坐标管理（右侧坐标卡片）
// ═══════════════════════════════════════════════════════
// 灵山胜境中心坐标（新添加景点默认位置）
const LINGSHAN_DEFAULT = { lat: 31.4275, lng: 120.0945 }

const coordEdits = ref({})   // { [spotId]: { lat, lng, hasCoord, modified } }
const coordSaving = ref(false)
const coordDirtyCount = ref(0)

/** 从 spots 数据初始化坐标编辑状态 */
function initCoordEdits() {
  const edits = {}
  for (const s of spots.value) {
    const hasLat = s.lat != null && s.lat !== '' && !isNaN(parseFloat(s.lat))
    const hasLng = s.lng != null && s.lng !== '' && !isNaN(parseFloat(s.lng))
    const hasCoord = hasLat && hasLng
    edits[s.id] = {
      lat: hasLat ? String(s.lat) : '',
      lng: hasLng ? String(s.lng) : '',
      hasCoord,
      modified: false
    }
  }
  coordEdits.value = edits
  coordDirtyCount.value = 0
}

/** 添加默认坐标（灵山中心） */
function addCoord(spotId) {
  const edit = coordEdits.value[spotId]
  if (!edit) return
  edit.lat = String(LINGSHAN_DEFAULT.lat)
  edit.lng = String(LINGSHAN_DEFAULT.lng)
  edit.hasCoord = true
  edit.modified = true
  coordDirtyCount.value = Object.values(coordEdits.value).filter(e => e.modified).length
}

/** 坐标值变更时标记为已修改 */
function onCoordChange(spotId) {
  const edit = coordEdits.value[spotId]
  if (!edit) return
  edit.modified = true
  coordDirtyCount.value = Object.values(coordEdits.value).filter(e => e.modified).length
}

/** 批量保存所有修改过的坐标 */
async function saveAllCoords() {
  const token = localStorage.getItem('admin_token')
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const modified = Object.entries(coordEdits.value)
    .filter(([_, e]) => e.modified)
    .map(([id, e]) => ({
      id: parseInt(id),
      latitude: parseFloat(e.lat) || null,
      longitude: parseFloat(e.lng) || null
    }))

  if (modified.length === 0) {
    ElMessage.info('没有需要保存的坐标')
    return
  }

  coordSaving.value = true
  let successCount = 0
  let failCount = 0

  for (const m of modified) {
    try {
      await api.put(`/spots/${m.id}`, {
        scenicId: 1,
        latitude: m.latitude,
        longitude: m.longitude
      })
      successCount++
      // 标记为已保存
      if (coordEdits.value[m.id]) {
        coordEdits.value[m.id].modified = false
      }
    } catch (e) {
      failCount++
      console.error(`[coord] 保存景点${m.id}坐标失败:`, e)
    }
  }

  coordSaving.value = false
  coordDirtyCount.value = Object.values(coordEdits.value).filter(e => e.modified).length

  if (failCount === 0) {
    ElMessage.success(`✅ 全部坐标已保存（${successCount} 处）`)
  } else {
    ElMessage.warning(`⚠️ ${successCount} 处成功，${failCount} 处失败`)
  }

  // 刷新列表以更新左侧表格和详情面板
  await fetchSpots()
  initCoordEdits()
}

// 自定义上传 — 使用 axios 替代 el-upload 默认 XHR，确保正确代理和响应解析
async function customUpload(options) {
  const { file, onSuccess, onError } = options
  uploading.value = true
  const formData = new FormData()
  formData.append('file', file)
  const spotId = selectedSpot.value?.id || 0
  const url = '/api/scenic/spots/' + spotId + '/upload-image'
  const token = localStorage.getItem('admin_token')
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  console.log('[upload] POST', url, 'file:', file.name, file.size)
  try {
    const { data } = await axios.post(url, formData, { headers })
    console.log('[upload] response:', data)
    if (data.code === 200 && data.data?.url) {
      const newUrl = data.data.url
      // 替换选中景点的图片（而非追加）
      if (selectedSpot.value) {
        selectedSpot.value.images = [newUrl]
        console.log('[upload] images replaced:', selectedSpot.value.images)
      }
      ElMessage.success('图片上传成功')
      onSuccess(data)
    } else {
      ElMessage.error(data.message || '图片上传失败')
      onError(new Error(data.message || '图片上传失败'))
    }
  } catch (e) {
    console.error('[upload] error:', e)
    ElMessage.error('图片上传失败: ' + (e.response?.data?.message || e.message))
    onError(e)
  } finally {
    uploading.value = false
  }
}

const spotImageUrls = computed(() => {
  if (!selectedSpot.value) return []
  const images = selectedSpot.value.images
  if (Array.isArray(images)) return images.filter(Boolean)
  if (typeof images === 'string') return [images]
  return []
})

function beforeImageUpload(file) {
  console.log('[upload] beforeImageUpload:', file.name, file.type, file.size)
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('图片大小不能超过 10MB')
    return false
  }
  return true
}

// 后端数据 → 前端格式
function toFrontend(spot) {
  return {
    id: spot.id,
    scenicId: spot.scenicId || 1,
    name: spot.name || '',
    icon: spot.icon || '🏔️',
    category: spot.category || '自然景观',
    lat: spot.latitude ?? spot.lat ?? '',
    lng: spot.longitude ?? spot.lng ?? '',
    open_time: spot.openTime || spot.open_time || '全天',
    price: spot.price || '免费',
    trigger_radius: spot.triggerRadius ?? spot.trigger_radius ?? 50,
    description: spot.description || '',
    guide_text: spot.guideText || spot.guide_text || '',
    images: spot.images || [],
    is_open: spot.isActive !== undefined ? spot.isActive : (spot.is_open !== undefined ? spot.is_open : true),
    orderNum: spot.orderNum || 0,
    durationMinutes: spot.durationMinutes || 5
  }
}

// 前端格式 → 后端格式
function toBackend(form) {
  return {
    scenicId: 1,
    name: form.name,
    icon: form.icon,
    category: form.category,
    latitude: parseFloat(form.lat) || null,
    longitude: parseFloat(form.lng) || null,
    openTime: form.open_time,
    price: form.price,
    triggerRadius: form.trigger_radius,
    description: form.description,
    guideText: form.guide_text,
    isActive: form.is_open
  }
}

async function fetchSpots() {
  loading.value = true
  try {
    const { data } = await api.get('/spots')
    // Python 后端直接返回 {spots: [...]}，Spring Boot 返回 {code: 200, data: {spots: [...]}}
    const rawSpots = data?.data?.spots || data?.spots || []
    if (rawSpots.length) {
      spots.value = rawSpots.map(toFrontend)
    }
    // 初始化坐标编辑状态
    initCoordEdits()
  } catch (e) {
    ElMessage.error('获取景点列表失败: ' + (e.response?.data?.message || e.message))
  } finally {
    loading.value = false
  }
}

const filteredSpots = computed(() => {
  if (!search.value) return spots.value
  return spots.value.filter(s => s.name.includes(search.value) || s.category.includes(search.value))
})

function selectSpot(row) {
  selectedSpot.value = row
}

function openAdd() {
  isEdit.value = false
  form.value = { name: '', icon: '🏔️', category: '自然景观', lat: '', lng: '', open_time: '08:00-17:30', price: '免费', trigger_radius: 100, description: '', guide_text: '', is_open: true }
  clearDialogImage()
  showDialog.value = true
}

function editSpot(row) {
  isEdit.value = true
  form.value = { ...row }
  showDialog.value = true
}

async function saveSpot() {
  // 走完整表单校验（名称、经纬度等 required 规则），校验失败直接中断
  try {
    await formRef.value?.validate()
  } catch {
    ElMessage.warning('请完整填写必填项')
    return
  }
  const payload = toBackend(form.value)
  try {
    let savedSpotId = form.value.id
    if (isEdit.value) {
      await api.put(`/spots/${form.value.id}`, payload)
      ElMessage.success('景点信息已更新')
    } else {
      const resp = await api.post('/spots', payload)
      const data = resp.data
      if (data.code === 200 && data.data?.id) {
        savedSpotId = data.data.id
        ElMessage.success('景点已添加')
      } else {
        ElMessage.success('景点已添加')
      }
    }
    // 如果有选择图片，上传到新创建/编辑的景点
    if (dialogImageFile.value && savedSpotId) {
      const formData = new FormData()
      formData.append('file', dialogImageFile.value)
      const token = localStorage.getItem('admin_token')
      const headers = token ? { Authorization: `Bearer ${token}` } : {}
      try {
        const uploadResp = await axios.post(
          `/api/scenic/spots/${savedSpotId}/upload-image`,
          formData,
          { headers }
        )
        if (uploadResp.data?.code === 200) {
          console.log('[saveSpot] 图片上传成功:', uploadResp.data.data?.url)
        }
      } catch (e) {
        console.error('[saveSpot] 图片上传失败:', e)
        ElMessage.warning('景点已保存，但图片上传失败，可在编辑中重新上传')
      }
    }
    showDialog.value = false
    clearDialogImage()
    await fetchSpots()
    // 刷新详情面板
    if (selectedSpot.value && isEdit.value) {
      const updated = spots.value.find(s => s.id === selectedSpot.value.id)
      if (updated) selectedSpot.value = updated
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.message || e.message))
  }
}

async function deleteSpot(row) {
  await ElMessageBox.confirm(`确认删除景点"${row.name}"？`, '确认', { type: 'warning' })
  try {
    await api.delete(`/spots/${row.id}`)
    if (selectedSpot.value?.id === row.id) selectedSpot.value = null
    ElMessage.success('已删除')
    await fetchSpots()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.response?.data?.message || e.message))
  }
}

onMounted(() => {
  fetchSpots()
})
</script>

<style scoped>
.scenic-page {}
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; }
.page-subtitle { font-size: 13px; color: #888; margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.spot-info { display: flex; align-items: center; gap: 10px; }
.spot-emoji { font-size: 24px; }
.spot-name-text { font-size: 14px; font-weight: 500; }
.spot-category { font-size: 12px; color: #888; }
.spot-image-section {
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}
.spot-image-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.spot-preview-image {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #eee;
}
.spot-image-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px;
  color: #bbb;
  font-size: 13px;
}
.spot-desc-section { margin-top: 16px; }
.section-label { font-size: 13px; color: #888; margin-bottom: 6px; font-weight: 500; }
.spot-desc-text { font-size: 14px; line-height: 1.7; color: #444; }
.input-with-unit { display: flex; align-items: center; gap: 0; }
.unit-suffix { margin-left: 8px; font-size: 13px; color: #888; white-space: nowrap; flex-shrink: 0; }

/* ===== 坐标管理 ===== */
.coord-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}
.coord-row:last-child { border-bottom: none; }
.coord-row:hover { background: #fafafa; }
.coord-row.coord-modified { background: #fef3e2; }
.coord-icon { font-size: 14px; flex-shrink: 0; }
.coord-name {
  font-size: 13px;
  color: #333;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.coord-status-na {
  font-size: 12px;
  color: #e6a23c;
  font-weight: 500;
  flex-shrink: 0;
}
</style>
