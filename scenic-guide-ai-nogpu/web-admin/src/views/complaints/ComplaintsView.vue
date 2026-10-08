<template>
  <div class="complaints-page">
    <!-- 页面标题 + 数据模式切换 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">📝 投诉与建议</h2>
        <p class="page-subtitle">管理游客投诉反馈与优化建议</p>
      </div>
      <div class="header-actions">
        <el-switch
          v-model="useMockData"
          active-text="演示数据"
          inactive-text="真实数据"
          @change="loadData"
        />
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="12" :md="6" :lg="6">
        <div class="stat-card" style="border-left: 4px solid #f56c6c">
          <div class="stat-value">{{ stats.total || 0 }}</div>
          <div class="stat-label">总提交数</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6" :lg="6">
        <div class="stat-card" style="border-left: 4px solid #e6a23c">
          <div class="stat-value">{{ stats.pending || 0 }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6" :lg="6">
        <div class="stat-card" style="border-left: 4px solid #409eff">
          <div class="stat-value">{{ stats.processing || 0 }}</div>
          <div class="stat-label">处理中</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6" :lg="6">
        <div class="stat-card" style="border-left: 4px solid #67c23a">
          <div class="stat-value">{{ stats.resolved || 0 }}</div>
          <div class="stat-label">已解决</div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :sm="24" :md="12" :lg="12">
        <el-card shadow="hover">
          <template #header><span>类型分布</span></template>
          <div ref="typeChartEl" style="height: 280px"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12" :lg="12">
        <el-card shadow="hover">
          <template #header><span>分类统计</span></template>
          <div ref="catChartEl" style="height: 280px"></div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>每日趋势（近30天）</span></template>
          <div ref="trendChartEl" style="height: 280px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>处理状态</span></template>
          <div ref="statusChartEl" style="height: 280px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 列表区 -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>投诉与建议列表</span>
          <div style="display: flex; gap: 12px">
            <el-select v-model="filterType" placeholder="类型" clearable style="width: 120px" @change="onFilterChange">
              <el-option label="投诉" value="complaint" />
              <el-option label="建议" value="suggestion" />
            </el-select>
            <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="onFilterChange">
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="processing" />
              <el-option label="已解决" value="resolved" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
          </div>
        </div>
      </template>
      <el-table :data="list" stripe style="width: 100%" v-loading="listLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === 'complaint' ? 'danger' : 'warning'" size="small">
              {{ row.type === 'complaint' ? '投诉' : '建议' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="80" />
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="tourist_name" label="提交人" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openReply(row)">回复</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="list.length === 0 && !listLoading" class="empty-state">
        <el-empty description="暂无投诉与建议记录" :image-size="60" />
      </div>
      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="pageSize" v-model:current-page="page" @current-change="onPageChange" />
      </div>
    </el-card>

    <!-- 回复弹窗 -->
    <el-dialog v-model="replyVisible" title="处理回复" width="500px">
      <el-form label-width="80px">
        <el-form-item label="状态">
          <el-select v-model="replyForm.status" style="width: 100%">
            <el-option label="处理中" value="processing" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="回复内容">
          <el-input v-model="replyForm.admin_reply" type="textarea" :rows="4" placeholder="请输入回复内容" />
        </el-form-item>
      </el-form>
      <div style="background: #f5f7fa; padding: 12px; border-radius: 8px; margin-bottom: 16px">
        <div style="font-weight: 600; margin-bottom: 6px">{{ replyItem?.title }}</div>
        <div style="color: #666; font-size: 13px">{{ replyItem?.content }}</div>
      </div>
      <template #footer>
        <el-button @click="replyVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReply" :loading="replyLoading">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onActivated, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api'
import * as echarts from 'echarts'

const page = ref(1)
const pageSize = 20
const total = ref(0)
const list = ref([])
const listLoading = ref(false)
const filterType = ref('')
const filterStatus = ref('')

const stats = reactive({ total: 0, pending: 0, processing: 0, resolved: 0 })

// Mock/Real 数据切换
const useMockData = ref(true)

// 图表
const typeChartEl = ref(null)
const catChartEl = ref(null)
const trendChartEl = ref(null)
const statusChartEl = ref(null)
let typeChart, catChart, trendChart, statusChart

// 回复弹窗
const replyVisible = ref(false)
const replyLoading = ref(false)
const replyItem = ref(null)
const replyForm = reactive({ status: 'resolved', admin_reply: '' })

function statusType(s) {
  return { pending: 'info', processing: '', resolved: 'success', rejected: 'danger' }[s] || 'info'
}
function statusLabel(s) {
  return { pending: '待处理', processing: '处理中', resolved: '已解决', rejected: '已驳回' }[s] || s
}
function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

// ===== 演示数据 =====
let mockIdCounter = 100
const mockList = ref([
  { id: 1, type: 'complaint', category: '服务', title: '导游讲解态度不好', content: '今天在景区遇到的导游态度非常差，爱理不理的，完全没有介绍景点的意思。', tourist_name: '张先生', status: 'pending', created_at: '2026-07-04T14:30:00' },
  { id: 2, type: 'complaint', category: '设施', title: '洗手间卫生太差', content: '九龙灌浴旁边的洗手间卫生状况堪忧，地面湿滑，没有纸巾，希望加强清洁。', tourist_name: '李女士', status: 'processing', created_at: '2026-07-04T13:15:00', admin_reply: '已通知保洁部门处理' },
  { id: 3, type: 'suggestion', category: '环境', title: '建议增加休息区座椅', content: '景区面积很大，老人小孩走累了没地方坐，建议沿途多设置一些休息座椅。', tourist_name: '王大爷', status: 'resolved', created_at: '2026-07-04T11:20:00', admin_reply: '感谢您的建议，已纳入下季度改造计划' },
  { id: 4, type: 'complaint', category: '安全', title: '台阶处缺少警示标识', content: '菩提大道有几处台阶没有警示标识，家里老人差点摔倒，非常危险。', tourist_name: '赵女士', status: 'pending', created_at: '2026-07-04T10:05:00' },
  { id: 5, type: 'suggestion', category: '服务', title: '希望增加英文讲解', content: '带外国朋友来游览，发现语音导览只有中文，希望能增加英文版本。', tourist_name: '陈先生', status: 'processing', created_at: '2026-07-03T16:40:00', admin_reply: '多语言功能正在开发中' },
  { id: 6, type: 'complaint', category: '设施', title: '停车场指示不清', content: 'P2停车场入口非常难找，导航也定位不准，绕了两圈才找到。', tourist_name: '刘先生', status: 'resolved', created_at: '2026-07-03T15:10:00', admin_reply: '已增设引导指示牌' },
  { id: 7, type: 'suggestion', category: '环境', title: '音乐声音太大', content: '景区背景音乐音量过大，影响游览体验，尤其是祥符禅寺附近应该保持安静。', tourist_name: '周女士', status: 'pending', created_at: '2026-07-03T14:22:00' },
  { id: 8, type: 'complaint', category: '票务', title: '线上购票无法退款', content: '因为临时有事没法去，APP上买的票却找不到退款入口，客服也联系不上。', tourist_name: '吴先生', status: 'pending', created_at: '2026-07-03T12:08:00' },
  { id: 9, type: 'suggestion', category: '服务', title: '建议开发小程序版', content: 'APP下载太占内存了，能不能开发一个微信小程序版本，方便游客使用。', tourist_name: '孙先生', status: 'resolved', created_at: '2026-07-03T11:45:00', admin_reply: '小程序已在开发中，预计下月上线' },
  { id: 10, type: 'complaint', category: '票务', title: '票价偏贵', content: '一家五口来玩，光门票就花了一千多，觉得性价比不高，希望能推出家庭套票。', tourist_name: '黄女士', status: 'processing', created_at: '2026-07-03T10:30:00', admin_reply: '已转达市场部评估' },
  { id: 11, type: 'suggestion', category: '环境', title: '建议多种些遮阳树', content: '夏天太晒了，尤其是大佛广场那边完全没有遮挡，建议多种些大树。', tourist_name: '杨先生', status: 'pending', created_at: '2026-07-02T16:55:00' },
  { id: 12, type: 'complaint', category: '设施', title: '充电桩不够用', content: '开电动车来的，景区只有4个充电桩全被占满了，等了快一小时。', tourist_name: '马先生', status: 'rejected', created_at: '2026-07-02T14:20:00', admin_reply: '景区外500米有商业充电站，建议前往' },
])

function computeMockStats() {
  const all = mockList.value
  stats.total = all.length
  stats.pending = all.filter(i => i.status === 'pending').length
  stats.processing = all.filter(i => i.status === 'processing').length
  stats.resolved = all.filter(i => i.status === 'resolved').length
}

const mockTypeData = [
  { type: 'complaint', count: 7 },
  { type: 'suggestion', count: 5 }
]

const mockCatData = [
  { category: '服务', count: 4 },
  { category: '设施', count: 3 },
  { category: '环境', count: 3 },
  { category: '票务', count: 2 },
]

// 近30天趋势
function generateMockTrend() {
  const dates = []
  const now = new Date()
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const ds = d.toISOString().substring(0, 10)
    dates.push({
      date: ds,
      complaint: Math.floor(Math.random() * 4),
      suggestion: Math.floor(Math.random() * 3)
    })
  }
  return dates
}

const mockStatusData = [
  { status: 'pending', count: 4 },
  { status: 'processing', count: 3 },
  { status: 'resolved', count: 4 },
  { status: 'rejected', count: 1 }
]

// ===== 数据加载调度 =====
function loadData() {
  page.value = 1
  if (useMockData.value) {
    loadMockData()
  } else {
    fetchList()
    fetchAnalytics()
  }
}

function onFilterChange() {
  page.value = 1
  loadData()
}

function onPageChange(p) {
  page.value = p
  loadData()
}

function loadMockData() {
  // 筛选
  let filtered = [...mockList.value]
  if (filterType.value) {
    filtered = filtered.filter(i => i.type === filterType.value)
  }
  if (filterStatus.value) {
    filtered = filtered.filter(i => i.status === filterStatus.value)
  }
  total.value = filtered.length
  const start = (page.value - 1) * pageSize
  list.value = filtered.slice(start, start + pageSize)

  // 统计
  computeMockStats()

  // 图表
  renderTypeChart(mockTypeData)
  renderCatChart(mockCatData)
  renderTrendChart(generateMockTrend())
  renderStatusChart(mockStatusData)
}

// ===== 真实数据 API =====
async function fetchList() {
  listLoading.value = true
  try {
    const res = await adminApi.getComplaints({ page: page.value, size: pageSize, type: filterType.value || undefined, status: filterStatus.value || undefined })
    list.value = res?.items || []
    total.value = res?.total || 0
  } catch (e) {
    ElMessage.error('获取投诉列表失败: ' + (e.response?.data?.detail || e.message || '网络错误'))
    list.value = []
    total.value = 0
  } finally {
    listLoading.value = false
  }
}

async function fetchAnalytics() {
  try {
    const res = await adminApi.getComplaintsAnalytics({ days: 30 })
    const ss = res?.status_stats || []
    stats.total = ss.reduce((a, b) => a + b.count, 0)
    stats.pending = ss.find(s => s.status === 'pending')?.count || 0
    stats.processing = ss.find(s => s.status === 'processing')?.count || 0
    stats.resolved = ss.find(s => s.status === 'resolved')?.count || 0
    renderTypeChart(res?.type_stats || [])
    renderCatChart(res?.category_stats || [])
    renderTrendChart(res?.daily_trend || [])
    renderStatusChart(res?.status_stats || [])
  } catch (e) {
    ElMessage.error('获取分析数据失败: ' + (e.response?.data?.detail || e.message || '网络错误'))
  }
}

// ===== 图表渲染 =====
function renderTypeChart(data) {
  if (!typeChart) return
  const typeMap = { complaint: '投诉', suggestion: '建议' }
  typeChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      data: data.map(d => ({ name: typeMap[d.type] || d.type, value: d.count })),
      emphasis: { label: { show: true, fontSize: 14 } },
      itemStyle: { borderRadius: 6 },
      color: ['#f56c6c', '#e6a23c'],
    }]
  })
}

