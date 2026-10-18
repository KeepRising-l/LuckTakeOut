import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ command }) => ({
  // 生产由 Django 挂在 /rider/ 下；开发仍用根路径，保持 README 里的 5175 地址
  base: command === 'build' ? '/rider/' : '/',
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5175,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8091', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8091', changeOrigin: true },
    },
  },
  build: { outDir: 'dist' },
}))
