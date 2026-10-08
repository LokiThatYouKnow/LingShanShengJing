<template>
  <div class="analytics-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">📊 游客数据分析</h2>
        <p class="page-subtitle">深度洞察游客行为、情感趋势与满意度报告</p>
      </div>
      <div class="header-actions">
        <el-switch
          v-model="useMockData"
          active-text="演示数据"
          inactive-text="真实数据"
          @change="loadData"
          style="margin-right: 12px"
        />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="default"
          @change="loadData"
        />
        <el-dropdown @command="exportReport">
          <el-button type="primary" :icon="Download">
            导出报告 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="doc">
                <el-icon><Document /></el-icon> Word 文档 (.doc)
              </el-dropdown-item>
              <el-dropdown-item command="xls">
                <el-icon><DataAnalysis /></el-icon> Excel 表格 (.xls)
              </el-dropdown-item>
              <el-dropdown-item command="csv">
                <el-icon><List /></el-icon> CSV 数据 (.csv)
              </el-dropdown-item>
              <el-dropdown-item command="txt">
                <el-icon><Tickets /></el-icon> 纯文本 (.txt)
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 核心指标 -->
    <el-row :gutter="16" class="metrics-row">
      <el-col :span="6" v-for="m in metrics" :key="m.key">
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-label">{{ m.label }}</span>
            <el-tag :type="m.trendType" size="small">{{ m.trend }}</el-tag>
          </div>
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-bar">
            <el-progress :percentage="m.percent" :color="m.color" :show-text="false" :stroke-width="6" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 情感趋势 + 用户来源 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>😊 情感趋势分析（近14天）</span>
              <el-checkbox-group v-model="sentimentLines" size="small">
                <el-checkbox-button label="positive">积极</el-checkbox-button>
                <el-checkbox-button label="neutral">中性</el-checkbox-button>
                <el-checkbox-button label="negative">消极</el-checkbox-button>
              </el-checkbox-group>
            </div>
          </template>
          <div ref="sentimentTrendEl" style="height:260px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>📱 访问来源分布</span></template>
          <div ref="sourceChartEl" style="height:260px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 问题分类词云 + 响应延迟 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="12">
        <el-card>
          <template #header><span>🏷️ 问题主题分类</span></template>
          <div ref="categoryChartEl" style="height:240px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>⚡ 响应延迟分布</span></template>
          <div ref="latencyChartEl" style="height:240px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 满意度评分 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="8">
        <el-card>
          <template #header><span>⭐ 满意度评分分布</span></template>
          <div ref="ratingChartEl" style="height:220px"></div>
          <div class="rating-summary">
            <div class="avg-rating">
              <span class="rating-num">4.8</span>
              <div class="stars">★★★★★</div>
              <span class="rating-total">共 1,284 条评价</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>💬 游客评价摘要</span>
              <el-tabs v-model="reviewTab" class="review-tabs">
                <el-tab-pane label="好评" name="positive" />
                <el-tab-pane label="中评" name="neutral" />
                <el-tab-pane label="差评" name="negative" />
              </el-tabs>
            </div>
          </template>
          <div class="review-list">
            <div v-for="review in currentReviews" :key="review.id" class="review-item">
              <div class="review-header">
                <div class="review-user">
                  <el-avatar :size="32" :style="{ background: review.color }">{{ review.user[0] }}</el-avatar>
                  <div>
                    <div class="review-username">{{ review.user }}</div>
                    <div class="review-time">{{ review.time }}</div>
                  </div>
                </div>
                <div class="review-stars">{{ '★'.repeat(review.rating) }}{{ '☆'.repeat(5 - review.rating) }}</div>
              </div>
              <p class="review-text">{{ review.content }}</p>
              <div class="review-tags">
                <el-tag v-for="tag in review.tags" :key="tag" size="small" type="info" round>{{ tag }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细对话记录 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📝 完整对话记录</span>
          <div class="filter-bar">
            <el-select v-model="filterSentiment" placeholder="情感筛选" clearable size="small" style="width:120px" @change="onChatLogFilterChange">
              <el-option label="积极" value="positive" />
              <el-option label="中性" value="neutral" />
              <el-option label="消极" value="negative" />
            </el-select>
            <el-select v-model="filterSource" placeholder="来源筛选" clearable size="small" style="width:120px" @change="onChatLogFilterChange">
              <el-option label="APP" value="app" />
              <el-option label="大屏" value="kiosk" />
            </el-select>
            <el-input v-model="filterKeyword" placeholder="关键词搜索" clearable size="small" style="width:180px" @keyup.enter="onChatLogFilterChange" @clear="onChatLogFilterChange" />
          </div>
        </div>
      </template>
      <el-table :data="chatLogs" stripe size="small" v-loading="chatLogLoading">
        <el-table-column prop="created_at" label="时间" width="150" />
        <el-table-column prop="user_query" label="用户问题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ai_answer" label="AI回答" min-width="250" show-overflow-tooltip />
        <el-table-column prop="sentiment" label="情感" width="80">
          <template #default="{ row }">
            <el-tag :type="sentimentTagType(row.sentiment)" size="small">{{ sentimentMap[row.sentiment] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="80">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time_ms" label="响应(ms)" width="100" align="center" />
        <el-table-column prop="rag_used" label="RAG" width="70" align="center">
          <template #default="{ row }">
            <el-icon :color="row.rag_used ? '#67c23a' : '#aaa'"><Check v-if="row.rag_used" /><Close v-else /></el-icon>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="chatLogPage"
        :page-size="chatLogPageSize"
        :total="chatLogTotal"
        layout="total, prev, pager, next"
        background
        class="pagination"
        style="margin-top:12px"
        @current-change="fetchChatLogs"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { Download, Check, Close, ArrowDown, Document, DataAnalysis, List, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { adminApi } from '@/api'

const dateRange = ref([])
const reviewTab = ref('positive')
const filterSentiment = ref('')
const filterSource = ref('')
const filterKeyword = ref('')
const logPage = ref(1)
const sentimentLines = ref(['positive', 'neutral', 'negative'])

// Mock/Real 数据切换
const useMockData = ref(true)

const sentimentTrendEl = ref(null)
const sourceChartEl = ref(null)
const categoryChartEl = ref(null)
const latencyChartEl = ref(null)
const ratingChartEl = ref(null)

let charts = {}

const metrics = ref([
  { key: 'sessions', label: '总服务人次', value: '12,847', percent: 85, color: '#409eff', trend: '↑12%', trendType: 'danger' },
  { key: 'satisfaction', label: '综合满意度', value: '96.2%', percent: 96, color: '#67c23a', trend: '↑1.4%', trendType: 'success' },
  { key: 'response', label: '平均响应时间', value: '1.8s', percent: 60, color: '#e6a23c', trend: '↓0.2s', trendType: 'success' },
  { key: 'accuracy', label: 'RAG问答准确率', value: '94.3%', percent: 94, color: '#f56c6c', trend: '↑0.8%', trendType: 'success' }
])

const sentimentMap = { positive: '积极', neutral: '中性', negative: '消极' }
function sentimentTagType(s) {
  return { positive: 'success', neutral: 'info', negative: 'danger' }[s] || 'info'
}

const reviews = {
  positive: [
    { id: 1, user: '游客A', color: '#409eff', rating: 5, time: '2026-04-01 14:23', content: '数字人讲解非常专业，语音清晰，回答问题准确，比人工讲解还详细！', tags: ['专业', '准确', '清晰'] },
    { id: 2, user: '游客B', color: '#67c23a', rating: 5, time: '2026-04-01 11:45', content: 'APP体验很好，GPS定位触发讲解太方便了，不用担心错过精彩看点。', tags: ['便捷', 'GPS定位', '体验好'] },
    { id: 3, user: '游客C', color: '#e6a23c', rating: 4, time: '2026-03-31 16:08', content: '语音识别很准，问了很多问题都能正确回答，推荐路线也很合理。', tags: ['语音准', '路线好'] }
  ],
  neutral: [
    { id: 4, user: '游客D', color: '#909399', rating: 3, time: '2026-04-01 10:22', content: '整体可以，有时候回答比较慢，不过内容还是挺准确的。', tags: ['稍慢'] },
    { id: 5, user: '游客E', color: '#9b59b6', rating: 3, time: '2026-03-31 14:55', content: '功能很全，但界面操作不太熟练，上手需要一点时间。', tags: ['功能全'] }
  ],
  negative: [
    { id: 6, user: '游客F', color: '#f56c6c', rating: 2, time: '2026-03-30 15:33', content: '遇到网络不好时回答会卡顿，希望能优化离线模式。', tags: ['网络问题'] }
  ]
}
const currentReviews = computed(() => reviews[reviewTab.value] || [])

const chatLogs = ref([])
const chatLogTotal = ref(0)
const chatLogPage = ref(1)
const chatLogPageSize = 10
const chatLogLoading = ref(false)

const dates14 = Array.from({ length: 14 }, (_, i) => {
  const d = new Date('2026-04-01')
  d.setDate(d.getDate() - 13 + i)
  return `${d.getMonth()+1}/${d.getDate()}`
})

function initCharts() {
  // 切换数据模式会重复调用本函数，先销毁旧实例避免重复 init 导致的内存泄漏与渲染告警
  Object.keys(charts).forEach(k => {
    if (charts[k]) { charts[k].dispose(); charts[k] = null }
  })
  // 情感趋势
  charts.sentiment = echarts.init(sentimentTrendEl.value)
  charts.sentiment.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: ['积极', '中性', '消极'] },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates14 },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '积极', type: 'line', data: [62,65,68,64,70,72,68,71,74,70,68,73,70,68], smooth: true, lineStyle: { color: '#67c23a' }, itemStyle: { color: '#67c23a' } },
      { name: '中性', type: 'line', data: [28,25,24,26,22,20,24,22,19,22,24,20,22,24], smooth: true, lineStyle: { color: '#e6a23c' }, itemStyle: { color: '#e6a23c' } },
      { name: '消极', type: 'line', data: [10,10,8,10,8,8,8,7,7,8,8,7,8,8], smooth: true, lineStyle: { color: '#f56c6c' }, itemStyle: { color: '#f56c6c' } }
    ]
  })

  // 来源分布
  charts.source = echarts.init(sourceChartEl.value)
  charts.source.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 10 },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '44%'],
      data: [
        { value: 68, name: '手机APP', itemStyle: { color: '#409eff' } },
        { value: 22, name: '景区大屏', itemStyle: { color: '#67c23a' } },
        { value: 10, name: 'Web端', itemStyle: { color: '#e6a23c' } }
      ],
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14 } }
    }]
  })

  // 问题分类
  charts.category = echarts.init(categoryChartEl.value)
  charts.category.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: '65%',
      data: [
        { value: 35, name: '景点介绍' },
        { value: 22, name: '路线导览' },
        { value: 18, name: '交通停车' },
        { value: 12, name: '餐饮服务' },
        { value: 8, name: '票价优惠' },
        { value: 5, name: '其他' }
      ],
      itemStyle: { borderRadius: 5 }
    }]
  })

  // 响应延迟
  charts.latency = echarts.init(latencyChartEl.value)
  charts.latency.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: ['<0.5s', '0.5-1s', '1-1.5s', '1.5-2s', '2-3s', '>3s'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar', barWidth: '50%',
      data: [312, 456, 298, 143, 62, 13],
      itemStyle: {
        color: function(p) {
          return ['#67c23a','#67c23a','#e6a23c','#e6a23c','#f56c6c','#f56c6c'][p.dataIndex]
        },
        borderRadius: [4, 4, 0, 0]
      },
      label: { show: true, position: 'top', fontSize: 11, color: '#666' }
    }]
  })

  // 满意度
  charts.rating = echarts.init(ratingChartEl.value)
  charts.rating.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: ['1星', '2星', '3星', '4星', '5星'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar', barWidth: '50%',
      data: [8, 15, 68, 215, 978],
      itemStyle: {
        color: function(p) {
          return ['#f56c6c','#e6a23c','#e6a23c','#67c23a','#67c23a'][p.dataIndex]
        },
        borderRadius: [4, 4, 0, 0]
      }
    }]
  })
}

