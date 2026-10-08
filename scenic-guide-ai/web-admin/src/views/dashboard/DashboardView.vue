<template>
  <div class="dashboard-page">
    <!-- 页面标题 + 数据模式切换 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">📊 数据大屏</h2>
        <p class="page-subtitle">景区运营核心指标一览</p>
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

    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.key">
        <div class="stat-card" :style="{ borderTop: `3px solid ${stat.color}` }">
          <div class="stat-icon" :style="{ background: stat.color + '20', color: stat.color }">
            <el-icon :size="28"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value" :style="{ color: stat.color }">
              {{ stat.hasData ? stat.value.toLocaleString() : '--' }}{{ stat.suffix }}
            </div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区：全部从最近对话记录计算 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>🔥 热门问题TOP5</span>
          </template>
          <div class="hot-questions" v-if="hotQuestions.length > 0">
            <div v-for="(q, i) in hotQuestions" :key="i" class="hot-item">
              <span class="rank" :class="i < 3 ? 'top3' : ''">{{ i + 1 }}</span>
              <span class="question">{{ q.keyword || q.question }}</span>
              <el-progress
                :percentage="hotQuestions[0]?.count ? Math.round(q.count / hotQuestions[0].count * 100) : 0"
                :color="rankColors[i]"
                :show-text="false"
                class="q-progress"
              />
              <span class="count">{{ q.count }}</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <el-empty description="暂无热门问题数据" :image-size="60" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>😊 情感分析分布</span>
          </template>
          <div ref="sentimentChartEl" class="chart-container" style="height:220px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>📍 景点热度排行</span>
          </template>
          <div ref="spotChartEl" class="chart-container" style="height:220px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>⏰ 分时访问分布</span>
          </template>
          <div ref="hourChartEl" class="chart-container" style="height:220px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近对话记录 -->
    <el-card class="recent-card">
      <template #header>
        <div class="card-header">
          <span>💬 最近对话记录</span>
          <el-input
            v-model="chatKeyword"
            placeholder="搜索游客问题..."
            clearable
            style="width:240px"
            size="small"
            @keyup.enter="onChatSearch"
            @clear="onChatSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </template>
      <el-table :data="recentChats" size="small" stripe style="width:100%" v-loading="chatLoading">
        <el-table-column prop="time" label="时间" width="160" />
        <el-table-column prop="user_query" label="游客问题" />
        <el-table-column prop="answer_preview" label="AI回答摘要" />
        <el-table-column prop="sentiment" label="情感" width="80">
          <template #default="{ row }">
            <el-tag :type="sentimentType(row.sentiment)" size="small">{{ row.sentiment }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="80">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="响应时长" width="90">
          <template #default="{ row }">{{ row.duration }}ms</template>
        </el-table-column>
      </el-table>
      <div v-if="recentChats.length === 0 && !chatLoading" class="empty-state">
        <el-empty description="暂无对话记录" :image-size="60" />
      </div>
      <div v-if="chatTotal > chatPageSize" class="chat-pagination">
        <el-pagination
          v-model:current-page="chatPage"
          :page-size="chatPageSize"
          :total="chatTotal"
          layout="total, prev, pager, next"
          background
          @current-change="onChatPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, onDeactivated, onBeforeUnmount, computed } from 'vue'

import * as echarts from 'echarts'
import { Search } from '@element-plus/icons-vue'
import { adminApi } from '@/api'
import { ElMessage } from 'element-plus'

const sentimentChartEl = ref(null)
const spotChartEl = ref(null)
const hourChartEl = ref(null)
const chatLoading = ref(false)
const chatPage = ref(1)
const chatPageSize = 10
const chatTotal = ref(0)
const chatKeyword = ref('')

let sentimentChart, spotChart, hourChart

const rankColors = ['#f56c6c', '#e6a23c', '#67c23a', '#409eff', '#909399']
const recentChats = ref([])

// Mock/Real 数据切换
const useMockData = ref(true)

function sentimentType(s) {
  const map = { 'positive': 'success', 'neutral': 'info', 'negative': 'danger', '积极': 'success', '中性': 'info', '消极': 'danger' }
  return map[s] || 'info'
}

// ===== 演示数据 =====
const mockRecentChats = [
  { time: '2026-07-04 14:23:15', user_query: '灵山大佛有多高？', answer_preview: '灵山大佛通高88米，是中国第二高的巨型佛像...', sentiment: '积极', source: '大屏', duration: 820 },
  { time: '2026-07-04 14:18:02', user_query: '九龙灌浴表演几点开始？', answer_preview: '九龙灌浴表演每天上午10:00和下午14:00各一场...', sentiment: '积极', source: 'APP', duration: 650 },
  { time: '2026-07-04 14:05:33', user_query: '门票多少钱？', answer_preview: '灵山胜境成人票210元，学生票105元...', sentiment: '中性', source: '大屏', duration: 420 },
  { time: '2026-07-04 13:52:11', user_query: '附近有停车场吗？', answer_preview: '景区设有P1-P3共三个停车场，总计2000个车位...', sentiment: '积极', source: 'APP', duration: 380 },
  { time: '2026-07-04 13:30:45', user_query: '推荐一下游览路线', answer_preview: '推荐经典路线：大照壁→五明桥→佛足坛→五智门→九龙灌浴→灵山大佛→梵宫，全程约3小时...', sentiment: '积极', source: '大屏', duration: 920 },
  { time: '2026-07-04 12:58:20', user_query: '梵宫里面有什么？', answer_preview: '灵山梵宫被誉为"东方卢浮宫"，内有木雕、琉璃、油画等艺术珍品...', sentiment: '积极', source: 'APP', duration: 750 },
  { time: '2026-07-04 12:35:10', user_query: '能带宠物吗？', answer_preview: '抱歉，景区内不允许携带宠物入内，但提供宠物寄存服务...', sentiment: '中性', source: '大屏', duration: 310 },
  { time: '2026-07-04 11:50:08', user_query: '这个景点讲解太啰嗦了', answer_preview: '感谢您的反馈，您可以随时说"跳过"来中断当前讲解...', sentiment: '消极', source: 'APP', duration: 560 },
  { time: '2026-07-04 11:22:40', user_query: '五智门有什么寓意？', answer_preview: '五智门代表佛教五种智慧：法界体性智、大圆镜智、平等性智、妙观察智、成所作智...', sentiment: '积极', source: '大屏', duration: 1100 },
  { time: '2026-07-04 10:45:15', user_query: '洗手间在哪', answer_preview: '景区内设有多个洗手间，分别在入口广场、九龙灌浴旁、梵宫一层...', sentiment: '中性', source: 'APP', duration: 290 },
]

const mockStats = [
  { key: 'total', label: '今日服务人次', value: 128, suffix: '', color: '#409eff', icon: 'User', hasData: true },
  { key: 'questions', label: '会话总数', value: 847, suffix: '', color: '#67c23a', icon: 'ChatDotRound', hasData: true },
  { key: 'satisfaction', label: '综合满意度', value: 94, suffix: '%', color: '#e6a23c', icon: 'Star', hasData: true },
  { key: 'response', label: '平均响应时间', value: 620, suffix: 'ms', color: '#f56c6c', icon: 'Timer', hasData: true }
]

const mockHotQuestions = [
  { keyword: '灵山大佛', count: 86 },
  { keyword: '九龙灌浴', count: 64 },
  { keyword: '门票价格', count: 52 },
  { keyword: '游览路线', count: 43 },
  { keyword: '停车场', count: 31 }
]

// ===== 真实数据计算属性 =====
const stats = ref(mockStats)
const hotQuestions = ref(mockHotQuestions)

// 真实数据计算（仅当 useMockData=false 时使用）
const realStats = computed(() => {
  const msgs = recentChats.value
  if (msgs.length === 0) {
    return [
      { key: 'total', label: '今日服务人次', value: 0, suffix: '', color: '#409eff', icon: 'User', hasData: false },
      { key: 'questions', label: '会话总数', value: 0, suffix: '', color: '#67c23a', icon: 'ChatDotRound', hasData: false },
      { key: 'satisfaction', label: '综合满意度', value: 0, suffix: '%', color: '#e6a23c', icon: 'Star', hasData: false },
      { key: 'response', label: '平均响应时间', value: 0, suffix: 'ms', color: '#f56c6c', icon: 'Timer', hasData: false }
    ]
  }

  const today = new Date().toLocaleDateString('zh-CN')
  const todayMsgs = msgs.filter(m => {
    if (!m.time) return false
    return new Date(m.time).toLocaleDateString('zh-CN') === today
  })

  const sentimentCounts = { positive: 0, neutral: 0, negative: 0 }
  const sentimentMap = { '积极': 'positive', '中性': 'neutral', '消极': 'negative' }
  msgs.forEach(m => {
    const s = m.sentiment || ''
    const key = sentimentMap[s] || s || 'neutral'
    if (sentimentCounts.hasOwnProperty(key)) sentimentCounts[key]++
  })
  const totalSentiment = sentimentCounts.positive + sentimentCounts.neutral + sentimentCounts.negative
  const satisfaction = totalSentiment > 0 ? Math.round(sentimentCounts.positive / totalSentiment * 100) : 0

  const durations = msgs.filter(m => m.duration != null).map(m => m.duration)
  const avgDuration = durations.length > 0 ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length) : 0

  return [
    { key: 'total', label: '今日服务人次', value: todayMsgs.length, suffix: '', color: '#409eff', icon: 'User', hasData: todayMsgs.length > 0 },
    { key: 'questions', label: '会话总数', value: msgs.length, suffix: '', color: '#67c23a', icon: 'ChatDotRound', hasData: msgs.length > 0 },
    { key: 'satisfaction', label: '综合满意度', value: satisfaction, suffix: '%', color: '#e6a23c', icon: 'Star', hasData: totalSentiment > 0 },
    { key: 'response', label: '平均响应时间', value: avgDuration, suffix: 'ms', color: '#f56c6c', icon: 'Timer', hasData: durations.length > 0 }
  ]
})

