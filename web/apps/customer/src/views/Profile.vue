<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

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
  cart.carts = []
  showToast('已退出登录')
  router.replace('/login')
}

onMounted(() => {
  if (!auth.isLogin) router.replace('/login')
})
</script>

<template>
  <div class="profile-page">
    <van-nav-bar title="我的" :border="false" />
    <div class="user-card">
      <van-image round width="60" height="60" :src="auth.user?.avatar">
        <template #loading><van-icon name="user-o" /></template>
        <template #error><van-icon name="user-o" /></template>
      </van-image>
      <div class="u-info">
        <div class="u-name">{{ auth.user?.nickname || '未登录' }}</div>
        <div class="u-phone">{{ auth.user?.phone || '' }}</div>
      </div>
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
  padding-bottom: 70px;
}
.user-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(135deg, #ff6d1f, #ff8a45);
  margin: 0 12px;
  border-radius: 12px;
  padding: 22px 16px;
  color: #fff;
}
.user-card .van-icon {
  font-size: 34px;
  color: #fff;
}
.u-name {
  font-size: 18px;
  font-weight: 600;
}
.u-phone {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
}
.cell-group {
  margin-top: 12px;
}
.cell-group .van-cell {
  padding: 15px 16px;
}
</style>
