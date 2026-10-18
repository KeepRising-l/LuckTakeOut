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
        <div class="name serif">{{ product.name }}</div>
        <div class="desc">{{ product.description }}</div>
        <div class="tags" v-if="product.tags?.length">
          <span v-for="t in product.tags" :key="t" class="tag">{{ t }}</span>
        </div>
        <div class="price-card">
          <div class="price-row">
            <span class="price tk-price"><span class="yen">¥</span>{{ money(product.price) }}</span>
            <span class="stock">库存 {{ product.stock }}</span>
          </div>
          <div class="qty-row">
            <span>购买数量</span>
            <van-stepper v-model="quantity" min="1" :max="product.stock || 99" />
          </div>
        </div>
        <div v-if="merchant" class="merchant-line" @click="router.push(`/shop/${merchant.id}`)">
          <div class="ml-shop">
            <van-icon name="shop-o" />
            <span>{{ merchant.name }}</span>
          </div>
          <span class="ml-go">进店 <van-icon name="arrow" /></span>
        </div>
      </div>
    </template>
    <van-empty v-else description="商品不存在" />

    <van-action-bar v-if="product" safe-area-inset-bottom class="tk-action-bar">
      <van-action-bar-icon icon="cart-o" text="购物车" :badge="cart.totalCount || ''" @click="router.push('/cart')" />
      <van-action-bar-button class="btn-cart" text="加入购物车" @click="addCart" />
      <van-action-bar-button class="btn-buy" text="立即购买" @click="buyNow" />
    </van-action-bar>
  </div>
</template>

<style scoped>
.product-page {
  min-height: 100vh;
  padding-bottom: 60px;
  background: var(--canvas);
}
.hero .van-icon {
  font-size: 60px;
  color: var(--ink-4);
  line-height: 280px;
}
.body {
  padding: 16px var(--gutter);
}
.name {
  font-size: var(--text-3xl);
  font-weight: 700;
}
.desc {
  font-size: var(--text-md);
  color: var(--ink-3);
  margin-top: 8px;
  line-height: 1.5;
}
.tags {
  display: flex;
  gap: 6px;
  margin-top: 12px;
}
.tag {
  font-size: var(--text-xs);
  color: var(--brand-700);
  background: var(--brand-50);
  border: 1px solid var(--brand-100);
  border-radius: var(--radius-sm);
  padding: 3px 8px;
}

/* ---------- 价格卡 ---------- */
.price-card {
  margin-top: 16px;
  background: var(--surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--hairline);
  padding: 16px;
}
.price-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.price {
  font-size: 32px;
}
.yen {
  font-size: var(--text-xl);
  font-weight: 600;
  margin-right: 2px;
}
.stock {
  font-size: var(--text-sm);
  color: var(--ink-3);
}
.qty-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--hairline);
  font-size: var(--text-lg);
}

/* ---------- 商家入口 ---------- */
.merchant-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 13px 14px;
  background: var(--surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--hairline);
  font-size: var(--text-lg);
}
.ml-shop {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}
.ml-shop .van-icon {
  color: var(--brand-500);
  font-size: 18px;
}
.ml-go {
  font-size: var(--text-sm);
  color: var(--brand-600);
}

/* ---------- 底部操作栏 ---------- */
.tk-action-bar {
  border-top: 1px solid var(--hairline);
}
.btn-cart {
  background: linear-gradient(135deg, #ffd9ac, #ffc498);
  color: var(--brand-800);
  font-weight: 600;
}
.btn-buy {
  background: linear-gradient(135deg, #ff8a3d, #f2570a);
  color: #fff;
  font-weight: 600;
}
</style>
