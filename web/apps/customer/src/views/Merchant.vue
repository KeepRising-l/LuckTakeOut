<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showLoadingToast, showToast } from 'vant'
import { merchantApi, pickImage, money } from '@/api'
import { useCartStore } from '@/stores/cart'
import type { Merchant, Category, Product } from '@/api'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()

const merchantId = Number(route.params.id)
const merchant = ref<Merchant>()
const categories = ref<Category[]>([])
const products = ref<Product[]>([])
const loading = ref(true)
const activeCat = ref(0)
const showCart = ref(false)
const rightRef = ref<HTMLElement>()

const cartInfo = computed(() => cart.merchantCart(merchantId))
const totalCount = computed(() => cartInfo.value?.items.reduce((n, i) => n + i.quantity, 0) || 0)
const totalPrice = computed(() => cartInfo.value?.items.reduce((n, i) => n + i.price * i.quantity, 0) || 0)

async function load() {
  showLoadingToast({ message: '加载中...', forbidClick: true, duration: 0 })
  try {
    const [m, cats, prods] = await Promise.all([
      merchantApi.detail(merchantId),
      merchantApi.categories(merchantId),
      merchantApi.products(merchantId, { page: 1, size: 100 }),
    ])
    merchant.value = m
    categories.value = cats
    products.value = prods
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    loading.value = false
    closeToast()
  }
}

function productsOf(catId: number) {
  return products.value.filter((p) => p.categoryId === catId)
}

function scrollToCat(catId: number, index: number) {
  activeCat.value = index
  const el = document.getElementById(`cat-${catId}`)
  if (el && rightRef.value) rightRef.value.scrollTo({ top: el.offsetTop, behavior: 'smooth' })
}

function add(p: Product) {
  cart.add({ id: merchantId, name: merchant.value?.name || '', deliveryFee: merchant.value?.deliveryFee || 0 }, p)
}

function dec(p: Product) {
  cart.setCount(merchantId, p.id, cart.quantityOf(merchantId, p.id) - 1)
}

function goCheckout() {
  if (!totalCount.value) return showToast('请先选择商品')
  showCart.value = false
  router.push({ path: '/checkout', query: { merchantId: String(merchantId) } })
}

onMounted(load)
</script>

<template>
  <div class="merchant-page">
    <van-nav-bar :title="merchant?.name || '商家'" left-arrow @click-left="router.back()" />

    <div v-if="merchant" class="m-head">
      <van-image class="m-avatar" radius="10" fit="cover" :src="pickImage(merchant)">
        <template #loading><van-icon name="shop-o" /></template>
      </van-image>
      <div class="m-text">
        <div class="m-name serif">{{ merchant.name }}</div>
        <div class="m-sub">
          <van-rate :model-value="merchant.rating ?? 0" readonly allow-half size="12" />
          <span>{{ merchant.rating != null ? `${merchant.rating} 分` : '暂无评分' }}</span>
          <i class="dot" />
          <span>配送费 ¥{{ money(merchant.deliveryFee) }}</span>
        </div>
        <div class="m-sub m-addr">
          <van-icon name="location-o" />
          <span>{{ merchant.address }}</span>
        </div>
      </div>
    </div>

    <div class="menu-wrap">
      <aside class="cat-nav">
        <div
          v-for="(c, i) in categories"
          :key="c.id"
          class="cat-item"
          :class="{ active: activeCat === i }"
          @click="scrollToCat(c.id, i)"
        >
          {{ c.name }}
        </div>
      </aside>
      <div ref="rightRef" class="product-list">
        <section v-for="c in categories" :id="`cat-${c.id}`" :key="c.id" class="cat-section">
          <div class="cat-title">{{ c.name }}</div>
          <div v-for="p in productsOf(c.id)" :key="p.id" class="product-card">
            <van-image class="p-img" radius="8" fit="cover" :src="pickImage(p)" @click="router.push(`/product/${p.id}`)">
              <template #loading><van-icon name="goods-o" /></template>
            </van-image>
            <div class="p-info">
              <div class="p-name" @click="router.push(`/product/${p.id}`)">{{ p.name }}</div>
              <div class="p-desc">{{ p.description }}</div>
              <div class="p-bottom">
                <div class="p-price tk-price"><span class="yen">¥</span>{{ money(p.price) }}</div>
                <div class="stepper">
                  <transition name="fade">
                    <van-icon v-if="cart.quantityOf(merchantId, p.id) > 0" name="minus" class="step-btn" @click="dec(p)" />
                  </transition>
                  <span v-if="cart.quantityOf(merchantId, p.id) > 0" class="step-num">{{ cart.quantityOf(merchantId, p.id) }}</span>
                  <van-icon name="plus" class="step-btn add" @click="add(p)" />
                </div>
              </div>
            </div>
          </div>
          <van-empty v-if="!productsOf(c.id).length" description="该分类暂无商品" image-size="60" />
        </section>
      </div>
    </div>

    <van-action-bar class="cart-bar">
      <div class="cart-icon-wrap" @click="totalCount && (showCart = true)">
        <van-badge :content="totalCount || ''" max="99">
          <div class="cart-icon" :class="{ on: totalCount > 0 }">
            <van-icon name="cart-o" />
          </div>
        </van-badge>
      </div>
      <div class="cart-total">
        <template v-if="totalCount">
          <span class="total-price tk-price">¥{{ money(totalPrice) }}</span>
          <span class="total-fee">另需配送费 ¥{{ money(merchant?.deliveryFee) }}</span>
        </template>
        <span v-else class="total-empty">购物车是空的</span>
      </div>
      <van-button type="primary" round class="checkout-btn" :disabled="!totalCount" @click="goCheckout">
        去结算
      </van-button>
    </van-action-bar>

    <van-popup v-model:show="showCart" position="bottom" round class="cart-popup">
      <div class="popup-head">
        <span>已选商品</span>
        <span class="clear" @click="cart.clearMerchant(merchantId); showCart = false">
          <van-icon name="delete-o" /> 清空
        </span>
      </div>
      <div class="popup-list">
        <div v-for="i in cartInfo?.items || []" :key="i.productId" class="popup-item">
          <div class="pi-name">{{ i.name }}</div>
          <div class="pi-right">
            <span class="pi-price tk-price">¥{{ money(i.price * i.quantity) }}</span>
            <van-icon name="minus" class="step-btn" @click="cart.setCount(merchantId, i.productId, i.quantity - 1)" />
            <span class="step-num">{{ i.quantity }}</span>
            <van-icon
              name="plus"
              class="step-btn add"
              @click="cart.setCount(merchantId, i.productId, i.quantity + 1)"
            />
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.merchant-page {
  min-height: 100vh;
  padding-bottom: 70px;
}

