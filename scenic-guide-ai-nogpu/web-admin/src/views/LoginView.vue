<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">🏔️</div>
      <h2 class="login-title">景区智慧导览系统</h2>
      <p class="login-subtitle">管理后台</p>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="0" class="login-form">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          style="width:100%;margin-top:8px"
          :loading="loading"
          @click="handleLogin"
        >
          登 录
        </el-button>
      </el-form>
      <p class="login-hint">默认账号：admin / admin123</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const formRef = ref(null)

const form = ref({ username: 'admin', password: 'admin123' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  // 表单校验：校验失败 Element Plus 会 reject，单独捕获避免误报「登录失败」
  try {
    await formRef.value?.validate()
  } catch {
    return  // 校验失败，表单已经显示了红字提示
  }

  loading.value = true
  try {
    // 调用 Python 后端登录（OAuth2PasswordRequestForm）
    const res = await adminApi.login(form.value.username, form.value.password)
    // api 拦截器已 unwrap response.data，res 就是响应体 JSON
    // 兼容多种响应格式:
    //   Python 直接返回: { access_token, token_type, username, role }
    //   Spring Boot 包装: { code, message, data: { accessToken, tokenType, ... }, ok }
    //   Spring Boot 直接:  { accessToken, tokenType, username, role }
    const token = res?.access_token
        || res?.data?.accessToken
        || res?.data?.access_token
        || res?.accessToken
    console.log('[Login] res:', res, 'token:', token ? 'OK' : 'MISSING')
    if (token) {
      localStorage.setItem('admin_token', token)
      localStorage.setItem('python_token', token)
      localStorage.setItem('admin_username', form.value.username)

      // 获取用户信息（角色等）
      try {
        const me = await adminApi.getMe()
        localStorage.setItem('admin_role', me?.role || '')
      } catch {
        // getMe 可能返回 401 如果还没设置 token header
      }

      ElMessage.success('登录成功')
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } else {
      ElMessage.error('登录失败：未获取到有效令牌，请检查账号密码')
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || err?.response?.data?.message || err?.message || '登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a1628, #1a3a6a, #0d2137);
  display: flex; align-items: center; justify-content: center;
}
.login-card {
  width: 380px; background: #fff; border-radius: 16px;
  padding: 40px 36px; text-align: center;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.login-logo { font-size: 56px; margin-bottom: 12px; }
.login-title { font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 4px; }
.login-subtitle { font-size: 14px; color: #888; margin-bottom: 28px; }
.login-form { text-align: left; }
.login-hint { font-size: 12px; color: #bbb; margin-top: 20px; }

/* 移动端全屏显示 */
@media (max-width: 768px) {
  .login-page { padding: 0; }
  .login-card {
    width: 100vw;
    min-height: 100vh;
    border-radius: 0;
    padding: 60px 24px 40px;
    box-shadow: none;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .login-logo { font-size: 48px; }
  .login-title { font-size: 20px; }
  .login-subtitle { font-size: 13px; margin-bottom: 24px; }
}
</style>
