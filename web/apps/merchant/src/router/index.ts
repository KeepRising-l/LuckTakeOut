import { createRouter, createWebHistory } from 'vue-router'
import { storage } from '@takeout/shared'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { title: '商户登录' } },
    {
      path: '/',
      component: () => import('@/layout/AdminLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '仪表盘' } },
        { path: 'orders', name: 'orders', component: () => import('@/views/Orders.vue'), meta: { title: '订单管理' } },
        { path: 'products', name: 'products', component: () => import('@/views/Products.vue'), meta: { title: '菜品管理' } },
        { path: 'categories', name: 'categories', component: () => import('@/views/Categories.vue'), meta: { title: '分类管理' } },
        { path: 'shop', name: 'shop', component: () => import('@/views/Shop.vue'), meta: { title: '店铺信息' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || ''} - 商户中心`
  if (to.path !== '/login' && !storage.get('merchantToken')) return '/login'
  if (to.path === '/login' && storage.get('merchantToken')) return '/'
})

export default router