const realHotQuestions = computed(() => {
  const msgs = recentChats.value
  if (msgs.length === 0) return []

  const stopWords = new Set([
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你',
    '会', '着', '没有', '看', '好', '自己', '这', '吗', '呢', '啊', '吧', '哦', '嗯', '什么', '怎么', '哪', '哪里', '哪边',
    '可以', '能', '能够', '请问', '一下', '这个', '那个', '哪个', '哪些', '想', '知道', '告诉', '介绍一下', '介绍',
    '有没有', '是不是', '好不好', '能不能'
  ])

  const keywordCounts = {}
  msgs.forEach(m => {
    const text = (m.user_query || '').replace(/[，。！？、；：""''（）\(\)\[\]\s]/g, '')
    for (let len = 2; len <= 4; len++) {
      for (let i = 0; i <= text.length - len; i++) {
        const gram = text.substring(i, i + len)
        if (!stopWords.has(gram) && gram.length >= 2) {
          keywordCounts[gram] = (keywordCounts[gram] || 0) + 1
        }
      }
    }
  })

  return Object.entries(keywordCounts)
    .filter(([, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([keyword, count]) => ({ keyword, count }))
})

const emotionData = computed(() => {
  const msgs = recentChats.value
  const result = { positive: 0, neutral: 0, negative: 0 }
  const sentimentMap = { '积极': 'positive', '中性': 'neutral', '消极': 'negative' }
  msgs.forEach(m => {
    const s = m.sentiment || ''
    const key = sentimentMap[s] || s || 'neutral'
    if (result.hasOwnProperty(key)) result[key]++
  })
  return result
})

const spotNames = ['灵山大照壁', '五明桥', '佛足坛', '五智门', '菩提大道', '九龙灌浴', '降魔浮雕', '阿育王柱', '百子戏弥勒', '祥符禅寺', '灵山大佛', '灵山梵宫']

const spotPopularity = computed(() => {
  const msgs = recentChats.value
  const spotCounts = {}
  spotNames.forEach(name => spotCounts[name] = 0)

  msgs.forEach(msg => {
    const content = (msg.user_query || '').toLowerCase()
    spotNames.forEach(name => {
      if (content.includes(name) || content.includes(name.replace('区', ''))) {
        spotCounts[name] = (spotCounts[name] || 0) + 1
      }
    })
  })

  return Object.entries(spotCounts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name, count }))
})

