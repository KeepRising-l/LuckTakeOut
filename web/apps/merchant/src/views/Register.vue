<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { register } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  name: '',
  phone: '',
  address: '',
  description: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入登录账号', trigger: 'blur' },
    { min: 3, message: '账号至少 3 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入登录密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_r, value, cb) => {
        if (value !== form.password) cb(new Error('两次输入的密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
  name: [{ required: true, message: '请输入店铺名称', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入联系电话', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '请输入 11 位手机号', trigger: 'blur' },
  ],
  address: [{ required: true, message: '请输入店铺地址', trigger: 'blur' }],
}

async function submit() {
  await formRef.value?.validate().catch(() => Promise.reject())
  loading.value = true
  try {
    const data = await register({
      username: form.username,
      password: form.password,
      name: form.name,
      phone: form.phone,
      address: form.address,
      description: form.description,
    })
    auth.setAuth(data.token, {
      merchantId: data.merchantId,
      merchantName: data.merchantName,
      avatar: data.avatar,
      status: data.status,
    })
    ElMessage.success('入驻申请已提交，请等待平台审核')
    router.push('/review')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-head">
        <h1>商家入驻</h1>
        <p>填写账号与店铺资料，提交后由平台审核</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px" @keyup.enter="submit">
        <el-divider content-position="left">登录账号</el-divider>
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="登录用的账号" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>

        <el-divider content-position="left">店铺资料</el-divider>
        <el-form-item label="店铺名称" prop="name">
          <el-input v-model="form.name" placeholder="顾客看到的店铺名" />
        </el-form-item>
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="form.phone" placeholder="11 位手机号" />
        </el-form-item>
        <el-form-item label="店铺地址" prop="address">
          <el-input v-model="form.address" placeholder="门店所在的详细地址" />
        </el-form-item>
        <el-form-item label="店铺简介">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            maxlength="255"
            show-word-limit
            placeholder="选填，简单介绍主营品类"
          />
        </el-form-item>

        <el-button type="primary" class="submit-btn" :loading="loading" @click="submit">
          提交入驻申请
        </el-button>
      </el-form>
      <div class="register-foot">
        已有账号？<router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: linear-gradient(135deg, #fff1e5 0%, #ffe3c9 45%, #ffd3b3 100%);
}
.register-card {
  width: 520px;
  background: #fff;
  border-radius: 12px;
  padding: 32px 36px 24px;
  box-shadow: 0 12px 40px rgba(204, 87, 25, 0.15);
}
.register-head { text-align: center; margin-bottom: 12px; }
.register-head h1 { margin: 0 0 4px; font-size: 22px; color: #303133; }
.register-head p { margin: 0; color: #909399; font-size: 13px; }
.submit-btn { width: 100%; margin-top: 8px; }
.register-foot {
  margin-top: 16px;
  text-align: center;
  font-size: 13px;
  color: #909399;
}
.register-foot a { color: #ff6d1f; text-decoration: none; }
</style>
