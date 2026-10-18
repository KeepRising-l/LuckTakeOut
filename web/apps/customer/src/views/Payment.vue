<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showLoadingToast, showToast } from 'vant'
import { orderApi, money, ORDER_STATUS } from '@/api'
import type { Order } from '@/api'

const route = useRoute()
const router = useRouter()

const order = ref<Order>()
const paying = ref(false)
const paid = ref(false)

const PENDING_PAY = 10

async function load() {
  try {
    order.value = await orderApi.detail(String(route.params.id))
    if (Number(order.value.status) !== PENDING_PAY) paid.value = true
  } catch (e) {
    showToast((e as Error).message)
  }
}

async function pay() {
  if (!order.value) return
  paying.value = true
  showLoadingToast({ message: '支付中...', forbidClick: true, duration: 0 })
  try {
    await orderApi.pay(order.value.id)
    paid.value = true
    showToast('支付成功')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    closeToast()
    paying.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="payment-page">
    <van-nav-bar title="收银台" left-arrow @click-left="router.back()" />

    <div class="panel">
      <template v-if="!paid">
        <div class="label">应付金额</div>
        <div class="amount"><span>¥</span>{{ money(order?.actualAmount) }}</div>
        <div class="order-no" v-if="order">订单号：{{ order.orderNo }}</div>
        <van-cell-group inset class="pay-channel">
          <van-cell title="模拟支付渠道" icon="balance-o" value="余额支付" />
        </van-cell-group>
        <van-button type="danger" block round size="large" class="pay-btn" :loading="paying" @click="pay">
          模拟支付 ¥{{ money(order?.actualAmount) }}
        </van-button>
      </template>
      <template v-else>
        <div class="success-icon"><van-icon name="checked" /></div>
        <div class="success-text">支付成功</div>
        <div class="amount small">¥{{ money(order?.actualAmount) }}</div>
        <van-button type="primary" block round size="large" class="pay-btn" @click="router.replace(`/orders/${order?.id}`)">
          查看订单
        </van-button>
        <van-button block round size="large" plain class="home-btn" @click="router.replace('/')">返回首页</van-button>
      </template>
    </div>

    <div v-if="order" class="status-hint">当前状态：{{ ORDER_STATUS[order.status] || order.status }}</div>
  </div>
</template>

<style scoped>
.payment-page {
  min-height: 100vh;
}
.panel {
  background: #fff;
  margin: 12px;
  border-radius: 12px;
  padding: 40px 24px 32px;
  text-align: center;
}
.label {
  font-size: 14px;
  color: #969799;
}
.amount {
  font-size: 44px;
  font-weight: 700;
  margin: 12px 0 4px;
}
.amount span {
  font-size: 22px;
}
.amount.small {
  font-size: 24px;
}
.order-no {
  font-size: 12px;
  color: #969799;
  margin-bottom: 24px;
}
.pay-channel {
  margin-bottom: 28px;
  text-align: left;
}
.pay-btn {
  background: #ff6d1f;
  border-color: #ff6d1f;
}
.home-btn {
  margin-top: 12px;
}
.success-icon .van-icon {
  font-size: 64px;
  color: #07c160;
}
.success-text {
  font-size: 20px;
  font-weight: 600;
  margin: 12px 0 4px;
}
.status-hint {
  text-align: center;
  font-size: 12px;
  color: #969799;
}
</style>