function loadData() {
  if (useMockData.value) {
    // 恢复演示数据的核心指标
    metrics.value = [
      { key: 'sessions', label: '总服务人次', value: '12,847', percent: 85, color: '#409eff', trend: '↑12%', trendType: 'danger' },
      { key: 'satisfaction', label: '综合满意度', value: '96.2%', percent: 96, color: '#67c23a', trend: '↑1.4%', trendType: 'success' },
      { key: 'response', label: '平均响应时间', value: '1.8s', percent: 60, color: '#e6a23c', trend: '↓0.2s', trendType: 'success' },
      { key: 'accuracy', label: 'RAG问答准确率', value: '94.3%', percent: 94, color: '#f56c6c', trend: '↑0.8%', trendType: 'success' }
    ]
    initCharts()
    return
  }
  loadRealData()
}

async function loadRealData() {
  try {
    const [overview, emotionTrend, hotQs, dailyStats, hourlyDist, recentMsgs] = await Promise.all([
      adminApi.getDashboard({ days: 14 }),
      adminApi.getEmotionTrend({ days: 14 }),
      adminApi.getHotQuestions({ limit: 10 }),
      adminApi.getDailyStats({ days: 14 }),
      adminApi.getHourlyDistribution({ days: 14 }),
      adminApi.getRecentMessages({ limit: 50 })
    ])

    const overviewData = overview?.data || overview || {}
    const emotionDataRaw = emotionTrend?.data || emotionTrend || {}
    const hotQsData = hotQs?.data || hotQs || {}
    const msgsData = recentMsgs?.data || recentMsgs || {}

    // 更新核心指标
    const todayService = overviewData.todayServiceCount || overviewData.today_service_count || 0
    const satisfaction = overviewData.avgSatisfaction || overviewData.avg_satisfaction
      ? Math.round((overviewData.avgSatisfaction || overviewData.avg_satisfaction) * 20) : 0
    const avgResp = overviewData.avgResponseTime || overviewData.avg_response_time || 0

    metrics.value = [
      { key: 'sessions', label: '总服务人次', value: todayService.toLocaleString(), percent: Math.min(100, todayService), color: '#409eff', trend: '--', trendType: 'info' },
      { key: 'satisfaction', label: '综合满意度', value: satisfaction + '%', percent: satisfaction, color: '#67c23a', trend: '--', trendType: 'info' },
      { key: 'response', label: '平均响应时间', value: avgResp + 's', percent: Math.max(0, 100 - avgResp * 20), color: '#e6a23c', trend: '--', trendType: 'info' },
      { key: 'accuracy', label: 'RAG使用率', value: '--', percent: 0, color: '#f56c6c', trend: '--', trendType: 'info' }
    ]

    // 更新来源分布饼图
    const platformDist = overviewData.platformDistribution || overviewData.platform_distribution || {}
    const platformData = Object.entries(platformDist).map(([k, v]) => ({
      value: v,
      name: k === 'kiosk' ? '景区大屏' : k === 'app' ? '手机APP' : k === 'web' ? 'Web端' : k
    }))
    if (platformData.length > 0) {
      charts.source?.setOption({
        series: [{ data: platformData }]
      })
    }

    // 更新问题分类（用热门关键词数据）
    const kwStats = hotQsData.keywordStats || hotQsData.keyword_stats || []
    if (kwStats.length > 0) {
      charts.category?.setOption({
        series: [{ data: kwStats.slice(0, 6).map(k => ({ value: k.count, name: k.keyword })) }]
      })
    }

    // 更新响应延迟分布
    const msgs = msgsData.messages || []
    if (msgs.length > 0) {
      const buckets = [0, 0, 0, 0, 0, 0]
      msgs.forEach(m => {
        const rt = m.response_time || m.duration / 1000 || 0
        if (rt < 0.5) buckets[0]++
        else if (rt < 1) buckets[1]++
        else if (rt < 1.5) buckets[2]++
        else if (rt < 2) buckets[3]++
        else if (rt < 3) buckets[4]++
        else buckets[5]++
      })
      charts.latency?.setOption({ series: [{ data: buckets }] })
    }

    // 更新情感趋势 — 用真实数据
    const emotionMap = emotionDataRaw?.emotion_distribution || emotionDataRaw?.emotionDistribution || {}
    const posPct = emotionMap.positive || emotionMap['积极'] || 0
    const neuPct = emotionMap.neutral || emotionMap['中性'] || 0
    const negPct = emotionMap.negative || emotionMap['消极'] || 0
    const totalPct = posPct + neuPct + negPct || 1
    if (charts.sentiment) {
      charts.sentiment.setOption({
        series: [
          { name: '积极', data: Array(14).fill(Math.round(posPct / totalPct * 100)) },
          { name: '中性', data: Array(14).fill(Math.round(neuPct / totalPct * 100)) },
          { name: '消极', data: Array(14).fill(Math.round(negPct / totalPct * 100)) }
        ]
      })
    }

    // 更新对话记录表 — 使用分页查询
    await fetchChatLogs()

  } catch (error) {
    console.error('加载真实数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

async function fetchChatLogs() {
  chatLogLoading.value = true
  try {
    const params = { page: chatLogPage.value, page_size: chatLogPageSize }
    if (filterKeyword.value.trim()) params.keyword = filterKeyword.value.trim()
    if (filterSentiment.value) params.sentiment = filterSentiment.value
    if (filterSource.value) params.source = filterSource.value
    const res = await adminApi.getRecentMessages(params)
    const resData = res?.data || res || {}
    const msgs = resData.messages || []
    chatLogs.value = msgs.map(m => ({
      created_at: m.created_at || m.time,
      user_query: m.user_query,
      ai_answer: m.ai_answer || m.answer_preview,
      sentiment: m.sentiment,
      source: m.source === 'kiosk' ? '大屏' : m.source === 'app' ? 'APP' : m.source,
      response_time_ms: m.response_time_ms || m.duration,
      rag_used: m.rag_used
    }))
    chatLogTotal.value = resData.total || 0
  } catch (e) {
    console.error('获取对话记录失败:', e)
  } finally {
    chatLogLoading.value = false
  }
}

function onChatLogFilterChange() {
  chatLogPage.value = 1
  fetchChatLogs()
}

function getReportFilename(ext) {
  const now = new Date()
  const ds = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}`
  return `游客分析报告_${ds}.${ext}`
}

function buildReportHTML() {
  const m = metrics.value
  const now = new Date().toLocaleString('zh-CN')
  const dateLabel = dateRange.value?.length === 2
    ? `${dateRange.value[0].toLocaleDateString('zh-CN')} 至 ${dateRange.value[1].toLocaleDateString('zh-CN')}`
    : '全部'
  const rows = chatLogs.value.map(r => `
    <tr>
      <td>${r.created_at || ''}</td><td>${escHtml(r.user_query || '')}</td>
      <td>${escHtml(r.ai_answer || '')}</td><td>${sentimentMap[r.sentiment] || ''}</td>
      <td>${r.source || ''}</td><td>${r.response_time_ms || ''}</td><td>${r.rag_used ? '是' : '否'}</td>
    </tr>`).join('')
  const reviewsHtml = Object.entries(reviews).map(([k, list]) => list.map(r => `
    <tr><td>${k === 'positive' ? '好评' : k === 'neutral' ? '中评' : '差评'}</td>
      <td>${r.user}</td><td>${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</td>
      <td>${escHtml(r.content)}</td></tr>`).join('')).join('')
  return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>游客数据分析报告</title>
<style>
body{font-family:'Microsoft YaHei',sans-serif;margin:40px;color:#333;line-height:1.8}
h1{text-align:center;border-bottom:2px solid #409eff;padding-bottom:12px;margin-bottom:8px}
.subtitle{text-align:center;color:#888;margin-bottom:30px}
h2{color:#409eff;border-left:4px solid #409eff;padding-left:10px;margin-top:30px}
.metrics{display:flex;gap:16px;margin-bottom:20px}
.metric{border:1px solid #e0e0e0;border-radius:8px;padding:14px 20px;flex:1;text-align:center}
.metric .val{font-size:28px;font-weight:700;color:#409eff}
.metric .label{font-size:13px;color:#888}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
th,td{border:1px solid #ddd;padding:8px 10px;text-align:left}
th{background:#f5f7fa;font-weight:600}
tr:nth-child(even){background:#fafafa}
.footer{text-align:center;color:#aaa;margin-top:30px;font-size:12px}
</style></head><body>
<h1>景区AI导览 — 游客数据分析报告</h1>
<p class="subtitle">报告生成时间：${now} | 数据范围：${dateLabel}</p>
<h2>一、核心指标概览</h2>
<div class="metrics">
  ${m.map(x => `<div class="metric"><div class="val">${x.value}</div><div class="label">${x.label}</div></div>`).join('')}
</div>
<h2>二、情感趋势分析</h2>
<p>近14天情感分布：积极 ~68%, 中性 ~24%, 消极 ~8%（基于全部对话记录）</p>
<h2>三、访问来源分布</h2>
<p>手机APP 68% | 景区大屏 22% | Web端 10%</p>
<h2>四、问题主题分类</h2>
<p>景点介绍 35% | 路线导览 22% | 交通停车 18% | 餐饮服务 12% | 票价优惠 8% | 其他 5%</p>
<h2>五、响应延迟分布</h2>
<p>&lt;0.5s: 312 | 0.5-1s: 456 | 1-1.5s: 298 | 1.5-2s: 143 | 2-3s: 62 | &gt;3s: 13</p>
<h2>六、满意度评分</h2>
<p>平均评分 4.8/5.0 | 5星 978 | 4星 215 | 3星 68 | 2星 15 | 1星 8</p>
<h2>七、游客评价摘要</h2>
<table>${reviewsHtml || '<tr><td colspan="4">暂无数据</td></tr>'}</table>
<h2>八、对话记录</h2>
<table><tr><th>时间</th><th>用户问题</th><th>AI回答</th><th>情感</th><th>来源</th><th>响应(ms)</th><th>RAG</th></tr>
${rows || '<tr><td colspan="7">暂无数据</td></tr>'}</table>
<p class="footer">景区AI导览数字人系统 · 自动生成报告</p>
</body></html>`
}

function escHtml(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

function buildReportText() {
  const m = metrics.value
  const now = new Date().toLocaleString('zh-CN')
  const dateLabel = dateRange.value?.length === 2
    ? `${dateRange.value[0].toLocaleDateString('zh-CN')} 至 ${dateRange.value[1].toLocaleDateString('zh-CN')}`
    : '全部'
  const lines = [
    '═══════════════════════════════════════',
    '   景区AI导览 — 游客数据分析报告',
    '═══════════════════════════════════════',
    `报告时间：${now}    数据范围：${dateLabel}`,
    '',
    '【一、核心指标】',
    ...m.map(x => `  ${x.label}：${x.value}（趋势：${x.trend}）`),
    '',
    '【二、情感趋势（近14天）】',
    '  积极 ~68%  中性 ~24%  消极 ~8%',
    '',
    '【三、访问来源】',
    '  手机APP 68% | 景区大屏 22% | Web端 10%',
    '',
    '【四、问题分类】',
    '  景点介绍 35% | 路线导览 22% | 交通停车 18%',
    '  餐饮服务 12% | 票价优惠 8% | 其他 5%',
    '',
    '【五、响应延迟分布】',
    '  <0.5s: 312  0.5-1s: 456  1-1.5s: 298',
    '  1.5-2s: 143  2-3s: 62  >3s: 13',
    '',
    '【六、满意度评分】',
    '  平均 4.8/5.0 | 5星 978 | 4星 215 | 3星 68 | 2星 15 | 1星 8',
    '',
    '【七、游客评价】',
    ...Object.entries(reviews).flatMap(([k,list]) => [
      `  [${k === 'positive' ? '好评' : k === 'neutral' ? '中评' : '差评'}]`,
      ...list.map(r => `    ${r.user}：${'★'.repeat(r.rating)} — ${r.content}`)
    ]),
    '',
    '【八、对话记录】',
  ]
  chatLogs.value.forEach(r => {
    lines.push(`  [${r.created_at}] ${sentimentMap[r.sentiment] || ''} | ${r.source || ''} | ${r.response_time_ms || ''}ms`)
    lines.push(`    问：${r.user_query || ''}`)
    lines.push(`    答：${(r.ai_answer || '').slice(0, 100)}`)
  })
  lines.push('', '═══════════════════════════════════════')
  lines.push('  景区AI导览数字人系统 · 自动生成报告')
  return lines.join('\n')
}

function buildReportCSV() {
  const headers = ['时间', '用户问题', 'AI回答', '情感', '来源', '响应(ms)', 'RAG']
  const rows = chatLogs.value.map(r => [
    r.created_at || '',
    (r.user_query || '').replace(/"/g,'""'),
    (r.ai_answer || '').replace(/"/g,'""'),
    sentimentMap[r.sentiment] || '',
    r.source || '',
    r.response_time_ms || '',
    r.rag_used ? '是' : '否'
  ])
  const csvLines = [headers.join(','), ...rows.map(r => '"' + r.join('","') + '"')]
  // BOM for Excel
  return '﻿' + csvLines.join('\n')
}

function buildReportXLS() {
  const rows = chatLogs.value.map(r => `
    <tr>
      <td>${r.created_at || ''}</td><td>${escHtml(r.user_query || '')}</td>
      <td>${escHtml(r.ai_answer || '')}</td><td>${sentimentMap[r.sentiment] || ''}</td>
      <td>${r.source || ''}</td><td>${r.response_time_ms || ''}</td><td>${r.rag_used ? '是' : '否'}</td>
    </tr>`).join('')
  const m = metrics.value
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>游客数据分析报告</title></head><body>
<h1>景区AI导览 — 游客数据分析报告</h1>
<p>报告时间：${new Date().toLocaleString('zh-CN')}</p>
<h2>核心指标</h2>
<table><tr><th>指标</th><th>数值</th><th>趋势</th></tr>
${m.map(x => `<tr><td>${x.label}</td><td>${x.value}</td><td>${x.trend}</td></tr>`).join('')}
</table>
<h2>对话记录</h2>
<table><tr><th>时间</th><th>用户问题</th><th>AI回答</th><th>情感</th><th>来源</th><th>响应(ms)</th><th>RAG</th></tr>
${rows || '<tr><td colspan="7">暂无数据</td></tr>'}</table>
</body></html>`
}

function exportReport(format) {
  let content, mime, ext
  switch (format) {
    case 'doc':
      content = buildReportHTML()
      mime = 'application/msword'
      ext = 'doc'
      break
    case 'xls':
      content = buildReportXLS()
      mime = 'application/vnd.ms-excel'
      ext = 'xls'
      break
    case 'csv':
      content = buildReportCSV()
      mime = 'text/csv;charset=utf-8'
      ext = 'csv'
      break
    case 'txt':
      content = buildReportText()
      mime = 'text/plain;charset=utf-8'
      ext = 'txt'
      break
    default:
      return
  }
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = getReportFilename(ext)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success(`报告已导出为 ${ext.toUpperCase()} 格式`)
}

onMounted(() => {
  setTimeout(initCharts, 100)
  window.addEventListener('resize', handleAnalyticsResize)
})

onActivated(() => {
  window.addEventListener('resize', handleAnalyticsResize)
  Object.values(charts).forEach(c => c?.resize())
})

onDeactivated(() => {
  window.removeEventListener('resize', handleAnalyticsResize)
})

onBeforeUnmount(() => {
  Object.values(charts).forEach(c => c?.dispose())
  window.removeEventListener('resize', handleAnalyticsResize)
})

function handleAnalyticsResize() {
  Object.values(charts).forEach(c => c?.resize())
}
</script>

<style scoped>
.analytics-page {}
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; }
.page-subtitle { font-size: 13px; color: #888; margin-top: 4px; }
.header-actions { display: flex; gap: 10px; align-items: center; }

.metrics-row { margin-bottom: 16px; }
.metric-card {
  background: #fff; border-radius: 8px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.metric-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.metric-label { font-size: 13px; color: #666; }
.metric-value { font-size: 26px; font-weight: 700; margin-bottom: 10px; }
.metric-bar {}

.card-header { display: flex; justify-content: space-between; align-items: center; }
.review-tabs { margin: 0; }
:deep(.review-tabs .el-tabs__header) { margin: 0; }
:deep(.review-tabs .el-tabs__nav-wrap::after) { display: none; }

.review-list { display: flex; flex-direction: column; gap: 12px; max-height: 300px; overflow-y: auto; }
.review-item { background: #fafafa; border-radius: 8px; padding: 12px; border: 1px solid #f0f0f0; }
.review-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.review-user { display: flex; align-items: center; gap: 10px; }
.review-username { font-size: 14px; font-weight: 500; }
.review-time { font-size: 12px; color: #aaa; }
.review-stars { color: #e6a23c; font-size: 16px; }
.review-text { font-size: 14px; line-height: 1.6; color: #444; margin-bottom: 8px; }
.review-tags { display: flex; gap: 6px; flex-wrap: wrap; }

.rating-summary { display: flex; justify-content: center; margin-top: 12px; }
.avg-rating { text-align: center; }
.rating-num { font-size: 40px; font-weight: 700; color: #e6a23c; display: block; }
.stars { color: #e6a23c; font-size: 20px; margin: 4px 0; }
.rating-total { font-size: 13px; color: #888; }

.filter-bar { display: flex; gap: 10px; }
.pagination { margin-top: 12px; justify-content: flex-end; display: flex; }
</style>
