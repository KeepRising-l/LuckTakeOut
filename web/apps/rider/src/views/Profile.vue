<script setup lang="ts">
import { useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  try {
    await showConfirmDialog({
      title: '退出登录',
      message: '确定要退出当前账号吗？',
    })
  } catch {
    return
  }
  auth.logout()
  showSuccessToast('已退出登录')
  router.replace('/login')
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-hero">
      <div class="profile-avatar">{{ (auth.riderInfo?.name || '骑').slice(0, 1) }}</div>
      <div class="profile-name serif">{{ auth.riderInfo?.name || '骑手' }}</div>
      <div class="profile-id" v-if="auth.riderInfo?.phone">{{ auth.riderInfo.phone }}</div>
    </div>

    <van-cell-group inset class="profile-cells">
      <van-cell title="手机号" :value="auth.riderInfo?.phone || '--'" />
      <van-cell title="角色" value="外卖骑手" />
    </van-cell-group>

    <div class="profile-actions">
      <van-button block round type="danger" plain @click="logout">退出登录</van-button>
    </div>

    <van-tabbar route safe-area-inset-bottom>
      <van-tabbar-item replace to="/" icon="orders-o">接单</van-tabbar-item>
      <van-tabbar-item replace to="/profile" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.profile-page {
  min-height: 100vh;
  padding-bottom: 60px;
}

.profile-hero {
  background:
    radial-gradient(120% 80% at 85% 0%, rgba(255, 255, 255, 0.22) 0%, transparent 55%),
    linear-gradient(160deg, #ff8a3d 0%, #ff6f1c 58%, #f2570a 100%);
  padding: 32px 0 38px;
  text-align: center;
  color: #fff;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}

.profile-avatar {
  width: 72px;
  height: 72px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  border: 2px solid rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 700;
}

.profile-name {
  font-size: var(--text-2xl);
  font-weight: 700;
  letter-spacing: 1px;
}

.profile-id {
  margin-top: 6px;
  font-size: var(--text-md);
  opacity: 0.88;
  font-variant-numeric: tabular-nums;
}

.profile-cells {
  margin-top: 14px;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.profile-actions {
  margin: 32px 16px;
}
</style>
