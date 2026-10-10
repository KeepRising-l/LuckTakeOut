<script setup lang="ts">
import { ConfigProvider } from 'vant'
</script>

<template>
  <ConfigProvider :theme-vars="{ primaryColor: '#1989fa' }">
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
