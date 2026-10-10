<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const phone = ref('')
const code = ref('123456')
const counting = ref(false)
const countdown = ref(0)
const loading = ref(false)

async function sendCode() {
  if (!/^1\d{10}$/.test(phone.value)) return showToast('请输入正确的手机号')
  if (counting.value) return
  try {
    await authApi.sendCode(phone.value)
    showToast('验证码已发送')
    counting.value = true
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        clearInterval(timer)
        counting.value = false
      }
    }, 1000)
  } catch (e) {
    showToast((e as Error).message)
  }
}

async function doLogin() {
  if (!/^1\d{10}$/.test(phone.value)) return showToast('请输入正确的手机号')
  if (!code.value) return showToast('请输入验证码')
  loading.value = true
  try {
    const res = await authApi.login(phone.value, code.value)
    auth.setLogin(res.accessToken, res.user)
    showToast('登录成功')
    router.replace('/')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-hero">
      <div class="login-logo">
        <van-icon name="shop-o" />
      </div>
      <h1>欢迎来到外卖点餐</h1>
      <p>登录后开始点餐吧</p>
    </div>
    <div class="login-form">
      <van-field id="phone" v-model="phone" type="tel" maxlength="11" placeholder="请输入手机号" clearable>
        <template #left-icon><van-icon name="phone-o" /></template>
      </van-field>
      <van-field id="code" v-model="code" type="digit" maxlength="6" placeholder="请输入验证码">
        <template #left-icon><van-icon name="shield-o" /></template>
        <template #button>
          <van-button
            size="small"
            plain
            type="primary"
            class="code-btn"
            :disabled="counting"
            @click="sendCode"
          >
            {{ counting ? `${countdown}s 后重发` : '获取验证码' }}
          </van-button>
        </template>
      </van-field>
      <van-button type="primary" block round size="large" class="login-btn" :loading="loading" @click="doLogin">
        登录
      </van-button>
      <p class="login-tip">未注册的手机号将自动创建账号</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #ff6d1f 0%, #ff8f3f 30%, #f7f8fa 70%);
  padding: 0 28px;
}
.login-hero {
  padding: 80px 0 48px;
  color: #fff;
  text-align: center;
}
.login-logo {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-logo .van-icon {
  font-size: 40px;
  color: #fff;
}
.login-hero h1 {
  font-size: 24px;
  font-weight: 600;
}
.login-hero p {
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.9;
}
.login-form {
  background: #fff;
  border-radius: 16px;
  padding: 20px 4px 28px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
}
.login-form .van-field {
  height: 56px;
  align-items: center;
}
.login-btn {
  margin: 24px 16px 0;
  width: calc(100% - 32px);
}
.login-tip {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: #969799;
}
</style>
