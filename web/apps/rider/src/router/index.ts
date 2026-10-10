import { createRouter, createWebHashHistory } from 'vue-router'
import { storage } from '@takeout/shared'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { title: '骑手登录' },
    },
    {
      path: '/',
      name: 'workbench',
      component: () => import('@/views/Workbench.vue'),
      meta: { title: '接单' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/Profile.vue'),
      meta: { title: '我的' },
    },
    {
      path: '/task/:id',
      name: 'task-detail',
      component: () => import('@/views/TaskDetail.vue'),
      meta: { title: '任务详情' },
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.title) document.title = `${to.meta.title} - 骑手端`
  const hasToken = !!storage.get('riderToken')
  if (to.path !== '/login' && !hasToken) return { path: '/login', replace: true }
  if (to.path === '/login' && hasToken) return { path: '/', replace: true }
})

export default router