const hourData = computed(() => {
  const msgs = recentChats.value
  const hourCounts = {}
  for (let h = 8; h <= 18; h++) hourCounts[h] = 0

  msgs.forEach(m => {
    if (!m.time) return
    const hour = new Date(m.time).getHours()
    if (hour >= 8 && hour <= 18) hourCounts[hour]++
  })

  const hours = Object.keys(hourCounts).map(Number).sort((a, b) => a - b)
  return {
    hours: hours.map(h => `${h}:00`),
    data: hours.map(h => hourCounts[h])
  }
})

// ===== 真实数据获取 =====
async function fetchRecentChats() {
  chatLoading.value = true
  try {
    const params = { page: chatPage.value, page_size: chatPageSize }
    if (chatKeyword.value.trim()) {
      params.keyword = chatKeyword.value.trim()
    }
    const res = await adminApi.getRecentMessages(params)
    const resData = res?.data || res || {}
    recentChats.value = resData.messages || []
    chatTotal.value = resData.total || 0
  } catch (error) {
    console.error('获取对话记录失败:', error)
    ElMessage.error('获取对话记录失败: ' + (error.response?.data?.detail || error.message || '网络错误'))
    recentChats.value = []
  } finally {
    chatLoading.value = false
  }
}

function onChatPageChange(p) {
  chatPage.value = p
  if (useMockData.value) {
    // 演示数据模式：前端重新分页
    loadMockData()
  } else {
    fetchRecentChats()
  }
}