function renderCatChart(data) {
  if (!catChart) return
  const categories = data.map(d => d.category || '未知')
  const counts = data.map(d => d.count)
  catChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: categories, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'bar', data: counts, barWidth: '40%', itemStyle: { borderRadius: [4, 4, 0, 0], color: '#409eff' } }],
    grid: { left: 50, right: 20, bottom: 40, top: 20 },
  })
}

function renderTrendChart(data) {
  if (!trendChart) return
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['投诉', '建议'], top: 0 },
    xAxis: { type: 'category', data: data.map(d => d.date?.substring(5, 10)) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '投诉', type: 'line', data: data.map(d => d.complaint), smooth: true, itemStyle: { color: '#f56c6c' }, areaStyle: { color: 'rgba(245,108,108,0.15)' } },
      { name: '建议', type: 'line', data: data.map(d => d.suggestion), smooth: true, itemStyle: { color: '#e6a23c' }, areaStyle: { color: 'rgba(230,162,60,0.15)' } },
    ],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  })
}

function renderStatusChart(data) {
  if (!statusChart) return
  const sMap = { pending: '待处理', processing: '处理中', resolved: '已解决', rejected: '已驳回' }
  const colors = { pending: '#909399', processing: '#409eff', resolved: '#67c23a', rejected: '#f56c6c' }
  statusChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      data: data.map(d => ({ name: sMap[d.status] || d.status, value: d.count, itemStyle: { color: colors[d.status] || '#909399' } })),
      label: { show: true, formatter: '{b}: {c}' },
    }]
  })
}

