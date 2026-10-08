<template>
  <div class="user-manage">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">员工管理</h2>
        <span class="page-desc">管理系统登录账号，仅超级管理员可访问</span>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增员工</el-button>
    </div>

    <!-- 搜索栏 -->
    <el-card class="search-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索用户名或邮箱"
            clearable
            :prefix-icon="Search"
            @input="handleSearch"
          />
        </el-col>
        <el-col :xs="24" :sm="8" :md="6" :lg="6">
          <el-select v-model="filterRole" placeholder="角色筛选" clearable @change="handleSearch" style="width:100%">
            <el-option label="全部" value="" />
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="普通管理员" value="admin" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="4" :md="4" :lg="4">
          <el-button :icon="Refresh" @click="loadUsers">刷新</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 员工列表 -->
    <el-card class="table-card" shadow="never">
      <el-table
        :data="filteredUsers"
        v-loading="loading"
        stripe
        style="width: 100%"
        :header-cell-style="{ background: '#fafafa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="username" label="用户名" min-width="120">
          <template #default="{ row }">
            <div class="username-cell">
              <el-avatar :size="28" class="user-avatar" :style="{ background: row.role === 'super_admin' ? '#e6a23c' : '#409eff' }">
                {{ row.username[0].toUpperCase() }}
              </el-avatar>
              <span>{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="160">
          <template #default="{ row }">
            <span class="text-muted">{{ row.email || '未设置' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'super_admin' ? 'warning' : 'info'" effect="light">
              {{ row.role === 'super_admin' ? '超级管理员' : '普通管理员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="isActive" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'danger'" size="small">
              {{ row.isActive ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="170">
          <template #default="{ row }">
            <span class="text-muted">{{ formatTime(row.createdAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="row.role !== 'super_admin'">
              <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button type="warning" link size="small" @click="openResetPwdDialog(row)">重置密码</el-button>
              <el-popconfirm
                :title="`确定删除员工「${row.username}」吗？`"
                confirm-button-text="删除"
                cancel-button-text="取消"
                confirm-button-type="danger"
                @confirm="deleteUser(row)"
              >
                <template #reference>
                  <el-button type="danger" link size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
            <span v-else class="text-muted" style="font-size:12px">超管不可操作</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <span class="total-info">共 {{ filteredUsers.length }} 条记录</span>
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增员工' : '编辑员工'"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="90px" class="dialog-form">
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            :disabled="dialogMode === 'edit'"
            placeholder="请输入用户名（登录账号）"
          />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="初始密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少6位"
          />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="角色" prop="role">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="普通管理员" value="admin" />
          </el-select>
          <div class="form-hint">不能创建超级管理员账号</div>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" label="账号状态" prop="isActive">
          <el-switch v-model="form.isActive" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitForm">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog
      v-model="resetPwdVisible"
      title="重置密码"
      width="400px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="resetPwdForm" :rules="resetPwdRules" ref="resetPwdFormRef" label-width="90px">
        <el-form-item label="账号">
          <el-input :value="resetPwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetPwdForm.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPwd">
          <el-input v-model="resetPwdForm.confirmPwd" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const loading = ref(false)
const submitLoading = ref(false)
const users = ref([])
const searchKeyword = ref('')
const filterRole = ref('')

// ---- 弹窗状态 ----
const dialogVisible = ref(false)
const dialogMode = ref('create') // 'create' | 'edit'
const formRef = ref(null)
const currentUserId = ref(null)
const form = ref({ username: '', password: '', email: '', role: 'admin', isActive: true })

const resetPwdVisible = ref(false)
const resetPwdFormRef = ref(null)
const resetPwdForm = ref({ id: null, username: '', password: '', confirmPwd: '' })

// ---- 过滤后列表 ----
const filteredUsers = computed(() => {
  let list = users.value
  if (filterRole.value) {
    list = list.filter(u => u.role === filterRole.value)
  }
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(u =>
      u.username.toLowerCase().includes(kw) ||
      (u.email || '').toLowerCase().includes(kw)
    )
  }
  return list
})

// ---- 表单校验 ----
const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名 3-30 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!value || value.trim() === '') return callback()
        const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRe.test(value)) return callback(new Error('邮箱格式不正确'))
        callback()
      },
      trigger: 'blur'
    }
  ]
}
const resetPwdRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPwd: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== resetPwdForm.value.password) callback(new Error('两次密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

// ---- 数据加载 ----
async function loadUsers() {
  loading.value = true
  try {
    const res = await adminApi.getUsers()
    users.value = res?.data || res || []
  } catch (e) {
    if (e?.response?.status === 403) {
      ElMessage.error('权限不足：仅超级管理员可访问员工管理')
    } else {
      ElMessage.error('加载失败：' + (e?.message || '未知错误'))
    }
  } finally {
    loading.value = false
  }
}

function handleSearch() { /* filteredUsers 是 computed，自动响应 */ }

// ---- 新增 ----
function openCreateDialog() {
  dialogMode.value = 'create'
  form.value = { username: '', password: '', email: '', role: 'admin', isActive: true }
  currentUserId.value = null
  dialogVisible.value = true
}

// ---- 编辑 ----
function openEditDialog(row) {
  dialogMode.value = 'edit'
  form.value = {
    username: row.username,
    email: row.email || '',
    isActive: row.isActive
  }
  currentUserId.value = row.id
  dialogVisible.value = true
}

// ---- 提交表单 ----
async function submitForm() {
  submitLoading.value = true
  try {
    await formRef.value?.validate()
    if (dialogMode.value === 'create') {
      await adminApi.createUser({
        username: form.value.username,
        password: form.value.password,
        email: form.value.email || '',
        role: form.value.role
      })
      ElMessage.success('员工账号创建成功')
    } else {
      await adminApi.updateUser(currentUserId.value, {
        email: form.value.email || '',
        isActive: form.value.isActive
      })
      ElMessage.success('员工信息更新成功')
    }
    dialogVisible.value = false
    await loadUsers()
  } catch (e) {
    const msg = _extractError(e)
    ElMessage.error(msg)
  } finally {
    submitLoading.value = false
  }
}

// ---- 提取错误消息（支持 HTTP 错误 + 表单校验错误）----
function _extractError(e) {
  // HTTP 响应错误
  if (e?.response?.data?.message) return e.response.data.message
  if (e?.response?.data?.msg) return e.response.data.msg
  if (e?.response?.data?.detail) return e.response.data.detail
  // 表单校验错误（Element Plus async-validator 返回 {field: [msgs]}）
  if (e && typeof e === 'object' && !e.message) {
    for (const field of Object.keys(e)) {
      const msgs = e[field]
      if (Array.isArray(msgs) && msgs.length > 0) return msgs[0]
    }
  }
  if (e?.message) return e.message
  return '操作失败'
}

// ---- 删除 ----
async function deleteUser(row) {
  try {
    await adminApi.deleteUser(row.id)
    ElMessage.success(`已删除员工「${row.username}」`)
    await loadUsers()
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '删除失败'
    ElMessage.error(msg)
  }
}

// ---- 重置密码 ----
function openResetPwdDialog(row) {
  resetPwdForm.value = { id: row.id, username: row.username, password: '', confirmPwd: '' }
  resetPwdVisible.value = true
}
async function submitResetPwd() {
  submitLoading.value = true
  try {
    await resetPwdFormRef.value?.validate()
    await adminApi.resetPassword(resetPwdForm.value.id, resetPwdForm.value.password)
    ElMessage.success('密码重置成功')
    resetPwdVisible.value = false
  } catch (e) {
    const msg = _extractError(e)
    ElMessage.error(msg)
  } finally {
    submitLoading.value = false
  }
}

// ---- 工具 ----
function formatTime(timeStr) {
  if (!timeStr) return '-'
  return timeStr.replace('T', ' ').substring(0, 16)
}

onMounted(() => { loadUsers() })
</script>

<style scoped>
.user-manage { display: flex; flex-direction: column; gap: 16px; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 4px;
}
.page-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px; }
.page-desc { font-size: 13px; color: #888; }

.search-card :deep(.el-card__body) { padding: 16px 20px; }

.table-card :deep(.el-card__body) { padding: 0; }
.table-footer {
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  display: flex; justify-content: flex-end;
}
.total-info { font-size: 13px; color: #888; }

.username-cell { display: flex; align-items: center; gap: 8px; }
.user-avatar { flex-shrink: 0; font-size: 12px; font-weight: 600; }
.text-muted { color: #888; font-size: 13px; }

.dialog-form { padding-right: 10px; }
.form-hint { font-size: 12px; color: #f56c6c; margin-top: 4px; }

@media (max-width: 768px) {
  .user-manage .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .user-manage .page-header .el-button { align-self: flex-end; }
  .search-card .el-row { row-gap: 8px; }
  .search-card .el-select { width: 100% !important; }
  .dialog-form { padding-right: 0; }
}
</style>
