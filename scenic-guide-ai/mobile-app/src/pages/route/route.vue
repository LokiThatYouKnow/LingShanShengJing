<template>
  <view class="page">
    <view class="header">
      <text class="title">🗺️ 游览路线推荐</text>
      <text class="subtitle">根据您的偏好智能规划</text>
    </view>

    <!-- 偏好选择 -->
    <view class="pref-section card">
      <text class="section-title">游玩类型</text>
      <view class="pref-tags">
        <view
          v-for="t in tourTypes" :key="t.id"
          class="pref-tag" :class="{active: selectedType === t.id}"
          @tap="selectedType = t.id"
        >
          <text class="tag-icon">{{ t.icon }}</text>
          <text class="tag-name">{{ t.name }}</text>
        </view>
      </view>
      <text class="section-title mt">游览时长</text>
      <view class="duration-select">
        <view
          v-for="d in durations" :key="d"
          class="duration-item" :class="{active: selectedDuration === d}"
          @tap="selectedDuration = d"
        >
          <text>{{ d }}小时</text>
        </view>
      </view>
    </view>

    <!-- 路线模板 -->
    <view class="templates-section">
      <text class="section-title">热门路线</text>
      <view class="template-list">
        <view
          v-for="t in templates" :key="t.id"
          class="template-card card"
          @tap="selectTemplate(t)"
        >
          <view class="template-header">
            <text class="template-name">{{ t.name }}</text>
            <view class="template-tags">
              <view v-for="tag in (t.tags||[])" :key="tag" class="tag">{{ tag }}</view>
            </view>
          </view>
          <text class="template-desc">{{ t.description }}</text>
          <view class="template-meta">
            <text>⏱ {{ t.duration_hours }}小时</text>
            <text>🏃 {{ t.difficulty === 'easy' ? '轻松' : t.difficulty === 'medium' ? '适中' : '挑战' }}</text>
            <text>📍 {{ (t.spots_order||[]).length }}个景点</text>
          </view>
        </view>
      </view>
    </view>

    <!-- AI推荐按钮 -->
    <view class="ai-btn-wrap">
      <view class="ai-btn" :class="{loading: isGenerating}" @tap="generateAIRoute">
        <text v-if="!isGenerating">🤖 AI智能规划路线</text>
        <text v-else>生成中...</text>
      </view>
    </view>

    <!-- AI生成的路线 -->
    <view class="ai-route-section card" v-if="aiRoute">
      <view class="ai-route-header">
        <text class="ai-route-title">✨ AI为您规划的路线</text>
        <text class="ai-route-time">预计 {{ aiRoute.total_hours }} 小时</text>
      </view>
      <view class="route-steps">
        <view v-for="(spot, idx) in aiRoute.route" :key="idx" class="route-step">
          <view class="step-num">{{ idx + 1 }}</view>
          <view class="step-content">
            <text class="step-name">{{ spot }}</text>
          </view>
          <view class="step-line" v-if="idx < aiRoute.route.length - 1"></view>
        </view>
      </view>
      <text class="ai-tips">💡 {{ aiRoute.tips }}</text>
    </view>
  </view>
</template>

<script>
import { scenicApi } from '../../utils/api.js'
export default {
  data() {
    return {
      selectedType: 1,
      selectedDuration: 4,
      tourTypes: [
        { id: 1, icon: '🏛️', name: '历史文化' },
        { id: 2, icon: '🌿', name: '自然风光' },
        { id: 3, icon: '👨‍👩‍👧', name: '亲子游' },
        { id: 4, icon: '📸', name: '摄影打卡' },
      ],
      durations: [2, 3, 4, 6, 8],
      templates: [],
      aiRoute: null,
      isGenerating: false
    }
  },
  async onLoad() {
    await this.loadTemplates()
  },
  methods: {
    async loadTemplates() {
      try {
        const res = await scenicApi.getRouteTemplates()
        this.templates = res.templates || []
      } catch (e) {}
    },
    selectTemplate(t) {
      this.aiRoute = {
        route: t.spots_order?.map((id, i) => `景点${id}`) || [],
        tips: t.description,
        total_hours: t.duration_hours
      }
    },
    async generateAIRoute() {
      this.isGenerating = true
      try {
        const typeNames = {1:'历史文化', 2:'自然风光', 3:'亲子游', 4:'摄影打卡'}
        const res = await scenicApi.recommendRoute({
          type: typeNames[this.selectedType],
          duration: this.selectedDuration,
          difficulty: 'easy'
        })
        this.aiRoute = res.recommended_route
      } catch (e) {
        uni.showToast({ title: '生成失败，请重试', icon: 'none' })
      } finally {
        this.isGenerating = false
      }
    }
  }
}
</script>

