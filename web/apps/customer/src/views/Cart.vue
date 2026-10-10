<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { money, pickImage } from '@/api'
import { useCartStore } from '@/stores/cart'
import TabBar from '@/components/TabBar.vue'

const router = useRouter()
const cart = useCartStore()

const editingId = ref<number | null>(null)

const groups = computed(() => cart.carts)

function groupTotal(merchantId: number) {
  const mc = cart.merchantCart(merchantId)
  if (!mc) return 0
  return mc.items.filter((i) => i.checked).reduce((n, i) => n + i.price * i.quantity, 0)
}

function groupCheckedCount(merchantId: number) {
  const mc = cart.merchantCart(merchantId)
  if (!mc) return 0
  return mc.items.filter((i) => i.checked).reduce((n, i) => n + i.quantity, 0)
}

function groupAllChecked(merchantId: number) {
  const mc = cart.merchantCart(merchantId)
  if (!mc) return false
  return mc.items.length > 0 && mc.items.every((i) => i.checked)
}

function onToggleAll(merchantId: number) {
  cart.toggleAll(merchantId, !groupAllChecked(merchantId))
}

async function clearOne(merchantId: number) {
  await showConfirmDialog({ title: '提示', message: '清空该商家的购物车？' })
  cart.clearMerchant(merchantId)
}

function checkout(merchantId: number) {
  if (!groupCheckedCount(merchantId)) return showToast('请先勾选商品')
  editingId.value = null
  router.push({ path: '/checkout', query: { merchantId: String(merchantId) } })
}
</script>

<template>
  <div class="cart-page">
    <van-nav-bar title="购物车" />
    <template v-if="groups.length">
      <div v-for="g in groups" :key="g.merchantId" class="group">
        <div class="g-head">
          <van-checkbox
            :model-value="groupAllChecked(g.merchantId)"
            checked-color="#ff6d1f"
            @click.stop="onToggleAll(g.merchantId)"
          />
          <van-icon name="shop-o" />
          <span class="g-name">{{ g.merchantName }}</span>
          <van-icon name="delete-o" class="g-del" @click="clearOne(g.merchantId)" />
        </div>
        <div v-for="i in g.items" :key="i.productId" class="item">
          <van-checkbox
            :model-value="i.checked"
            checked-color="#ff6d1f"
            @click.stop="cart.toggleItem(g.merchantId, i.productId)"
          />
          <van-image class="i-img" radius="6" fit="cover" :src="i.image" @click="router.push(`/product/${i.productId}`)">
            <template #loading><van-icon name="goods-o" /></template>
            <template #error><van-icon name="goods-o" /></template>
          </van-image>
          <div class="i-info">
            <div class="i-name" @click="router.push(`/product/${i.productId}`)">{{ i.name }}</div>
            <div class="i-bottom">
              <span class="i-price">¥{{ money(i.price) }}</span>
              <van-stepper
                :model-value="i.quantity"
                min="0"
                integer
                @change="(v: number) => cart.setCount(g.merchantId, i.productId, v)"
              />
            </div>
          </div>
        </div>
        <div class="g-foot">
          <span>已选 {{ groupCheckedCount(g.merchantId) }} 件，合计 <em>¥{{ money(groupTotal(g.merchantId)) }}</em></span>
          <van-button type="primary" size="small" round @click="checkout(g.merchantId)">去结算</van-button>
        </div>
      </div>
    </template>
    <van-empty v-else image="cart" description="购物车空空如也">
      <van-button type="primary" round size="small" @click="router.push('/')">去逛逛</van-button>
    </van-empty>
    <TabBar />
  </div>
</template>

<style scoped>
.cart-page {
  min-height: 100vh;
  padding-bottom: 70px;
}
.group {
  background: #fff;
  border-radius: 10px;
  margin: 12px;
  padding: 12px;
}
.g-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  padding-bottom: 10px;
  border-bottom: 1px solid #f2f3f5;
}
.g-name {
  flex: 1;
}
.g-del {
  color: #969799;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
}
.i-img {
  width: 68px;
  height: 68px;
  flex-shrink: 0;
}
.i-img .van-icon {
  font-size: 26px;
  color: #dcdee0;
  line-height: 68px;
}
.i-info {
  flex: 1;
  min-width: 0;
}
.i-name {
  font-size: 14px;
}
.i-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.i-price {
  color: #ff6d1f;
  font-weight: 600;
}
.g-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #f2f3f5;
  font-size: 13px;
  color: #646566;
}
.g-foot em {
  color: #ff6d1f;
  font-style: normal;
  font-weight: 700;
}
</style>
