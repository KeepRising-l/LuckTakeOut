<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showLoadingToast, showToast } from 'vant'
import { addressApi, merchantApi, orderApi, money, pickImage } from '@/api'
import { useCartStore } from '@/stores/cart'
import type { Address, Merchant } from '@/api'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()

const merchantId = Number(route.query.merchantId)
const merchant = ref<Merchant>()
const addresses = ref<Address[]>([])
const selectedAddress = ref<Address>()
const showAddrPicker = ref(false)
const remark = ref('')
const submitting = ref(false)
const showNoAddr = ref(false)

/** 结算明细：直接来自购物车中该商家勾选的商品 */
const items = computed(() => {
  const mc = cart.merchantCart(merchantId)
  return mc ? mc.items.filter((i) => i.checked) : []
})
const productTotal = computed(() => items.value.reduce((n, i) => n + i.price * i.quantity, 0))
const deliveryFee = computed(() => merchant.value?.deliveryFee ?? 0)
const totalAmount = computed(() => productTotal.value + deliveryFee.value)

async function load() {
  if (!items.value.length) {
    showToast('请先选择商品')
    router.replace('/cart')
    return
  }
  showLoadingToast({ message: '加载中...', forbidClick: true, duration: 0 })
  try {
    merchant.value = await merchantApi.detail(merchantId)
    addresses.value = await addressApi.list()
    const def = addresses.value.find((a) => a.isDefault) || addresses.value[0]
    if (def) selectedAddress.value = def
    else showNoAddr.value = true
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    closeToast()
  }
}

function chooseAddress(a: Address) {
  selectedAddress.value = a
  showAddrPicker.value = false
}

async function submit() {
  if (!selectedAddress.value) {
    showAddrPicker.value = true
    return showToast('请选择收货地址')
  }
  if (!items.value.length) return showToast('没有可结算的商品')
  submitting.value = true
  try {
    const order = await orderApi.create({
      merchantId,
      items: items.value.map((i) => ({ productId: i.productId, quantity: i.quantity })),
      deliveryFee: deliveryFee.value,
      remark: remark.value,
      addressId: selectedAddress.value.id,
    })
    cart.removeItems(merchantId, items.value.map((i) => i.productId))
    showToast('下单成功')
    router.replace(`/payment/${order.id}`)
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="checkout-page">
    <van-nav-bar title="确认订单" left-arrow @click-left="router.back()" />

    <div class="addr-card" @click="addresses.length ? (showAddrPicker = true) : router.push('/addresses')">
      <div class="addr-icon">
        <van-icon name="location-o" />
      </div>
      <template v-if="selectedAddress">
        <div class="addr-body">
          <div class="addr-line1">{{ selectedAddress.name }} <span class="addr-phone">{{ selectedAddress.phone }}</span></div>
          <div class="addr-line2">
            {{ selectedAddress.province }}{{ selectedAddress.city }}{{ selectedAddress.district }}{{ selectedAddress.detail }}
          </div>
        </div>
      </template>
      <template v-else>
        <div class="addr-body add-addr">请添加收货地址</div>
      </template>
      <van-icon name="arrow" class="addr-arrow" />
    </div>

    <div class="goods-card">
      <div class="g-merchant"><van-icon name="shop-o" /> {{ merchant?.name || '商家' }}</div>
      <div v-for="i in items" :key="i.productId" class="g-item">
        <van-image class="g-img" radius="8" fit="cover" :src="i.image">
          <template #loading><van-icon name="goods-o" /></template>
          <template #error><van-icon name="goods-o" /></template>
        </van-image>
        <div class="g-info">
          <div class="g-name">{{ i.name }}</div>
          <div class="g-qty">x{{ i.quantity }}</div>
        </div>
        <span class="g-price tk-price">¥{{ money(i.price * i.quantity) }}</span>
      </div>
      <div class="fee-row"><span>商品金额</span><span>¥{{ money(productTotal) }}</span></div>
      <div class="fee-row"><span>配送费</span><span>¥{{ money(deliveryFee) }}</span></div>
      <div class="fee-row total"><span>合计</span><span class="t-price tk-price">¥{{ money(totalAmount) }}</span></div>
    </div>

    <div class="remark-card">
      <van-field
        v-model="remark"
        label="备注"
        type="textarea"
        placeholder="口味偏好、放门口等（选填）"
        rows="1"
        autosize
        maxlength="100"
      />
    </div>

    <van-action-bar safe-area-inset-bottom class="tk-action-bar">
      <div class="bar-total">
        合计 <em>¥{{ money(totalAmount) }}</em>
      </div>
      <van-button type="primary" round class="submit-btn" :loading="submitting" @click="submit">提交订单</van-button>
    </van-action-bar>

    <van-popup v-model:show="showAddrPicker" position="bottom" round :style="{ maxHeight: '70vh' }">
      <div class="picker-head">选择收货地址</div>
      <div class="picker-list">
        <div
          v-for="a in addresses"
          :key="a.id"
          class="picker-item"
          :class="{ on: selectedAddress?.id === a.id }"
          @click="chooseAddress(a)"
        >
          <div>
            <div class="pi-line1">{{ a.name }} {{ a.phone }} <van-tag v-if="a.isDefault" type="warning" round>默认</van-tag></div>
            <div class="pi-line2">{{ a.province }}{{ a.city }}{{ a.district }}{{ a.detail }}</div>
          </div>
          <van-icon v-if="selectedAddress?.id === a.id" name="success" class="pick-ok" />
        </div>
        <van-button block plain type="primary" class="picker-add" round @click="router.push('/addresses')">管理地址</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.checkout-page {
  min-height: 100vh;
  padding-bottom: 70px;
}

/* ---------- 地址卡 ---------- */
.addr-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface);
  margin: 12px var(--gutter);
  border-radius: var(--radius-lg);
  padding: 14px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
}
.addr-icon {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--brand-50);
  color: var(--brand-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  flex-shrink: 0;
}
.addr-body {
  flex: 1;
  min-width: 0;
}
.addr-line1 {
  font-size: var(--text-xl);
  font-weight: 600;
}
.addr-phone {
  font-weight: 400;
  color: var(--ink-2);
  margin-left: 4px;
}
.addr-line2 {
  font-size: var(--text-sm);
  color: var(--ink-3);
  margin-top: 4px;
  line-height: 1.45;
}
.addr-arrow {
  color: var(--ink-4);
}
.add-addr {
  color: var(--ink-3);
}