/* ---------- 店铺头 ---------- */
.m-head {
  display: flex;
  gap: 12px;
  background: var(--surface);
  margin: 12px var(--gutter) 0;
  border-radius: var(--radius-lg);
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
  padding: 14px;
}
.m-avatar {
  width: 68px;
  height: 68px;
  flex-shrink: 0;
}
.m-avatar .van-icon {
  font-size: 28px;
  color: var(--ink-4);
  line-height: 68px;
}
.m-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  justify-content: center;
}
.m-name {
  font-size: var(--text-2xl);
  font-weight: 700;
}
.m-sub {
  font-size: var(--text-sm);
  color: var(--ink-2);
  display: flex;
  align-items: center;
  gap: 5px;
}
.m-addr {
  color: var(--ink-3);
  overflow: hidden;
}
.m-addr span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--ink-4);
}

/* ---------- 菜单双栏 ---------- */
.menu-wrap {
  display: flex;
  margin-top: 12px;
  height: calc(100vh - 236px);
}
.cat-nav {
  width: 92px;
  background: var(--surface-2);
  flex-shrink: 0;
  overflow-y: auto;
}
.cat-item {
  padding: 17px 8px;
  font-size: var(--text-md);
  color: var(--ink-2);
  text-align: center;
  border-left: 3px solid transparent;
  transition: background var(--dur-fast), color var(--dur-fast);
}
.cat-item.active {
  background: var(--surface);
  color: var(--brand-600);
  font-weight: 600;
  border-left-color: var(--brand-500);
}
.product-list {
  flex: 1;
  background: var(--surface);
  height: 100%;
  overflow-y: auto;
  padding: 0 14px;
}
.cat-title {
  font-size: var(--text-sm);
  color: var(--ink-3);
  font-weight: 600;
  letter-spacing: 1px;
  padding: 14px 0 8px;
}
.product-card {
  display: flex;
  gap: 10px;
  padding-bottom: 16px;
}
.p-img {
  width: 78px;
  height: 78px;
  flex-shrink: 0;
}
.p-img .van-icon {
  font-size: 28px;
  color: var(--ink-4);
  line-height: 78px;
}
.p-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.p-name {
  font-size: var(--text-lg);
  font-weight: 600;
}
.p-desc {
  font-size: var(--text-xs);
  color: var(--ink-3);
  margin: 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.p-bottom {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.p-price {
  font-size: var(--text-2xl);
}
.yen {
  font-size: var(--text-sm);
  font-weight: 600;
  margin-right: 1px;
}

/* ---------- 步进按钮（圆形） ---------- */
.stepper {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--brand-500);
  color: #fff;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--dur-fast) var(--ease-spring);
}
.step-btn:active {
  transform: scale(0.88);
}
.step-num {
  min-width: 18px;
  text-align: center;
  font-size: var(--text-lg);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ---------- 底部结算栏 ---------- */
.cart-bar {
  padding-left: var(--gutter);
  border-top: 1px solid var(--hairline);
}
.cart-icon-wrap {
  margin-top: -28px;
}
.cart-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: var(--ink-3);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 4px solid var(--surface);
  box-shadow: var(--shadow-2);
  transition: background var(--dur-base);
}
.cart-icon.on {
  background: linear-gradient(135deg, #ff8a3d, #f2570a);
}
.cart-icon .van-icon {
  font-size: 24px;
  color: #fff;
}
.cart-total {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-left: 12px;
}
.total-price {
  font-size: var(--text-2xl);
}
.total-fee,
.total-empty {
  font-size: var(--text-xs);
  color: var(--ink-3);
}
.checkout-btn {
  width: 112px;
  height: 42px;
  margin-right: var(--gutter);
  font-weight: 600;
}

/* ---------- 已选弹层 ---------- */
.cart-popup {
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
}
.popup-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px var(--gutter) 10px;
  font-size: var(--text-xl);
  font-weight: 600;
}
.popup-head .clear {
  font-size: var(--text-sm);
  color: var(--ink-3);
  font-weight: 400;
  display: flex;
  align-items: center;
  gap: 3px;
}
.popup-list {
  max-height: 42vh;
  overflow-y: auto;
  padding: 0 var(--gutter);
}
.popup-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--hairline);
}
.popup-item:last-child {
  border-bottom: none;
}
.pi-name {
  font-size: var(--text-lg);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pi-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pi-price {
  font-size: var(--text-xl);
  margin-right: 4px;
}
</style>
