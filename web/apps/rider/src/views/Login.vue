<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const submitting = ref(false)

function fillTest() {
  username.value = 'rider1'
  password.value = 'rider123'
}

async function submit() {
  if (!username.value.trim() || !password.value) {
    showToast('请输入账号和密码')
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    showSuccessToast('登录成功')
    router.replace('/')
  } catch (e) {
    showToast((e as Error).message || '登录失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-hero">
      <div class="login-logo serif">骑</div>
      <h1 class="serif">骑手端</h1>
      <p>接单配送，即刻出发</p>
    </div>

    <div class="login-card">
      <van-form @submit.prevent>
        <van-cell-group inset>
          <van-field
            v-model="username"
            name="username"
            label="账号"
            left-icon="user-o"
            placeholder="请输入骑手账号"
            clearable
            @keyup.enter="submit"
          />
          <van-field
            v-model="password"
            name="password"
            label="密码"
            left-icon="lock"
            type="password"
            placeholder="请输入密码"
            @keyup.enter="submit"
          />
        </van-cell-group>
        <div class="login-actions">
          <van-button round block type="primary" :loading="submitting" @click="submit">
            登 录
          </van-button>
          <van-button round block plain size="small" class="test-btn" @click="fillTest">
            一键填入测试账号
          </van-button>
        </div>
      </van-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background:
    radial-gradient(100% 60% at 50% 0%, rgba(255, 255, 255, 0.28) 0%, transparent 60%),
    linear-gradient(165deg, #ff8a3d 0%, #ff6f1c 46%, var(--canvas) 46.2%, var(--canvas) 100%);
  padding-top: calc(env(safe-area-inset-top) + 72px);
}
.login-hero {
  text-align: center;
  color: #fff;
  margin-bottom: 44px;
}
.login-logo {
  width: 76px;
  height: 76px;
  margin: 0 auto 14px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.2);
  border: 1.5px solid rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  font-weight: 700;
  box-shadow: var(--shadow-3);
}
.login-hero h1 {
  font-size: var(--text-4xl);
  font-weight: 700;
  letter-spacing: 3px;
}
.login-hero p {
  margin-top: 8px;
  font-size: var(--text-md);
  opacity: 0.9;
  letter-spacing: 1px;
}
.login-card {
  padding: 0 4px;
}
.login-actions {
  margin: 28px 24px 0;
}
.test-btn {
  margin-top: 14px;
  width: 100%;
}
</style>
