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
      <div class="login-logo serif">拾</div>
      <h1 class="serif">拾味外卖</h1>
      <p>好好吃饭，是一件正经事</p>
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
  background:
    radial-gradient(100% 60% at 50% 0%, rgba(255, 255, 255, 0.28) 0%, transparent 60%),
    linear-gradient(165deg, #ff8a3d 0%, #ff6f1c 46%, var(--canvas) 46.2%, var(--canvas) 100%);
  padding: 0 28px;
}
.login-hero {
  padding: calc(env(safe-area-inset-top) + 64px) 0 40px;
  color: #fff;
  text-align: center;
}
.login-logo {
  width: 76px;
  height: 76px;
  margin: 0 auto 16px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.2);
  border: 1.5px solid rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 38px;
  font-weight: 700;
  box-shadow: var(--shadow-3);
}
.login-hero h1 {
  font-size: var(--text-4xl);
  font-weight: 700;
  letter-spacing: 3px;
}
.login-hero p {
  margin-top: 10px;
  font-size: var(--text-md);
  opacity: 0.92;
  letter-spacing: 1px;
}
.login-form {
  background: var(--surface);
  border-radius: var(--radius-xl);
  padding: 12px 4px 28px;
  box-shadow: var(--shadow-2);
  border: 1px solid var(--hairline);
}
.login-form :deep(.van-field) {
  height: 58px;
  align-items: center;
}
.login-btn {
  margin: 20px 16px 0;
  width: calc(100% - 32px);
  font-weight: 600;
  letter-spacing: 2px;
}
.login-tip {
  margin-top: 16px;
  text-align: center;
  font-size: var(--text-sm);
  color: var(--ink-3);
}
</style>
