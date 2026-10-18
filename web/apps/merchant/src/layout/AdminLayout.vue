<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menus = [
  { path: '/dashboard', label: '仪表盘' },
  { path: '/orders', label: '订单管理' },
  { path: '/products', label: '菜品管理' },
  { path: '/categories', label: '分类管理' },
  { path: '/shop', label: '店铺信息' },
]

async function onLogout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="210px" class="aside">
      <div class="brand">
        <span class="brand-dot"></span>
        <span class="serif">商户中心</span>
      </div>
      <el-menu :default-active="route.path" router class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ route.meta.title }}</div>
        <el-dropdown>
          <span class="user-entry">
            <el-avatar :size="30" :src="auth.info.avatar || undefined">
              {{ (auth.info.merchantName || '商').slice(0, 1) }}
            </el-avatar>
            <span class="user-name">{{ auth.info.merchantName || '商户' }}</span>
            <span class="caret"></span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/shop')">店铺信息</el-dropdown-item>
              <el-dropdown-item divided @click="onLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout { height: 100%; }
.aside {
  background: var(--surface);
  border-right: 1px solid var(--hairline);
  display: flex;
  flex-direction: column;
}
.brand {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  font-size: 17px;
  font-weight: 700;
  color: var(--brand-600);
  border-bottom: 1px solid var(--hairline);
}
.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand-500);
}
.menu { border-right: none; flex: 1; }
.menu :deep(.el-menu-item.is-active) {
  background: var(--brand-50);
  color: var(--brand-600);
  border-right: 3px solid var(--brand-500);
}
.header {
  height: 60px;
  background: var(--surface);
  border-bottom: 1px solid var(--hairline);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-title { font-size: 16px; font-weight: 600; }
.user-entry { display: flex; align-items: center; gap: 8px; cursor: pointer; outline: none; }
.user-name { font-size: 14px; }
.caret {
  width: 0; height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid var(--ink-3);
}
.main { background: var(--canvas); padding: 16px; overflow: auto; }
</style>
