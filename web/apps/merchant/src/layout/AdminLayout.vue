<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElNotification } from 'element-plus'
import { fetchNotifications, markNotificationsRead } from '@/api'
import type { MerchantNotification } from '@/api'
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

// 新订单通知：轮询站内信，首次加载只建立基线，之后新增未读才弹提醒
const notifications = ref<MerchantNotification[]>([])
const unreadCount = ref(0)
let timer: number | undefined
let lastSeenId = 0
let initialized = false
let polling = false

async function loadNotifications() {
  if (polling) return
  polling = true
  try {
    const data = await fetchNotifications()
    const newOnes = data.items.filter((n) => !n.isRead && n.id > lastSeenId)
    const maxId = data.items.length ? Math.max(...data.items.map((n) => n.id)) : 0

    notifications.value = data.items
    unreadCount.value = data.unread
    lastSeenId = Math.max(lastSeenId, maxId)

    if (initialized && newOnes.length) {
      ElNotification({
        title: newOnes[0].title,
        message: newOnes[0].content,
        type: 'warning',
        duration: 8000,
        onClick: () => router.push('/orders'),
      })
    }
    initialized = true
  } catch {
    // 轮询失败静默，避免打扰当前操作；下一轮会重试
  } finally {
    polling = false
  }
}

async function openNotification(n: MerchantNotification) {
  try {
    if (!n.isRead) {
      await markNotificationsRead({ ids: [n.id] })
      n.isRead = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  } catch {
    // 标记失败不阻断跳转，下一轮轮询会纠正未读数
  }
  router.push('/orders')
}

async function readAll() {
  try {
    await markNotificationsRead({ all: true })
    notifications.value = notifications.value.map((n) => ({ ...n, isRead: true }))
    unreadCount.value = 0
  } catch {
    // 静默失败，下一轮轮询重试
  }
}

onMounted(() => {
  loadNotifications()
  timer = window.setInterval(loadNotifications, 15000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})

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
        <div class="header-right">
          <el-popover placement="bottom-end" :width="340" trigger="click">
            <template #reference>
              <el-badge
                :value="unreadCount"
                :max="99"
                :hidden="unreadCount === 0"
                class="notif-badge"
              >
                <el-button text class="notif-btn">通知</el-button>
              </el-badge>
            </template>
            <div class="notif-head">
              <span>新订单通知</span>
              <el-button v-if="unreadCount" link type="primary" size="small" @click="readAll">
                全部已读
              </el-button>
            </div>
            <el-empty
              v-if="!notifications.length"
              description="暂无通知"
              :image-size="60"
            />
            <div v-else class="notif-list">
              <div
                v-for="n in notifications"
                :key="n.id"
                class="notif-item"
                :class="{ unread: !n.isRead }"
                @click="openNotification(n)"
              >
                <div class="notif-title">{{ n.title }}</div>
                <div class="notif-content">{{ n.content }}</div>
                <div class="notif-time">{{ n.createTime }}</div>
              </div>
            </div>
          </el-popover>
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
        </div>
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
.header-right { display: flex; align-items: center; gap: 18px; }
.notif-btn { font-size: 14px; color: var(--ink-2); }
.notif-badge { display: inline-flex; }
.notif-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--hairline);
  font-weight: 600;
}
.notif-list { max-height: 360px; overflow: auto; }
.notif-item {
  padding: 10px 8px;
  border-bottom: 1px solid var(--hairline);
  cursor: pointer;
  border-radius: 6px;
}
.notif-item:hover { background: var(--brand-50); }
.notif-item.unread .notif-title::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--brand-500);
  vertical-align: middle;
}
.notif-title { font-size: 14px; font-weight: 600; }
.notif-content { font-size: 13px; color: var(--ink-2); margin-top: 4px; line-height: 1.5; }
.notif-time { font-size: 12px; color: var(--ink-3); margin-top: 4px; }
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
