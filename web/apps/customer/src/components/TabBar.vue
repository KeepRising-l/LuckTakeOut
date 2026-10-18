<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  { to: '/', icon: 'wap-home-o', text: '首页' },
  { to: '/orders', icon: 'orders-o', text: '订单' },
  { to: '/profile', icon: 'user-o', text: '我的' },
]

const active = computed(() => route.path)
</script>

<template>
  <van-tabbar route :model-value="active" safe-area-inset-bottom class="tk-tabbar">
    <van-tabbar-item v-for="t in tabs" :key="t.to" :to="t.to" :icon="t.icon">
      {{ t.text }}
    </van-tabbar-item>
  </van-tabbar>
</template>

<style scoped>
/* 选中态加一枚暖色胶囊底，弱化 Vant 默认的纯变色 */
.tk-tabbar :deep(.van-tabbar-item) {
  transition: color var(--dur-fast) var(--ease-spring);
}
.tk-tabbar :deep(.van-tabbar-item--active) {
  font-weight: 600;
}
</style>
