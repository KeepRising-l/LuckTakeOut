<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showLoadingToast, showToast } from 'vant'
import { orderApi, ORDER_STATUS, money, datetime } from '@/api'
import type { Order } from '@/api'

const route = useRoute()
const router = useRouter()

const order = ref<Order>()
const showReview = ref(false)
const rating = ref(5)
const content = ref('')
const submitting = ref(false)

const orderId = String(route.params.id)

/** 状态步骤条：1 下单 → 2 支付 → 3 接单 → 5 配送 → 8 完成 */
const stepIndex = computed(() => {
  const s = order.value?.status
  if (s === 1) return 0
  if (s === 2) return 1
  if (s === 3) return 2
  if (s === 5) return 3
  if (s === 8) return 4
  return -1
})

async function load() {
  showLoadingToast({ message: '加载中...', forbidClick: true, duration: 0 })
  try {
    order.value = await orderApi.detail(orderId)
    if (route.query.review === '1' && order.value.status === 8) showReview.value = true
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    closeToast()
  }
}

async function cancel() {
  await showConfirmDialog({ title: '提示', message: '确定取消该订单吗？' })
  try {
    await orderApi.cancel(orderId)
    showToast('订单已取消')
    load()
  } catch (e) {
    showToast((e as Error).message)
  }
}

async function pay() {
  router.push(`/payment/${orderId}`)
}

async function submitReview() {
  if (!content.value.trim()) return showToast('请填写评价内容')
  submitting.value = true
  try {
    await orderApi.review(orderId, { rating: rating.value, content: content.value.trim() })
    showToast('评价成功')
    showReview.value = false
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="od-page">
    <van-nav-bar title="订单详情" left-arrow @click-left="router.back()" />

    <template v-if="order">
      <!-- 状态区 -->
      <div class="status-panel">
        <template v-if="order.status === 9">
          <div class="status-big cancel"><van-icon name="close" /> 已取消</div>
        </template>
        <template v-else>
          <van-steps :active="stepIndex" active-color="#ff6d1f" inactive-color="#c8c9cc">
            <van-step>提交订单</van-step>
            <van-step>支付完成</van-step>
            <van-step>商家接单</van-step>
            <van-step>配送中</van-step>
            <van-step>已完成</van-step>
          </van-steps>
        </template>
        <div class="status-text">当前状态：{{ ORDER_STATUS[order.status] || order.status }} · {{ datetime(order.createTime) }}</div>
      </div>

      <!-- 地址 -->
      <div class="addr-panel" v-if="order.address">
        <van-icon name="location-o" />
        <span>{{ order.address }}</span>
      </div>

      <!-- 商品 -->
      <div class="goods-panel">
        <div class="g-merchant"><van-icon name="shop-o" /> {{ order.merchantName }}</div>
        <div v-for="i in order.items" :key="i.productId" class="g-item">
          <div class="g-name">{{ i.productName }}</div>
          <div class="g-right">x{{ i.quantity }} <span class="g-price">¥{{ money(i.amount) }}</span></div>
        </div>
        <div class="fee-row"><span>商品金额</span><span>¥{{ money(order.productAmount) }}</span></div>
        <div class="fee-row"><span>配送费</span><span>¥{{ money(order.deliveryFee) }}</span></div>
        <div class="fee-row" v-if="order.discountAmount"><span>优惠</span><span>-¥{{ money(order.discountAmount) }}</span></div>
        <div class="fee-row total"><span>实付</span><span class="t-price">¥{{ money(order.actualAmount) }}</span></div>
      </div>

      <!-- 信息 -->
      <van-cell-group inset class="info-panel">
        <van-cell title="订单编号" :value="order.orderNo" />
        <van-cell title="下单时间" :value="datetime(order.createTime)" />
        <van-cell v-if="order.remark" title="备注" :value="order.remark" />
      </van-cell-group>

      <!-- 操作 -->
      <div class="action-bar">
        <van-button v-if="order.status === 1" plain round type="danger" @click="cancel">取消订单</van-button>
        <van-button v-if="order.status === 1" round type="danger" @click="pay">去支付</van-button>
        <van-button v-if="order.status === 8" round type="primary" @click="showReview = true">评价订单</van-button>
      </div>
    </template>
    <van-empty v-else description="订单不存在" />

    <van-popup v-model:show="showReview" position="bottom" round>
      <div class="review-panel">
        <div class="rv-title">评价订单</div>
        <van-rate v-model="rating" color="#ff6d1f" size="28" />
        <van-field
          v-model="content"
          type="textarea"
          rows="3"
          maxlength="200"
          show-word-limit
          placeholder="这一餐吃得还满意吗？说说感受吧～"
          class="rv-field"
        />
        <van-button type="primary" block round :loading="submitting" @click="submitReview">提交评价</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.od-page {
  min-height: 100vh;
  padding-bottom: 24px;
}
.status-panel {
  background: #fff;
  margin: 12px;
  border-radius: 10px;
  padding: 20px 8px 12px;
}
.status-big {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  color: #969799;
  padding: 8px 0;
}
.status-text {
  text-align: center;
  font-size: 12px;
  color: #969799;
  margin-top: 10px;
}
.addr-panel {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  margin: 0 12px 12px;
  border-radius: 10px;
  padding: 14px 12px;
  font-size: 14px;
}
.addr-panel .van-icon {
  color: #ff6d1f;
  font-size: 18px;
}
.goods-panel,
.info-panel {
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
  padding-bottom: 8px;
}
.g-item {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  padding: 6px 0;
}
.g-right {
  color: #969799;
}
.g-price {
  color: #323233;
  margin-left: 8px;
  font-weight: 600;
}
.fee-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #646566;
  padding-top: 8px;
}
.fee-row.total {
  border-top: 1px solid #f2f3f5;
  margin-top: 8px;
  padding-top: 10px;
  font-weight: 600;
  color: #323233;
}
.t-price {
  color: #ff6d1f;
  font-size: 17px;
}
.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 12px;
}
.action-bar .van-button {
  padding: 0 24px;
}
.review-panel {
  padding: 20px 16px 28px;
  text-align: center;
}
.rv-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 14px;
}
.rv-field {
  margin: 14px 0;
  background: #f7f8fa;
  border-radius: 8px;
}
</style>
