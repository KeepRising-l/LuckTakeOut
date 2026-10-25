<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showConfirmDialog, showLoadingToast, showToast } from 'vant'
import { orderApi, ORDER_STATUS, money, datetime } from '@/api'
import type { Order } from '@/api'

const route = useRoute()
const router = useRouter()

const order = ref<Order>()
const showReview = ref(false)
const rating = ref(5)
const content = ref('')
const submitting = ref(false)
const showRefund = ref(false)
const refundReason = ref('')
const refunding = ref(false)

const orderId = String(route.params.id)

/** 状态步骤条：10 下单 → 20 支付 → 30 接单 → 40 配送 → 50 完成 */
const stepIndex = computed(() => {
  const s = order.value?.status
  if (s === 10) return 0
  if (s === 20) return 1
  if (s === 30) return 2
  if (s === 40) return 3
  if (s === 50) return 4
  return -1
})

/** 已支付/待接单可申请退款 */
const canApplyRefund = computed(() => [20, 30].includes(order.value?.status ?? 0))

async function load() {
  showLoadingToast({ message: '加载中...', forbidClick: true, duration: 0 })
  try {
    order.value = await orderApi.detail(orderId)
    if (route.query.review === '1' && order.value.status === 50) showReview.value = true
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

async function submitRefund() {
  if (!refundReason.value.trim()) return showToast('请填写退款原因')
  refunding.value = true
  try {
    await orderApi.refundApply(orderId, refundReason.value.trim())
    showToast('退款申请已提交，等待商家审核')
    showRefund.value = false
    refundReason.value = ''
    load()
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    refunding.value = false
  }
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
        <template v-if="order.status === 60">
          <div class="status-big cancel"><van-icon name="close" /> 已取消</div>
        </template>
        <template v-else-if="order.status === 70">
          <div class="status-big refunding"><van-icon name="clock-o" /> 退款审核中</div>
        </template>
        <template v-else-if="order.status === 80">
          <div class="status-big refunded"><van-icon name="passed" /> 已退款</div>
        </template>
        <template v-else>
          <van-steps :active="stepIndex" active-color="var(--brand-500)" inactive-color="var(--hairline-strong)">
            <van-step>提交订单</van-step>
            <van-step>支付完成</van-step>
            <van-step>商家接单</van-step>
            <van-step>配送中</van-step>
            <van-step>已完成</van-step>
          </van-steps>
        </template>
        <div class="status-text">{{ ORDER_STATUS[order.status] || order.status }} · {{ datetime(order.createTime) }}</div>
      </div>

      <!-- 退款被拒提示 -->
      <div class="refund-notice" v-if="order.refundStatus === 30">
        <van-icon name="warning-o" />
        <span>上一次退款申请被商家拒绝{{ order.refundRemark ? `：${order.refundRemark}` : '' }}</span>
      </div>

      <!-- 地址 -->
      <div class="addr-panel" v-if="order.address">
        <div class="addr-icon">
          <van-icon name="location-o" />
        </div>
        <span>{{ order.address }}</span>
      </div>

      <!-- 商品 -->
      <div class="goods-panel">
        <div class="g-merchant"><van-icon name="shop-o" /> {{ order.merchantName }}</div>
        <div v-for="i in order.items" :key="i.productId" class="g-item">
          <div class="g-name">{{ i.productName }}</div>
          <div class="g-right">x{{ i.quantity }} <span class="g-price tk-price">¥{{ money(i.amount) }}</span></div>
        </div>
        <div class="fee-row"><span>商品金额</span><span>¥{{ money(order.productAmount) }}</span></div>
        <div class="fee-row"><span>配送费</span><span>¥{{ money(order.deliveryFee) }}</span></div>
        <div class="fee-row" v-if="order.discountAmount"><span>优惠</span><span>-¥{{ money(order.discountAmount) }}</span></div>
        <div class="fee-row total"><span>实付</span><span class="t-price tk-price">¥{{ money(order.actualAmount) }}</span></div>
      </div>

      <!-- 信息 -->
      <van-cell-group inset class="info-panel">
        <van-cell title="订单编号" :value="order.orderNo" />
        <van-cell title="下单时间" :value="datetime(order.createTime)" />
        <van-cell v-if="order.remark" title="备注" :value="order.remark" />
      </van-cell-group>

      <!-- 操作 -->
      <div class="action-bar">
        <van-button v-if="order.status === 10" plain round type="danger" @click="cancel">取消订单</van-button>
        <van-button v-if="order.status === 10" round type="primary" @click="pay">去支付</van-button>
        <van-button v-if="canApplyRefund" plain round type="danger" @click="showRefund = true">申请退款</van-button>
        <van-button v-if="order.status === 50" round type="primary" @click="showReview = true">评价订单</van-button>
      </div>
    </template>
    <van-empty v-else description="订单不存在" />

    <!-- 申请退款 -->
    <van-popup v-model:show="showRefund" position="bottom" round>
      <div class="review-panel">
        <div class="rv-title serif">申请退款</div>
        <p class="refund-amount">退款金额：<span class="tk-price">¥{{ money(order?.actualAmount ?? 0) }}</span>（全额）</p>
        <van-field
          v-model="refundReason"
          type="textarea"
          rows="3"
          maxlength="200"
          show-word-limit
          placeholder="请填写退款原因，方便商家处理"
          class="rv-field"
        />
        <van-button type="danger" block round :loading="refunding" @click="submitRefund">提交申请</van-button>
      </div>
    </van-popup>

    <van-popup v-model:show="showReview" position="bottom" round>
      <div class="review-panel">
        <div class="rv-title serif">评价订单</div>
        <div class="rv-rate-label">{{ rating }}.0 分</div>
        <van-rate v-model="rating" size="28" />
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
  background: var(--canvas);
}
.status-panel {
  background: var(--surface);
  margin: 12px var(--gutter);
  border-radius: var(--radius-lg);
  padding: 20px 12px 14px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
}
.status-big {
  text-align: center;
  font-size: var(--text-3xl);
  font-weight: 600;
  color: var(--ink-3);
  padding: 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.status-text {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--ink-3);
  margin-top: 10px;
}
.status-big.refunding {
  color: var(--brand-600);
}
.status-big.refunded {
  color: var(--ink-2);
}
.refund-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 var(--gutter) 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--color-brand-soft, #fff4ec);
  color: var(--brand-600);
  font-size: var(--text-sm);
}
.refund-amount {
  font-size: var(--text-md);
  color: var(--ink-2);
  margin-bottom: 4px;
}
.addr-panel {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface);
  margin: 0 var(--gutter) 12px;
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  border: 1px solid var(--hairline);
  font-size: var(--text-lg);
}
.addr-icon {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--color-indigo-soft);
  color: var(--color-indigo);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}
