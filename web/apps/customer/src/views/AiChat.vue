<script setup lang="ts">
import { useRouter } from 'vue-router'
import AiChatPanel from '@/components/AiChatPanel.vue'

const router = useRouter()
</script>

<template>
  <div class="ai-page">
    <van-nav-bar title="AI 点餐助手" left-arrow @click-left="router.back()" />
    <div class="ai-page-body">
      <AiChatPanel />
    </div>
  </div>
</template>

<style scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--canvas);
}
.ai-page-body {
  flex: 1;
  min-height: 0;
}
</style>
