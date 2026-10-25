<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import TabBar from '@/components/TabBar.vue'

const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()

const cells = [
  { title: '地址管理', icon: 'location-o', to: '/addresses' },
  { title: '我的订单', icon: 'orders-o', to: '/orders' },
  { title: '购物车', icon: 'cart-o', to: '/cart' },
  { title: 'AI 点餐助手', icon: 'chat-o', to: '/ai' },
]

async function logout() {
  await showConfirmDialog({ title: '提示', message: '确定退出登录吗？' })
  auth.logout()
  cart.clearAll()
  showToast('已退出登录')
  router.replace('/login')
}

onMounted(() => {
  if (!auth.isLogin) router.replace('/login')
})
</script>

<template>
  <div class="profile-page">
    <div class="user-card">
      <div class="u-avatar">
        <van-image round width="60" height="60" :src="auth.user?.avatar">
          <template #loading><van-icon name="user-o" /></template>
          <template #error><van-icon name="user-o" /></template>
        </van-image>
      </div>
      <div class="u-info">
        <div class="u-name serif">{{ auth.user?.nickname || '未登录' }}</div>
        <div class="u-phone">{{ auth.user?.phone || '' }}</div>
      </div>
      <div class="u-badge">干饭人</div>
    </div>

    <van-cell-group inset class="cell-group">
      <van-cell v-for="c in cells" :key="c.to" :title="c.title" :icon="c.icon" is-link @click="router.push(c.to)" />
    </van-cell-group>

    <van-cell-group inset class="cell-group">
      <van-cell title="退出登录" icon="revoke" is-link @click="logout" />
    </van-cell-group>

    <TabBar />
  </div>
</template>

<style scoped>
.profile-page {
  min-height: 100vh;
  padding: 12px 0 76px;
}

/* ---------- 用户卡 ---------- */
.user-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background:
    radial-gradient(90% 130% at 90% 10%, rgba(255, 255, 255, 0.26) 0%, transparent 55%),
    linear-gradient(140deg, #ff8a3d 0%, #ff6f1c 60%, #f2570a 100%);
  margin: 0 var(--gutter);
  border-radius: var(--radius-xl);
  padding: 22px 18px;
  color: #fff;
  box-shadow: var(--shadow-brand);
}
.u-avatar :deep(.van-image__img) {
  border: 2px solid rgba(255, 255, 255, 0.8);
}
.u-avatar .van-icon {
  font-size: 34px;
  color: rgba(255, 255, 255, 0.9);
}
.u-info {
  flex: 1;
  min-width: 0;
}
.u-name {
  font-size: var(--text-3xl);
  font-weight: 700;
  letter-spacing: 0.5px;
}
.u-phone {
  font-size: var(--text-md);
  opacity: 0.88;
  margin-top: 6px;
  font-variant-numeric: tabular-nums;
}
.u-badge {
  flex-shrink: 0;
  font-size: var(--text-xs);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.5);
  letter-spacing: 1px;
}

/* ---------- 功能列表 ---------- */
.cell-group {
  margin-top: 12px;
}
.cell-group :deep(.van-cell) {
  padding: 15px 16px;
}
.cell-group :deep(.van-cell__left-icon) {
  color: var(--brand-500);
  font-size: 19px;
  margin-right: 8px;
}
</style>
