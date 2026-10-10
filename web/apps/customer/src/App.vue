<script setup lang="ts">
import { ConfigProvider } from 'vant'
</script>

<template>
  <ConfigProvider :theme-vars="{ primaryColor: '#ff6d1f' }">
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