// ===== 操作（兼容演示 / 真实数据） =====
function openReply(row) {
  replyItem.value = row
  replyForm.status = row.status === 'pending' ? 'processing' : row.status
  replyForm.admin_reply = row.admin_reply || ''
  replyVisible.value = true
}

async function submitReply() {
  replyLoading.value = true
  try {
    if (useMockData.value) {
      // 演示模式：本地更新
      const item = mockList.value.find(i => i.id === replyItem.value.id)
      if (item) {
        item.status = replyForm.status
        item.admin_reply = replyForm.admin_reply
      }
      ElMessage.success('回复成功（演示模式）')
    } else {
      await adminApi.updateComplaint(replyItem.value.id, replyForm)
      ElMessage.success('回复成功')
    }
    replyVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    replyLoading.value = false
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确认删除该记录？', '提示', { type: 'warning' })
    if (useMockData.value) {
      const idx = mockList.value.findIndex(i => i.id === id)
      if (idx !== -1) mockList.value.splice(idx, 1)
      ElMessage.success('已删除（演示模式）')
    } else {
      await adminApi.deleteComplaint(id)
      ElMessage.success('已删除')
    }
    loadData()
  } catch (e) {
    if (e !== 'cancel' && e?.toString() !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    }
  }
}

function handleResize() {
  typeChart?.resize()
  catChart?.resize()
  trendChart?.resize()
  statusChart?.resize()
}

onMounted(async () => {
  await nextTick()
  typeChart = echarts.init(typeChartEl.value)
  catChart = echarts.init(catChartEl.value)
  trendChart = echarts.init(trendChartEl.value)
  statusChart = echarts.init(statusChartEl.value)
  window.addEventListener('resize', handleResize)
  // 默认加载演示数据
  loadMockData()
})

onActivated(() => { nextTick(handleResize) })
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  typeChart?.dispose(); catChart?.dispose(); trendChart?.dispose(); statusChart?.dispose()
})
</script>

<style scoped>
.complaints-page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { font-size: 13px; color: #888; margin: 4px 0 0; }
.header-actions { display: flex; gap: 10px; align-items: center; }
.stat-row { margin-bottom: 0; }
.stat-card {
  background: #fff; border-radius: 8px; padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.stat-value { font-size: 28px; font-weight: 700; color: #303133; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
}

@media (max-width: 768px) {
  .complaints-page .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .complaints-page .header-actions { align-self: flex-start; }
  .stat-row { margin-bottom: 10px; }
  .stat-card { padding: 12px; }
  .stat-card .stat-value { font-size: 20px; }
  .stat-card .stat-label { font-size: 11px; }
  .reply-input { width: 100% !important; }
}
</style>