function onChatSearch() {
  chatPage.value = 1
  if (useMockData.value) {
    loadMockData()
  } else {
    fetchRecentChats()
  }
}

// ===== 数据加载调度 =====
function loadData() {
  if (useMockData.value) {
    loadMockData()
  } else {
    loadRealData()
  }
}

function loadMockData() {
  // 关键词过滤
  let filtered = mockRecentChats
  if (chatKeyword.value.trim()) {
    const kw = chatKeyword.value.trim().toLowerCase()
    filtered = mockRecentChats.filter(m =>
      m.user_query.toLowerCase().includes(kw) || m.answer_preview.toLowerCase().includes(kw)
    )
  }
  chatTotal.value = filtered.length
  const start = (chatPage.value - 1) * chatPageSize
  recentChats.value = filtered.slice(start, start + chatPageSize)
  stats.value = mockStats
  hotQuestions.value = mockHotQuestions
  chatLoading.value = false

  // 用演示数据更新图表
  updateSentimentChartMock()
  updateSpotChartMock()
  updateHourChartMock()
}

async function loadRealData() {
  await fetchRecentChats()
  stats.value = realStats.value
  hotQuestions.value = realHotQuestions.value
  updateAllCharts()
}

// ===== ECharts 初始化与更新 =====

function initSentimentChart() {
  sentimentChart = echarts.init(sentimentChartEl.value)
}

function updateSentimentChartMock() {
  sentimentChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, left: 'center', icon: 'circle', itemWidth: 10 },
    series: [{
      type: 'pie', radius: ['50%', '70%'],
      center: ['50%', '42%'],
      data: [
        { value: 68, name: '积极', itemStyle: { color: '#67c23a' } },
        { value: 24, name: '中性', itemStyle: { color: '#e6a23c' } },
        { value: 8, name: '消极', itemStyle: { color: '#f56c6c' } }
      ],
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } }
    }]
  })
}

function updateSentimentChartReal() {
  const { positive, neutral, negative } = emotionData.value
  const total = positive + neutral + negative

  if (total === 0) {
    sentimentChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } },
      series: []
    })
    return
  }

  sentimentChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, left: 'center', icon: 'circle', itemWidth: 10 },
    series: [{
      type: 'pie', radius: ['50%', '70%'],
      center: ['50%', '42%'],
      data: [
        { value: positive, name: '积极', itemStyle: { color: '#67c23a' } },
        { value: neutral, name: '中性', itemStyle: { color: '#e6a23c' } },
        { value: negative, name: '消极', itemStyle: { color: '#f56c6c' } }
      ],
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } }
    }]
  })
}

function initSpotChart() {
  spotChart = echarts.init(spotChartEl.value)
}

