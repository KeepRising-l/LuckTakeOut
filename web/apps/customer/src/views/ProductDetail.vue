<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showLoadingToast, showToast } from 'vant'
import { merchantApi, productApi, pickImage, money } from '@/api'
import { useCartStore } from '@/stores/cart'
import type { Product, Merchant } from '@/api'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()

const productId = Number(route.params.id)
const product = ref<Product>()
const merchant = ref<Merchant>()
const quantity = ref(1)

// 商品详情接口不直接给商家信息；先查商品，再按商品 merchantId 查商家（如返回）
const merchantId = computed(() => (product.value as { merchantId?: number } | undefined)?.merchantId || 0)

const totalPrice = computed(() => (product.value ? product.value.price * quantity.value : 0))

async function load() {
  showLoadingToast({ message: '加载中...', forbidClick: true, duration: 0 })
  try {
    product.value = await productApi.detail(productId)
    if (merchantId.value) {
      try {
        merchant.value = await merchantApi.detail(merchantId.value)
      } catch {
        /* 商家信息失败不阻塞 */
      }
    }
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    closeToast()
  }
}

function addCart() {
  if (!product.value) return
  const m = merchant.value || {
    id: merchantId.value,
    name: '',
    deliveryFee: 0,
  }
  if (!m.id) return showToast('缺少商家信息')
  for (let k = 0; k < quantity.value; k++) cart.add(m, product.value)
  showToast('已加入购物车')
}

function buyNow() {
  if (!product.value) return
  const m = merchant.value || { id: merchantId.value, name: '', deliveryFee: 0 }
  if (!m.id) return showToast('缺少商家信息')
  for (let k = 0; k < quantity.value; k++) cart.add(m, product.value)
  router.push({ path: '/checkout', query: { merchantId: String(m.id) } })
}

onMounted(load)
</script>

<template>
  <div class="product-page">
    <van-nav-bar left-arrow @click-left="router.back()" />
    <template v-if="product">
      <van-image class="hero" width="100%" height="280" fit="cover" :src="pickImage(product)">
        <template #loading><van-icon name="goods-o" /></template>
      </van-image>
      <div class="body">
        <div class="name">{{ product.name }}</div>
        <div class="desc">{{ product.description }}</div>
        <div class="tags">
          <van-tag plain type="warning" v-for="t in product.tags || []" :key="t">{{ t }}</van-tag>
        </div>
        <div class="price-row">
          <span class="price"><span>¥</span>{{ money(product.price) }}</span>
          <span class="stock">库存 {{ product.stock }}</span>
        </div>
        <div class="qty-row">
          <span>购买数量</span>
          <van-stepper v-model="quantity" min="1" :max="product.stock || 99" />
        </div>
        <div v-if="merchant" class="merchant-line" @click="router.push(`/shop/${merchant.id}`)">
          <van-icon name="shop-o" />
          <span>{{ merchant.name }}</span>
          <van-icon name="arrow" />
        </div>
      </div>
    </template>
    <van-empty v-else description="商品不存在" />

    <van-action-bar v-if="product" safe-area-inset-bottom>
      <van-action-bar-icon icon="cart-o" text="购物车" :badge="cart.totalCount || ''" @click="router.push('/cart')" />
      <van-action-bar-button type="warning" text="加入购物车" @click="addCart" />
      <van-action-bar-button type="danger" text="立即购买" @click="buyNow" />
    </van-action-bar>
  </div>
</template>

<style scoped>
.product-page {
  min-height: 100vh;
  padding-bottom: 60px;
  background: #fff;
}
.hero .van-icon {
  font-size: 60px;
  color: #dcdee0;
  line-height: 280px;
}
.body {
  padding: 16px;
}
.name {
  font-size: 20px;
  font-weight: 600;
}
.desc {
  font-size: 13px;
  color: #969799;
  margin-top: 8px;
}
.tags {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}
.price-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-top: 16px;
}
.price {
  color: #ff6d1f;
  font-size: 26px;
  font-weight: 700;
}
.price span {
  font-size: 14px;
}
.stock {
  font-size: 12px;
  color: #969799;
}
.qty-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  font-size: 14px;
}
.merchant-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  padding: 12px;
  background: #f7f8fa;
  border-radius: 8px;
  font-size: 14px;
}
.merchant-line .van-icon:last-child {
  margin-left: auto;
  color: #c8c9cc;
}
</style>
