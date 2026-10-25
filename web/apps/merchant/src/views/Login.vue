<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { login } from '@/api'
import { STATUS_APPROVED, useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

// 测试账号入口只在开发构建展示，生产构建不暴露演示凭据
const isDev = import.meta.env.DEV

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function fillTest() {
  form.username = 'merchant1'
  form.password = 'merchant123'
}

async function submit() {
  await formRef.value?.validate().catch(() => Promise.reject())
  loading.value = true
  try {
    const data = await login({ ...form })
    auth.setAuth(data.token, {
      merchantId: data.merchantId,
      merchantName: data.merchantName,
      avatar: data.avatar,
      status: data.status,
    })
    ElMessage.success('登录成功')
    // 未通过入驻审核的商户登录后只能查看审核状态（R3）
    router.push(data.status === STATUS_APPROVED ? '/' : '/review')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-head">
        <span class="logo serif">商</span>
        <h1 class="serif">商户中心</h1>
        <p>外卖平台商家管理端</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="submit">登 录</el-button>
        <el-button v-if="isDev" class="test-btn" text @click="fillTest">测试账号 merchant1 / merchant123</el-button>
      </el-form>
      <div class="login-foot">
        还没有账号？<router-link to="/register">商家入驻</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(120% 100% at 80% 0%, rgba(255, 255, 255, 0.35) 0%, transparent 55%),
    linear-gradient(135deg, #fff3e8 0%, #ffe8d1 45%, #ffd9b3 100%);
}
.login-card {
  width: 380px;
  background: var(--surface);
  border-radius: var(--radius-xl);
  padding: 40px 36px 28px;
  box-shadow: var(--shadow-2);
  border: 1px solid var(--hairline);
}
.login-head { text-align: center; margin-bottom: 24px; }
.login-head h1 { margin: 8px 0 4px; font-size: 22px; color: var(--ink-1); }
.login-head p { margin: 0; color: var(--ink-3); font-size: 13px; }
.logo {
  display: inline-block;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--brand-500);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  line-height: 48px;
  text-align: center;
  box-shadow: var(--shadow-brand);
}
.login-btn { width: 100%; margin-top: 4px; font-weight: 600; }
.test-btn {
  width: 100%;
  margin: 10px 0 0;
  color: var(--ink-3);
  font-size: 12px;
}
.login-foot {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: var(--ink-3);
}
.login-foot a { color: var(--brand-600); text-decoration: none; }
</style>
