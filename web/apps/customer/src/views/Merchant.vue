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
      <van-image class="m-avatar" radius="8" fit="cover" :src="pickImage(merchant)">
        <template #loading><van-icon name="shop-o" /></template>
      </van-image>
      <div class="m-text">
        <div class="m-name">{{ merchant.name }}</div>
        <div class="m-sub">
          <van-rate :model-value="merchant.rating" readonly allow-half size="12" color="#ff6d1f" />
          <span>{{ merchant.rating != null ? `${merchant.rating} 分` : '暂无评分' }} · 配送费 ¥{{ merchant.deliveryFee }}</span>
        </div>
        <div class="m-sub">配送费 ¥{{ money(merchant.deliveryFee) }} · {{ merchant.address }}</div>
        <div class="m-tags">
          <van-tag plain type="warning" v-for="t in merchant.tags || []" :key="t">{{ t }}</van-tag>
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
            <van-image class="p-img" radius="6" fit="cover" :src="pickImage(p)" @click="router.push(`/product/${p.id}`)">
              <template #loading><van-icon name="goods-o" /></template>
            </van-image>
            <div class="p-info">
              <div class="p-name" @click="router.push(`/product/${p.id}`)">{{ p.name }}</div>
              <div class="p-desc">{{ p.description }}</div>
              <div class="p-bottom">
                <div class="p-price"><span>¥</span>{{ money(p.price) }}</div>
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
          <span class="total-price">¥{{ money(totalPrice) }}</span>
          <span class="total-fee">另需配送费 ¥{{ money(merchant?.deliveryFee) }}</span>
        </template>
        <span v-else class="total-empty">未选购商品</span>
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
            <span class="pi-price">¥{{ money(i.price * i.quantity) }}</span>
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
.m-head {
  display: flex;
  gap: 12px;
  background: #fff;
  padding: 12px 16px;
}
.m-avatar {
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}
.m-avatar .van-icon {
  font-size: 28px;
  color: #dcdee0;
  line-height: 64px;
}
.m-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.m-name {
  font-size: 18px;
  font-weight: 600;
}
.m-sub {
  font-size: 12px;
  color: #969799;
  display: flex;
  align-items: center;
  gap: 4px;
}
.m-tags {
  display: flex;
  gap: 4px;
}
.menu-wrap {
  display: flex;
  margin-top: 10px;
  min-height: calc(100vh - 210px);
}
.cat-nav {
  width: 88px;
  background: #f7f8fa;
  flex-shrink: 0;
}
.cat-item {
  padding: 16px 8px;
  font-size: 13px;
  color: #646566;
  text-align: center;
  border-left: 3px solid transparent;
}
.cat-item.active {
  background: #fff;
  color: #323233;
  font-weight: 600;
  border-left-color: #ff6d1f;
}
.product-list {
  flex: 1;
  background: #fff;
  height: calc(100vh - 210px);
  overflow-y: auto;
  padding: 0 12px;
}
.cat-title {
  font-size: 13px;
  color: #969799;
  padding: 14px 0 8px;
}
.product-card {
  display: flex;
  gap: 10px;
  padding-bottom: 14px;
}
.p-img {
  width: 76px;
  height: 76px;
  flex-shrink: 0;
}
.p-img .van-icon {
  font-size: 28px;
  color: #dcdee0;
  line-height: 76px;
}
.p-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.p-name {
  font-size: 15px;
  font-weight: 500;
}
.p-desc {
  font-size: 11px;
  color: #969799;
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
  color: #ff6d1f;
  font-size: 18px;
  font-weight: 600;
}
.p-price span {
  font-size: 12px;
}
.stepper {
  display: flex;
  align-items: center;
  gap: 8px;
}
.step-btn {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ff6d1f;
  color: #fff;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.step-btn.add {
  background: #ff6d1f;
}
.step-num {
  min-width: 18px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.cart-bar {
  padding-left: 16px;
}
.cart-icon-wrap {
  margin-top: -26px;
}
.cart-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #c8c9cc;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 4px solid #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  transition: background 0.2s;
}
.cart-icon.on {
  background: #ff6d1f;
}
.cart-icon .van-icon {
  font-size: 24px;
  color: #fff;
}
.cart-total {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-left: 10px;
}
.total-price {
  font-size: 18px;
  font-weight: 700;
  color: #323233;
}
.total-fee,
.total-empty {
  font-size: 11px;
  color: #969799;
}
.checkout-btn {
  width: 110px;
  height: 40px;
}
.cart-popup {
  padding-bottom: 20px;
}
.popup-head {
  display: flex;
  justify-content: space-between;
  padding: 16px;
  font-size: 15px;
  font-weight: 600;
}
.popup-head .clear {
  font-size: 12px;
  color: #969799;
  font-weight: 400;
  display: flex;
  align-items: center;
  gap: 2px;
}
.popup-list {
  max-height: 40vh;
  overflow-y: auto;
  padding: 0 16px;
}
.popup-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}
.pi-name {
  font-size: 14px;
  flex: 1;
  min-width: 0;
}
.pi-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pi-price {
  color: #ff6d1f;
  font-weight: 600;
  margin-right: 6px;
}
</style>
