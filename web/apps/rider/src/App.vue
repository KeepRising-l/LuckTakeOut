<script setup lang="ts">
import { ConfigProvider } from 'vant'
</script>

<template>
  <ConfigProvider :theme-vars="{ primaryColor: 'var(--brand-500)' }">
    <router-view />
  </ConfigProvider>
</template>

<style>
#app {
  max-width: 750px;
  margin: 0 auto;
  min-height: 100vh;
}
</style>
