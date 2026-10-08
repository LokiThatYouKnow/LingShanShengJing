<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">📚 知识库管理</h2>
        <p class="page-subtitle">上传景区资料，自动切片入向量库，维护景区FAQ</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showUpload = true">上传文档</el-button>
        <el-button :icon="RefreshRight" @click="loadDocs">刷新</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：文档列表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>文档列表</span>
              <div class="search-bar">
                <el-input
                  v-model="searchQuery"
                  placeholder="搜索文档..."
                  :prefix-icon="Search"
                  clearable
                  style="width:220px"
                />
                <el-select v-model="filterStatus" placeholder="状态" style="width:120px">
                  <el-option label="全部" value="" />
                  <el-option label="已入库" value="indexed" />
                  <el-option label="处理中" value="processing" />
                  <el-option label="失败" value="failed" />
                </el-select>
              </div>
            </div>
          </template>

          <el-table
            :data="filteredDocs"
            v-loading="loading"
            stripe
          >
            <el-table-column prop="filename" label="文件名" min-width="200">
              <template #default="{ row }">
                <div class="file-info">
                  <span class="file-icon">{{ fileIcon(row.file_type) }}</span>
                  <div>
                    <div class="file-name">{{ row.filename }}</div>
                    <div class="file-meta">{{ row.file_size }} · {{ row.created_at }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ categoryLabel(row.category) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块数" width="80" align="center" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="statusType(row.status)"
                  size="small"
                  :class="row.status === 'processing' ? 'blink' : ''"
                >
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="170" align="center">
              <template #default="{ row }">
                <div class="action-btns">
                  <el-button text type="primary" size="small" @click="previewDoc(row)">预览</el-button>
                  <el-button text type="warning" size="small" @click="reindex(row)">重建</el-button>
                  <el-button text type="danger" size="small" @click="deleteDoc(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="totalDocs"
            layout="total, prev, pager, next"
            class="pagination"
          />
        </el-card>

        <!-- FAQ管理 -->
        <el-card class="faq-card">
          <template #header>
            <div class="card-header">
              <span>❓ FAQ 常见问题维护</span>
              <el-button type="primary" size="small" :icon="Plus" @click="showFaqDialog = true">新增FAQ</el-button>
            </div>
          </template>
          <el-table :data="faqs" size="small" stripe>
            <el-table-column prop="question" label="问题" />
            <el-table-column prop="answer" label="答案" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="hit_count" label="命中次数" width="90" align="center" />
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="editFaq(row)">编辑</el-button>
                <el-button text type="danger" size="small" @click="deleteFaq(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：知识库信息 -->
      <el-col :span="8">
        <el-card class="kb-info-card">
          <template #header><span>📊 知识库状态</span></template>
          <div class="kb-stats">
            <div class="kb-stat-item" v-for="item in kbStats" :key="item.label">
              <div class="kb-stat-value" :style="{ color: item.color }">{{ item.value }}</div>
              <div class="kb-stat-label">{{ item.label }}</div>
            </div>
          </div>
          <el-divider />
          <div class="storage-bar">
            <div class="storage-label">
              <span>存储使用</span>
              <span>{{ usedStorage }} / 10GB</span>
            </div>
            <el-progress :percentage="storagePercent" :color="storageColor" />
          </div>
        </el-card>

        <!-- 向量搜索测试 -->
        <el-card class="test-card">
          <template #header><span>🔍 向量检索测试</span></template>
          <el-input
            v-model="testQuery"
            placeholder="输入查询内容测试RAG检索..."
            type="textarea"
            :rows="3"
          />
          <el-button
            type="primary"
            style="margin-top:10px;width:100%"
            :loading="testLoading"
            @click="testSearch"
          >
            测试检索
          </el-button>
          <div v-if="testResults.length > 0" class="test-results">
            <div class="results-title">检索结果（相关度排序）：</div>
            <div v-for="(r, i) in testResults" :key="i" class="result-item">
              <div class="result-score">
                <el-tag size="small" :type="r.score > 0.8 ? 'success' : r.score > 0.6 ? 'warning' : 'info'">
                  {{ (r.score * 100).toFixed(0) }}%
                </el-tag>
              </div>
              <p class="result-text">{{ r.text }}</p>
              <p class="result-source">来源：{{ r.source }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUpload" title="上传景区资料" width="520px" @closed="onUploadDialogClosed">
      <el-upload
        ref="uploadRef"
        v-model:file-list="uploadFiles"
        drag multiple
        :auto-upload="false"
        :before-upload="beforeUpload"
        :on-change="onFileChange"
        accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.csv"
        class="upload-area"
      >
        <el-icon class="el-icon--upload" :size="40"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击选择文件</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF / Word / TXT / MD / Excel / CSV，单文件不超过 50MB<br/>
            ⚠️ 提取后文本超过 50 万字符将自动拒绝（约 1000 个分块），大文件请拆分上传
          </div>
        </template>
      </el-upload>
      <div class="upload-options">
        <el-form label-width="80px" size="small">
          <el-form-item label="分类标签">
            <el-select v-model="uploadCategory" placeholder="选择分类" style="width:100%">
              <el-option label="景点介绍" value="spot" />
              <el-option label="历史文化" value="history" />
              <el-option label="游览指引" value="guide" />
              <el-option label="餐饮住宿" value="food" />
              <el-option label="应急安全" value="safety" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="自动入库">
            <el-switch v-model="autoIndex" />
            <span class="form-tip">上传后自动切片并入向量库</span>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- FAQ编辑对话框 -->
    <el-dialog v-model="showFaqDialog" :title="editingFaq ? '编辑FAQ' : '新增FAQ'" width="560px">
      <el-form :model="faqForm" label-width="80px">
        <el-form-item label="问题" required>
          <el-input v-model="faqForm.question" placeholder="请输入常见问题" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="faqForm.answer" type="textarea" :rows="4" placeholder="请输入标准答案" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="faqForm.category" style="width:100%">
            <el-option label="景点信息" value="spot" />
            <el-option label="交通停车" value="traffic" />
            <el-option label="餐饮服务" value="food" />
            <el-option label="开放时间" value="time" />
            <el-option label="票务优惠" value="ticket" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFaqDialog = false">取消</el-button>
        <el-button type="primary" @click="saveFaq">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文档预览对话框 -->
    <el-dialog v-model="showPreview" :title="'📄 ' + previewFileName" width="800px" top="5vh" @closed="previewContent = ''">
      <div v-if="previewLoading" class="preview-loading">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>正在加载文档内容...</p>
      </div>
      <div v-else class="preview-body">
        <div class="preview-meta">
          <el-tag size="small" :type="previewFileType === 'pdf' ? 'danger' : previewFileType === 'xlsx' || previewFileType === 'csv' ? 'success' : 'info'">
            {{ previewFileType?.toUpperCase() }}
          </el-tag>
          <span class="preview-length">{{ previewContent.length.toLocaleString() }} 字符</span>
        </div>
        <el-divider style="margin: 10px 0" />
        <div class="preview-content" v-text="previewContent"></div>
      </div>
      <template #footer>
        <el-button @click="showPreview = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, RefreshRight, Search, UploadFilled, Loading } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const loading = ref(false)
const uploading = ref(false)
const testLoading = ref(false)
const showUpload = ref(false)
const showFaqDialog = ref(false)
const searchQuery = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = ref(10)
const totalDocs = ref(0)
const uploadFiles = ref([])
const uploadCategory = ref('spot')
const autoIndex = ref(true)
const testQuery = ref('')
const testResults = ref([])
const selectedDoc = ref(null)
const editingFaq = ref(null)

const showPreview = ref(false)
const previewLoading = ref(false)
const previewFileName = ref('')
const previewFileType = ref('')
const previewContent = ref('')

const faqForm = ref({ question: '', answer: '', category: 'spot' })

// 全部来自后端API
const docs = ref([])
const faqs = ref([])
const kbStats = ref([
  { label: '文档总数', value: '0', color: '#409eff' },
  { label: '向量分块', value: '0', color: '#67c23a' },
  { label: 'FAQ条目', value: '0', color: '#e6a23c' },
  { label: 'RAG分块', value: '0', color: '#f56c6c' },
])
const usedStorage = ref('--')
const storagePercent = ref(0)
const storageColor = '#409eff'

const filteredDocs = computed(() => {
  return docs.value.filter(d => {
    const keyword = searchQuery.value.toLowerCase()
    const matchQuery = !keyword || (d.filename || d.title || '').toLowerCase().includes(keyword) || (d.title || '').toLowerCase().includes(keyword)
    // 兼容旧状态值: indexed/done 均为已入库, failed/error 均为失败
    let matchStatus = true
    if (filterStatus.value === 'indexed') {
      matchStatus = d.status === 'indexed' || d.status === 'done'
    } else if (filterStatus.value === 'failed') {
      matchStatus = d.status === 'failed' || d.status === 'error'
    } else if (filterStatus.value) {
      matchStatus = d.status === filterStatus.value
    }
    return matchQuery && matchStatus
  })
})

function fileIcon(type) {
  const map = { pdf: '📄', docx: '📝', txt: '📃', md: '📋', xlsx: '📊', csv: '📈', doc: '📝', text: '📃' }
  return map[type] || '📁'
}

function categoryLabel(cat) {
  const map = { spot: '景点介绍', history: '历史文化', guide: '游览指引', food: '餐饮住宿', safety: '应急安全', other: '其他' }
  return map[cat] || cat || '未分类'
}

function statusType(s) {
  const map = { indexed: 'success', done: 'success', processing: 'warning', failed: 'danger', error: 'danger', pending: 'info' }
  return map[s] || 'info'
}

function statusLabel(s) {
  const map = { indexed: '已入库', done: '已入库', processing: '处理中', failed: '失败', error: '失败', pending: '待处理' }
  return map[s] || s
}

async function loadDocs() {
  loading.value = true
  try {
    const res = await adminApi.getDocuments({ page: page.value, size: pageSize.value, status: filterStatus.value || undefined })
    const items = (res?.items || []).map(d => ({
      ...d,
      filename: d.file_name || d.title || '未知文件',
      file_type: d.file_type || '',
      file_size: d.file_size || '--',
      preview_chunks: d.preview_chunks || []
    }))
    docs.value = items
    totalDocs.value = res?.total || 0
    // 更新统计
    if (res?.rag_stats) {
      kbStats.value[0].value = String(res.total || 0)
      kbStats.value[1].value = String(res.rag_stats.total_chunks || 0)
      kbStats.value[2].value = String(faqs.value.length)
      kbStats.value[3].value = '--'
    }
  } catch (e) {
    console.error('加载文档失败:', e)
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

async function loadFaqs() {
  try {
    const res = await adminApi.getFaqs()
    faqs.value = (res?.faqs || []).map(f => ({
      ...f,
      hit_count: f.hit_count || 0
    }))
    kbStats.value[2].value = String(faqs.value.length)
  } catch (e) {
    console.error('加载FAQ失败:', e)
  }
}

function beforeUpload(file) {
  const maxSize = 50 * 1024 * 1024
  const allowed = ['.pdf','.docx','.doc','.txt','.md','.xlsx','.xls','.csv']
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件类型: ${ext}（支持 PDF/Word/TXT/MD/Excel/CSV）`)
    return false
  }
  if (file.size > maxSize) {
    ElMessage.error(`文件 ${file.name} 超过 50MB 限制（当前 ${(file.size / 1024 / 1024).toFixed(1)}MB）`)
    return false
  }
  // 警告大文件（某些 xlsx/csv 提取后可能超大）
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning(`${file.name} 较大（${(file.size / 1024 / 1024).toFixed(1)}MB），如内容过多可能被拒绝，建议拆分上传`)
  }
  return true
}

// on-change 拦截：从列表中移除无效文件（before-upload 返回 false 不会阻止文件加入列表）
function onFileChange(file, fileList) {
  const allowed = ['.pdf','.docx','.doc','.txt','.md','.xlsx','.xls','.csv']
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowed.includes(ext)) {
    // 从列表中移除无效文件
    const idx = uploadFiles.value.findIndex(f => f.uid === file.uid)
    if (idx !== -1) uploadFiles.value.splice(idx, 1)
  }
}

// 对话框关闭时清空文件列表
function onUploadDialogClosed() {
  uploadFiles.value = []
}

// el-upload 的 http-request：逐个文件上传
async function uploadDoc({ file, onProgress, onSuccess, onError }) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', file.name)
  formData.append('category', uploadCategory.value)
  try {
    await adminApi.uploadDocument(formData)
    onSuccess()
  } catch (e) {
    onError(e)
  }
}

// 确认上传：触发 el-upload 的 submit()
async function submitUpload() {
  if (uploadFiles.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  // el-upload 的 auto-upload 通过 http-request 逐个上传
  // 这里手动触发每个文件上传
  try {
    for (const f of uploadFiles.value) {
      if (f.status !== 'success') {
        const formData = new FormData()
        formData.append('file', f.raw)
        formData.append('title', f.name)
        formData.append('category', uploadCategory.value)
        await adminApi.uploadDocument(formData)
      }
    }
    ElMessage.success('文档已上传，正在后台处理入库...')
    showUpload.value = false
    uploadFiles.value = []
    await loadDocs()
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    ElMessage.error({ message: '上传失败: ' + detail, duration: 6000 })
  } finally {
    uploading.value = false
  }
}

async function previewDoc(row) {
  showPreview.value = true
  previewLoading.value = true
  previewFileName.value = row.filename || row.file_name || row.title || ''
  previewFileType.value = row.file_type || ''
  previewContent.value = ''
  try {
    const res = await adminApi.getDocumentContent(row.id)
    previewContent.value = res?.content || '(文档内容为空)'
  } catch (e) {
    previewContent.value = '加载失败: ' + (e?.response?.data?.detail || e?.message || '未知错误')
    ElMessage.error('预览失败')
  } finally {
    previewLoading.value = false
  }
}

async function reindex(row) {
  try {
    await ElMessageBox.confirm(`确认重建 "${row.filename}" 的向量索引？`, '确认', { type: 'info' })
    row.status = 'processing'
    await adminApi.reindexDocument(row.id)
    ElMessage.success('正在后台重建索引，请稍后刷新查看...')
    setTimeout(loadDocs, 3000)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('重建失败: ' + (e?.response?.data?.detail || e?.message || ''))
    loadDocs()
  }
}

async function deleteDoc(row) {
  await ElMessageBox.confirm(`确认删除文档 "${row.filename}"？此操作将同时删除相关向量数据。`, '确认删除', { type: 'warning' })
  try {
    await adminApi.deleteDocument(row.id)
    if (selectedDoc.value?.id === row.id) selectedDoc.value = null
    ElMessage.success('已删除')
    await loadDocs()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e?.response?.data?.detail || e?.message || ''))
  }
}

async function testSearch() {
  if (!testQuery.value.trim()) return
  testLoading.value = true
  try {
    const res = await adminApi.searchTest({ query: testQuery.value, top_k: 3 })
    testResults.value = res?.results || []
    if (testResults.value.length === 0) {
      ElMessage.info('未检索到相关内容（知识库可能为空）')
    }
  } catch (e) {
    ElMessage.error('检索失败: ' + (e?.response?.data?.detail || e?.message || ''))
    testResults.value = []
  } finally {
    testLoading.value = false
  }
}

async function editFaq(row) {
  editingFaq.value = row
  faqForm.value = { ...row }
  showFaqDialog.value = true
}

async function saveFaq() {
  if (!faqForm.value.question || !faqForm.value.answer) {
    ElMessage.warning('请填写完整的问题和答案')
    return
  }
  try {
    if (editingFaq.value) {
      await adminApi.updateFaq(editingFaq.value.id, {
        question: faqForm.value.question,
        answer: faqForm.value.answer,
        category: faqForm.value.category
      })
      ElMessage.success('FAQ已更新')
    } else {
      await adminApi.saveFaq({
        question: faqForm.value.question,
        answer: faqForm.value.answer,
        category: faqForm.value.category
      })
      ElMessage.success('FAQ已添加并自动入向量库')
    }
    showFaqDialog.value = false
    editingFaq.value = null
    faqForm.value = { question: '', answer: '', category: 'spot' }
    await loadFaqs()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e?.response?.data?.detail || e?.message || ''))
  }
}

async function deleteFaq(row) {
  await ElMessageBox.confirm('确认删除该FAQ？将从向量库同步移除。', '确认', { type: 'warning' })
  try {
    await adminApi.deleteFaq(row.id)
    ElMessage.success('已删除')
    await loadFaqs()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e?.response?.data?.detail || e?.message || ''))
  }
}

onMounted(() => {
  loadDocs()
  loadFaqs()
})
</script>

<style scoped>
.knowledge-page {}
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; }
.page-subtitle { font-size: 13px; color: #888; margin-top: 4px; }
.header-actions { display: flex; gap: 10px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.search-bar { display: flex; gap: 10px; }
.file-info { display: flex; align-items: center; gap: 10px; }
.file-icon { font-size: 24px; flex-shrink: 0; }
.file-name { font-size: 14px; font-weight: 500; }
.file-meta { font-size: 12px; color: #aaa; margin-top: 2px; }
.pagination { margin-top: 12px; justify-content: flex-end; display: flex; }
.faq-card { margin-top: 16px; }

.kb-info-card {}
.kb-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.kb-stat-item { text-align: center; padding: 12px; background: #f5f7fa; border-radius: 8px; }
.kb-stat-value { font-size: 22px; font-weight: 700; }
.kb-stat-label { font-size: 12px; color: #888; margin-top: 4px; }
.storage-label { display: flex; justify-content: space-between; font-size: 13px; color: #666; margin-bottom: 8px; }

.action-btns { display: flex; justify-content: center; gap: 0; flex-wrap: nowrap; white-space: nowrap; }

.test-card { margin-top: 16px; }
.test-results { margin-top: 12px; }
.results-title { font-size: 13px; font-weight: 500; margin-bottom: 8px; color: #666; }
.result-item { background: #f5f7fa; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
.result-score { margin-bottom: 6px; }
.result-text { font-size: 13px; line-height: 1.6; color: #333; margin-bottom: 4px; }
.result-source { font-size: 12px; color: #888; }

.upload-area { width: 100%; }
.upload-options { margin-top: 16px; }
.form-tip { margin-left: 8px; font-size: 12px; color: #888; }

.blink { animation: blink 1.2s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.preview-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 0; color: #888; gap: 16px; }
.preview-body { max-height: 65vh; display: flex; flex-direction: column; }
.preview-meta { display: flex; align-items: center; gap: 12px; }
.preview-length { font-size: 12px; color: #888; }
.preview-content { flex: 1; overflow-y: auto; white-space: pre-wrap; word-break: break-word; font-size: 14px; line-height: 1.8; color: #333; background: #f9fafb; border: 1px solid #ebeef5; border-radius: 6px; padding: 16px; max-height: 50vh; }
</style>
