import { createRouter, createWebHistory } from 'vue-router'
import { storage } from '@takeout/shared'
import { STATUS_APPROVED, type MerchantInfo } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { title: '商户登录' } },
    { path: '/register', name: 'register', component: () => import('@/views/Register.vue'), meta: { title: '商户入驻' } },
    { path: '/review', name: 'review', component: () => import('@/views/ReviewStatus.vue'), meta: { title: '入驻审核状态' } },
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

/** 未登录可访问的页面 */
const PUBLIC_PATHS = ['/login', '/register']

function storedStatus(): number | undefined {
  return storage.getJSON<MerchantInfo>('merchantInfo')?.status
}

router.beforeEach((to) => {
  document.title = `${to.meta.title || ''} - 商户中心`
  const loggedIn = !!storage.get('merchantToken')
  const approved = storedStatus() === STATUS_APPROVED

  if (PUBLIC_PATHS.includes(to.path)) {
    if (!loggedIn) return true
    return approved ? '/' : '/review'
  }
  if (!loggedIn) return '/login'
  // 未通过入驻审核的商户只能查看审核状态（R3）
  if (!approved && to.path !== '/review') return '/review'
  if (approved && to.path === '/review') return '/'
  return true
})

export default router