/* ---------- 商品卡 ---------- */
.goods-card {
  background: var(--surface);
  margin: 0 var(--gutter) 12px;
  border-radius: var(--radius-lg);
  padding: 4px 14px 14px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
}
.g-merchant {
  font-size: var(--text-xl);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 0;
  border-bottom: 1px solid var(--hairline);
}
.g-merchant .van-icon {
  color: var(--brand-500);
}
.g-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--hairline);
}
.g-img {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
}
.g-img .van-icon {
  font-size: 20px;
  color: var(--ink-4);
  line-height: 52px;
}
.g-info {
  flex: 1;
  min-width: 0;
}
.g-name {
  font-size: var(--text-lg);
}
.g-qty {
  font-size: var(--text-sm);
  color: var(--ink-3);
  margin-top: 4px;
}
.g-price {
  font-weight: 700;
  font-size: var(--text-xl);
}
.fee-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-md);
  color: var(--ink-2);
  padding-top: 10px;
}
.fee-row.total {
  border-top: 1px solid var(--hairline);
  margin-top: 8px;
  padding-top: 12px;
  font-size: var(--text-lg);
  color: var(--ink-1);
  font-weight: 600;
}
.t-price {
  font-size: var(--text-3xl);
}

/* ---------- 备注 ---------- */
.remark-card {
  background: var(--surface);
  margin: 0 var(--gutter);
  border-radius: var(--radius-lg);
  border: 1px solid var(--hairline);
  overflow: hidden;
}

/* ---------- 底部栏 ---------- */
.tk-action-bar {
  border-top: 1px solid var(--hairline);
}
.bar-total {
  flex: 1;
  padding-left: var(--gutter);
  font-size: var(--text-md);
  color: var(--ink-2);
}
.bar-total em {
  color: var(--brand-600);
  font-style: normal;
  font-size: var(--text-3xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin-left: 4px;
}
.submit-btn {
  width: 120px;
  height: 42px;
  margin-right: var(--gutter);
  font-weight: 600;
}

/* ---------- 地址选择弹层 ---------- */
.picker-head {
  padding: 16px;
  font-size: var(--text-xl);
  font-weight: 600;
  text-align: center;
  border-bottom: 1px solid var(--hairline);
}
.picker-list {
  padding: 4px 16px calc(20px + env(safe-area-inset-bottom));
  overflow-y: auto;
}
.picker-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 13px 0;
  border-bottom: 1px solid var(--hairline);
}
.pick-ok {
  color: var(--brand-500);
  font-size: 20px;
}
.picker-item.on .pi-line1 {
  color: var(--brand-600);
}
.pi-line1 {
  font-size: var(--text-lg);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pi-line2 {
  font-size: var(--text-sm);
  color: var(--ink-3);
  margin-top: 4px;
}
.picker-add {
  margin-top: 16px;
}
</style>
