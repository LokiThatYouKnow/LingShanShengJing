<template>
  <div class="tourists-page">
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>游客账号管理</span>
          <el-input v-model="keyword" placeholder="搜索昵称/手机号" style="width:100%;max-width:220px" clearable @clear="fetchList" @keyup.enter="fetchList">
            <template #append><el-button @click="fetchList">搜索</el-button></template>
          </el-input>
        </div>
      </template>
      <el-table :data="list" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="头像" width="60">
          <template #default="{ row }">
            <el-avatar :size="32" :src="row.avatar_url" v-if="row.avatar_url" />
            <el-avatar :size="32" v-else>{{ (row.nickname || '?')[0] }}</el-avatar>
          </template>
        </el-table-column>
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="visit_count" label="访问次数" width="90" />
        <el-table-column prop="review_count" label="评论数" width="80" />
        <el-table-column prop="complaint_count" label="投诉数" width="80" />
        <el-table-column prop="last_visit" label="最后访问" width="170">
          <template #default="{ row }">{{ formatTime(row.last_visit) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="toggleStatus(row)">
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-popconfirm
              :title="`确定删除游客「${row.nickname || row.id}」吗？将同时删除其评论数据。`"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="deleteTourist(row)"
            >
              <template #reference>
                <el-button size="small" type="danger" plain>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="list.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无游客数据" :image-size="60" />
      </div>
      <div style="display: flex; justify-content: flex-end; margin-top: 16px">
        <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="pageSize" v-model:current-page="page" @current-change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'

const page = ref(1)
const pageSize = 20
const total = ref(0)
const list = ref([])
const loading = ref(false)
const keyword = ref('')

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

async function fetchList() {
  loading.value = true
  try {
    const res = await adminApi.getTourists({ page: page.value, size: pageSize, keyword: keyword.value || undefined })
    list.value = res?.items || []
    total.value = res?.total || 0
  } catch (e) {
    ElMessage.error('获取游客列表失败: ' + (e.response?.data?.detail || e.message || '网络错误'))
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function toggleStatus(row) {
  try {
    const res = await adminApi.toggleTouristStatus(row.id)
    ElMessage.success(res?.message || '操作成功')
    fetchList()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  }
}

async function deleteTourist(row) {
  try {
    const res = await adminApi.deleteTourist(row.id)
    ElMessage.success(res?.message || '删除成功')
    fetchList()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  }
}

onMounted(fetchList)
</script>

<style scoped>
.tourists-page { padding: 0; }
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
}

@media (max-width: 768px) {
  .tourists-page .el-card__header > div { flex-direction: column; gap: 8px; align-items: stretch; }
  .tourists-page .el-card__header .el-input { max-width: 100% !important; }
}
</style>