.goods-panel,
.info-panel {
  background: var(--surface);
  margin: 0 var(--gutter) 12px;
  border-radius: var(--radius-lg);
  padding: 4px 14px 14px;
  border: 1px solid var(--hairline);
}
.info-panel {
  padding: 0;
  overflow: hidden;
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
  justify-content: space-between;
  font-size: var(--text-lg);
  padding: 9px 0;
  border-bottom: 1px dashed var(--hairline);
}
.g-right {
  color: var(--ink-2);
  font-size: var(--text-md);
}
.g-price {
  color: var(--ink-1);
  margin-left: 8px;
  font-size: var(--text-lg);
}
.fee-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-md);
  color: var(--ink-2);
  padding-top: 9px;
}
.fee-row.total {
  border-top: 1px solid var(--hairline);
  margin-top: 8px;
  padding-top: 11px;
  font-weight: 600;
  color: var(--ink-1);
  font-size: var(--text-lg);
}
.t-price {
  font-size: var(--text-2xl);
}
.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 var(--gutter);
}
.action-bar .van-button {
  padding: 0 24px;
  font-weight: 500;
}
.review-panel {
  padding: 22px 16px calc(28px + env(safe-area-inset-bottom));
  text-align: center;
}
.rv-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  margin-bottom: 6px;
  letter-spacing: 1px;
}
.rv-rate-label {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--brand-600);
  font-variant-numeric: tabular-nums;
  margin-bottom: 8px;
}
.rv-field {
  margin: 16px 0;
  background: var(--surface-2);
  border-radius: var(--radius-md);
}
</style>