<style lang="scss">
.page { padding: 16px; background: #f0f7f4; min-height: 100vh; }
.header { padding: 20px 0 16px; }
.title { font-size: 22px; font-weight: 700; color: #1a7a4a; display: block; }
.subtitle { font-size: 13px; color: #999; margin-top: 4px; display: block; }
.card { background: #fff; border-radius: 14px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
.section-title { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 12px; display: block; &.mt { margin-top: 16px; } }
.pref-tags { display: flex; gap: 10px; flex-wrap: wrap; }
.pref-tag {
  display: flex; flex-direction: column; align-items: center;
  padding: 10px 16px; border-radius: 12px; background: #f5f5f5;
  border: 2px solid transparent; transition: all 0.2s;
  &.active { background: rgba(26,122,74,0.1); border-color: #1a7a4a; }
}
.tag-icon { font-size: 22px; }
.tag-name { font-size: 12px; color: #666; margin-top: 4px; }
.duration-select { display: flex; gap: 8px; }
.duration-item {
  flex: 1; text-align: center; padding: 8px; border-radius: 8px;
  background: #f5f5f5; border: 2px solid transparent;
  text { font-size: 13px; color: #666; }
  &.active { background: rgba(26,122,74,0.1); border-color: #1a7a4a; text { color: #1a7a4a; font-weight: 600; } }
}
.templates-section { margin-bottom: 14px; }
.template-card { cursor: pointer; }
.template-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.template-name { font-size: 16px; font-weight: 600; color: #333; }
.template-tags { display: flex; gap: 6px; }
.tag { background: rgba(26,122,74,0.1); padding: 2px 8px; border-radius: 10px; font-size: 11px; color: #1a7a4a; }
.template-desc { font-size: 13px; color: #666; margin-bottom: 10px; display: block; }
.template-meta { display: flex; gap: 16px; text { font-size: 12px; color: #999; } }
.ai-btn-wrap { margin: 8px 0 16px; }
.ai-btn {
  background: linear-gradient(135deg, #1a7a4a, #2d9e5f);
  padding: 14px; border-radius: 14px; text-align: center;
  box-shadow: 0 4px 15px rgba(26,122,74,0.3);
  text { color: #fff; font-size: 16px; font-weight: 600; }
  &.loading { opacity: 0.7; }
}
.ai-route-section { }
.ai-route-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.ai-route-title { font-size: 16px; font-weight: 600; color: #1a7a4a; }
.ai-route-time { font-size: 13px; color: #999; }
.route-steps { }
.route-step { display: flex; align-items: flex-start; position: relative; padding-bottom: 20px; }
.step-num {
  width: 28px; height: 28px; border-radius: 50%;
  background: #1a7a4a; color: #fff; font-size: 13px; font-weight: 600;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.step-content { margin-left: 12px; }
.step-name { font-size: 15px; color: #333; font-weight: 500; }
.step-line {
  position: absolute; left: 13px; top: 28px; width: 2px; height: calc(100% - 28px);
  background: #e0e0e0;
}
.ai-tips { font-size: 13px; color: #666; margin-top: 8px; line-height: 1.6; display: block; padding: 10px; background: #f9f9f9; border-radius: 8px; }
</style>
