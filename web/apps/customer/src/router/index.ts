import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/Login.vue'), meta: { title: '登录' } },
    { path: '/', component: () => import('@/views/Home.vue'), meta: { title: '首页', tabbar: true } },
    { path: '/search', component: () => import('@/views/Search.vue'), meta: { title: '搜索' } },
    { path: '/merchant/:id', component: () => import('@/views/Merchant.vue'), meta: { title: '商家' } },
    { path: '/product/:id', component: () => import('@/views/ProductDetail.vue'), meta: { title: '商品详情' } },
    { path: '/cart', component: () => import('@/views/Cart.vue'), meta: { title: '购物车' } },
    { path: '/checkout', component: () => import('@/views/Checkout.vue'), meta: { title: '确认订单' } },
    { path: '/payment/:id', component: () => import('@/views/Payment.vue'), meta: { title: '收银台' } },
    { path: '/orders', component: () => import('@/views/Orders.vue'), meta: { title: '我的订单', tabbar: true } },
    { path: '/orders/:id', component: () => import('@/views/OrderDetail.vue'), meta: { title: '订单详情' } },
    { path: '/addresses', component: () => import('@/views/Addresses.vue'), meta: { title: '地址管理' } },
    { path: '/profile', component: () => import('@/views/Profile.vue'), meta: { title: '我的', tabbar: true } },
    { path: '/ai', component: () => import('@/views/AiChat.vue'), meta: { title: 'AI 点餐助手' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) || '外卖'
})

export default router
