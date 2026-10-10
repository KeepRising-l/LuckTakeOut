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
      <template v-if="selectedAddress">
        <van-icon name="location-o" class="loc" />
        <div class="addr-body">
          <div class="addr-line1">{{ selectedAddress.name }} {{ selectedAddress.phone }}</div>
          <div class="addr-line2">
            {{ selectedAddress.province }}{{ selectedAddress.city }}{{ selectedAddress.district }}{{ selectedAddress.detail }}
          </div>
        </div>
        <van-icon name="arrow" />
      </template>
      <template v-else>
        <van-icon name="add-o" class="loc" />
        <div class="addr-body add-addr">请添加收货地址</div>
        <van-icon name="arrow" />
      </template>
    </div>

    <div class="goods-card">
      <div class="g-merchant"><van-icon name="shop-o" /> {{ merchant?.name || '商家' }}</div>
      <div v-for="i in items" :key="i.productId" class="g-item">
        <van-image class="g-img" radius="6" fit="cover" :src="i.image">
          <template #loading><van-icon name="goods-o" /></template>
          <template #error><van-icon name="goods-o" /></template>
        </van-image>
        <div class="g-info">
          <div class="g-name">{{ i.name }}</div>
          <div class="g-qty">x{{ i.quantity }}</div>
        </div>
        <span class="g-price">¥{{ money(i.price * i.quantity) }}</span>
      </div>
      <div class="fee-row"><span>商品金额</span><span>¥{{ money(productTotal) }}</span></div>
      <div class="fee-row"><span>配送费</span><span>¥{{ money(deliveryFee) }}</span></div>
      <div class="fee-row total"><span>合计</span><span class="t-price">¥{{ money(totalAmount) }}</span></div>
    </div>

    <van-field
      v-model="remark"
      label="备注"
      type="textarea"
      placeholder="口味偏好、放门口等（选填）"
      rows="1"
      autosize
      maxlength="100"
    />

    <van-action-bar safe-area-inset-bottom>
      <div class="bar-total">
        合计 <em>¥{{ money(totalAmount) }}</em>
      </div>
      <van-button type="danger" round class="submit-btn" :loading="submitting" @click="submit">提交订单</van-button>
    </van-action-bar>

    <van-popup v-model:show="showAddrPicker" position="bottom" round style="max-height: 70vh">
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
            <div class="pi-line1">{{ a.name }} {{ a.phone }} <van-tag v-if="a.isDefault" type="warning">默认</van-tag></div>
            <div class="pi-line2">{{ a.province }}{{ a.city }}{{ a.district }}{{ a.detail }}</div>
          </div>
          <van-icon v-if="selectedAddress?.id === a.id" name="success" color="#ff6d1f" />
        </div>
        <van-button block plain type="primary" class="picker-add" @click="router.push('/addresses')">管理地址</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.checkout-page {
  min-height: 100vh;
  padding-bottom: 70px;
}
.addr-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  margin: 12px;
  border-radius: 10px;
  padding: 16px 12px;
}
.addr-card .loc {
  color: #ff6d1f;
  font-size: 20px;
}
.addr-body {
  flex: 1;
  min-width: 0;
}
.add-addr {
  color: #969799;
}
.addr-line1 {
  font-size: 15px;
  font-weight: 600;
}
.addr-line2 {
  font-size: 12px;
  color: #969799;
  margin-top: 4px;
}
.goods-card {
  background: #fff;
  margin: 0 12px 12px;
  border-radius: 10px;
  padding: 12px;
}
.g-merchant {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  padding-bottom: 10px;
}
.g-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}
.g-img {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
}
.g-img .van-icon {
  font-size: 20px;
  color: #dcdee0;
  line-height: 52px;
}
.g-info {
  flex: 1;
  min-width: 0;
}
.g-name {
  font-size: 14px;
}
.g-qty {
  font-size: 12px;
  color: #969799;
  margin-top: 4px;
}
.g-price {
  font-weight: 600;
}
.fee-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #646566;
  padding-top: 10px;
  margin-top: 4px;
}
.fee-row.total {
  border-top: 1px solid #f2f3f5;
  margin-top: 10px;
  font-size: 14px;
  color: #323233;
  font-weight: 600;
}
.t-price {
  color: #ff6d1f;
  font-size: 18px;
}
.bar-total {
  flex: 1;
  padding-left: 16px;
  font-size: 14px;
}
.bar-total em {
  color: #ff6d1f;
  font-style: normal;
  font-size: 20px;
  font-weight: 700;
}
.submit-btn {
  width: 130px;
}
.picker-head {
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
}
.picker-list {
  padding: 0 16px 20px;
  overflow-y: auto;
}
.picker-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 0;
  border-bottom: 1px solid #f2f3f5;
}
.picker-item.on .pi-line1 {
  color: #ff6d1f;
}
.pi-line1 {
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pi-line2 {
  font-size: 12px;
  color: #969799;
  margin-top: 4px;
}
.picker-add {
  margin-top: 16px;
}
</style>
