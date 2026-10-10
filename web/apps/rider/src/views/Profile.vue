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
    <van-nav-bar title="我的" fixed placeholder />

    <div class="profile-hero">
      <div class="profile-avatar">{{ (auth.riderInfo?.name || '骑').slice(0, 1) }}</div>
      <div class="profile-name">{{ auth.riderInfo?.name || '骑手' }}</div>
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
  background: linear-gradient(180deg, #1989fa 0%, #3d9bfa 100%);
  padding: 28px 0 34px;
  text-align: center;
  color: #fff;
}

.profile-avatar {
  width: 64px;
  height: 64px;
  margin: 0 auto 10px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 600;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
}

.profile-cells {
  margin-top: 12px;
  border-radius: 12px;
  overflow: hidden;
}

.profile-actions {
  margin: 32px 16px;
}
</style>
