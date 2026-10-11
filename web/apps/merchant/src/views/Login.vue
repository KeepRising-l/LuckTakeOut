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
        <span class="logo"></span>
        <h1>商户中心</h1>
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
        <el-button class="test-btn" text @click="fillTest">测试账号 merchant1 / merchant123</el-button>
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
  background: linear-gradient(135deg, #fff1e5 0%, #ffe3c9 45%, #ffd3b3 100%);
}
.login-card {
  width: 380px;
  background: #fff;
  border-radius: 12px;
  padding: 40px 36px 28px;
  box-shadow: 0 12px 40px rgba(204, 87, 25, 0.15);
}
.login-head { text-align: center; margin-bottom: 24px; }
.login-head h1 { margin: 8px 0 4px; font-size: 22px; color: #303133; }
.login-head p { margin: 0; color: #909399; font-size: 13px; }
.logo {
  display: inline-block;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #ff6d1f;
  box-shadow: 0 6px 16px rgba(255, 109, 31, 0.4);
}
.login-btn { width: 100%; margin-top: 4px; }
.test-btn {
  width: 100%;
  margin: 10px 0 0;
  color: #909399;
  font-size: 12px;
}
.login-foot {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: #909399;
}
.login-foot a { color: #ff6d1f; text-decoration: none; }
</style>
