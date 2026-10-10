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
  <van-tabbar route :model-value="active" safe-area-inset-bottom>
    <van-tabbar-item v-for="t in tabs" :key="t.to" :to="t.to" :icon="t.icon">
      {{ t.text }}
    </van-tabbar-item>
  </van-tabbar>
</template>