function updateSpotChartMock() {
  const spots = [
    { name: '灵山大佛', count: 86 },
    { name: '九龙灌浴', count: 64 },
    { name: '灵山梵宫', count: 48 },
    { name: '五智门', count: 35 },
    { name: '祥符禅寺', count: 28 }
  ]
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']

  spotChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 70, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    yAxis: {
      type: 'category',
      data: spots.map(s => s.name),
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#303133', fontSize: 12, fontWeight: 500 }
    },
    series: [{
      type: 'bar', barWidth: '50%',
      data: spots.map((s, i) => ({ value: s.count, itemStyle: { color: colors[i] || '#409eff', borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: 'right', fontSize: 12, color: '#303133' }
    }]
  })
}

function updateSpotChartReal() {
  const spots = spotPopularity.value
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']

  if (spots.length === 0) {
    spotChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } },
      series: []
    })
    return
  }

  spotChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 70, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    yAxis: {
      type: 'category',
      data: spots.map(s => s.name),
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#303133', fontSize: 12, fontWeight: 500 }
    },
    series: [{
      type: 'bar', barWidth: '50%',
      data: spots.map((s, i) => ({ value: s.count, itemStyle: { color: colors[i] || '#409eff', borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: 'right', fontSize: 12, color: '#303133' }
    }]
  })
}

function initHourChart() {
  hourChart = echarts.init(hourChartEl.value)
}

function updateHourChartMock() {
  const hours = ['8:00', '9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']
  const data = [12, 38, 72, 65, 30, 25, 68, 55, 42, 28, 15]

  hourChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 30, right: 10, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: hours, axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [{
      data,
      type: 'bar',
      barWidth: '60%',
      itemStyle: { color: '#409eff', borderRadius: [2, 2, 0, 0] }
    }]
  })
}

function updateHourChartReal() {
  const hours = hourData.value.hours
  const data = hourData.value.data

  if (data.length === 0 || data.every(v => v === 0)) {
    hourChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } },
      series: []
    })
    return
  }

  hourChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 30, right: 10, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: hours, axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [{
      data,
      type: 'bar',
      barWidth: '60%',
      itemStyle: { color: '#409eff', borderRadius: [2, 2, 0, 0] }
    }]
  })
}

// 更新所有图表（真实数据模式）
function updateAllCharts() {
  updateSentimentChartReal()
  updateSpotChartReal()
  updateHourChartReal()
}

onMounted(async () => {
  initSentimentChart()
  initSpotChart()
  initHourChart()

  // 默认加载演示数据
  loadMockData()

  window.addEventListener('resize', handleResize)
})

onActivated(() => {
  // keep-alive 重新激活：重新绑定 resize 监听（onDeactivated 会移除），并刷新图表尺寸
  window.addEventListener('resize', handleResize)
  sentimentChart?.resize()
  spotChart?.resize()
  hourChart?.resize()
})

onDeactivated(() => {
  window.removeEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  sentimentChart?.dispose()
  spotChart?.dispose()
  hourChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  sentimentChart?.resize()
  spotChart?.resize()
  hourChart?.resize()
}
</script>

<style scoped>
.dashboard-page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; margin: 0; }
.page-subtitle { font-size: 13px; color: #888; margin: 4px 0 0; }
.header-actions { display: flex; gap: 10px; align-items: center; }
.stat-row { margin-bottom: 16px; }
.stat-card {
  background: #fff; border-radius: 8px; padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  display: flex; align-items: center; gap: 16px;
  transition: box-shadow 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.stat-icon {
  width: 56px; height: 56px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: #888; margin-top: 4px; }
.stat-change { font-size: 12px; margin-top: 4px; display: flex; align-items: center; gap: 2px; }
.up { color: #f56c6c; }
.down { color: #67c23a; }

.chart-row { margin-bottom: 16px; }
.chart-card { border-radius: 8px; }
.card-header {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 15px; font-weight: 500;
}
.chart-container { width: 100%; }

.hot-questions { display: flex; flex-direction: column; gap: 12px; }
.hot-item { display: flex; align-items: center; gap: 10px; }
.rank {
  width: 20px; height: 20px; border-radius: 4px;
  background: #f0f0f0; color: #888;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}
.rank.top3 { background: linear-gradient(135deg, #f56c6c, #e6a23c); color: #fff; }
.question { flex: 1; font-size: 13px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.q-progress { width: 60px; flex-shrink: 0; }
.count { font-size: 13px; color: #888; width: 36px; text-align: right; flex-shrink: 0; }

.recent-card { border-radius: 8px; }

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
}
</style>
