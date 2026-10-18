<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NavBar,
  showConfirmDialog,
  showSuccessToast,
  showFailToast,
  showToast,
} from 'vant'
import { money, datetime } from '@takeout/shared'
import { api, type DeliveryTask } from '@/api'

const route = useRoute()
const router = useRouter()

const task = ref<DeliveryTask | null>(null)
const loading = ref(true)
const acting = ref(false)

const statusText: Record<string, string> = {
  pending: '待抢单',
  accepted: '已接单',
  delivering: '配送中',
  completed: '已完成',
}

const stepActive = computed(() => {
  switch (task.value?.status) {
    case 'accepted':
      return 1
    case 'delivering':
      return 2
    case 'completed':
      return 3
    default:
      return 0
  }
})

const itemsTotal = computed(() =>
  (task.value?.items || []).reduce((s, i) => s + Number(i.price) * Number(i.quantity), 0),
)

async function load() {
  loading.value = true
  try {
    task.value = await api.getTask(route.params.id as string)
  } catch (e) {
    showToast((e as Error).message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function accept() {
  if (!task.value || acting.value) return
  try {
    await showConfirmDialog({
      title: '确认接单',
      message: `商家：${task.value.merchantName}\n配送费：¥${money(task.value.deliveryFee)}`,
      confirmButtonText: '确认接单',
    })
  } catch {
    return
  }
  acting.value = true
  try {
    await api.acceptTask(task.value.id)
    showSuccessToast('接单成功')
    await load()
  } catch (e) {
    showFailToast((e as Error).message || '接单失败')
  } finally {
    acting.value = false
  }
}

async function finish() {
  if (!task.value || acting.value) return
  try {
    await showConfirmDialog({
      title: '确认送达',
      message: `订单 ${task.value.orderNo} 是否已送达客户？`,
    })
  } catch {
    return
  }
  acting.value = true
  try {
    await api.updateStatus(task.value.id, 6)
    showSuccessToast('配送完成')
    await load()
  } catch (e) {
    showFailToast((e as Error).message || '操作失败')
  } finally {
    acting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="detail-page">
    <van-nav-bar
      title="任务详情"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" class="detail-loading" size="24" vertical>加载中...</van-loading>

    <template v-else-if="task">
      <!-- 状态步骤条 -->
      <div class="detail-section">
        <van-steps :active="stepActive" active-color="#1989fa" inactive-color="#c8c9cc">
          <van-step>已接单</van-step>
          <van-step>取餐</van-step>
          <van-step>配送</van-step>
          <van-step>送达</van-step>
        </van-steps>
        <div class="detail-status-row">
          <van-tag :type="task.status === 'completed' ? 'success' : 'primary'" size="large">
            {{ statusText[task.status] }}
          </van-tag>
          <span class="detail-order-no">订单号 {{ task.orderNo }}</span>
        </div>
      </div>

      <!-- 商家 / 地址 / 联系人 -->
      <div class="detail-section">
        <div class="detail-row">
          <div class="detail-row-icon shop">
            <van-icon name="shop-o" />
          </div>
          <div class="detail-row-body">
            <div class="detail-row-title">{{ task.merchantName }}</div>
            <div class="detail-row-sub">下单时间 {{ datetime(task.createTime) }}</div>
          </div>
        </div>
        <div class="detail-row">
          <div class="detail-row-icon location">
            <van-icon name="location-o" />
          </div>
          <div class="detail-row-body">
            <div class="detail-row-title">{{ task.deliveryAddress }}</div>
            <div class="detail-row-sub">配送费 ¥{{ money(task.deliveryFee) }}</div>
          </div>
        </div>
        <div class="detail-row">
          <div class="detail-row-icon contact">
            <van-icon name="contact-o" />
          </div>
          <div class="detail-row-body">
            <div class="detail-row-title">{{ task.contactName }}</div>
            <a class="detail-tel" :href="`tel:${task.contactPhone}`">
              <van-icon name="phone-o" />
              {{ task.contactPhone }}
            </a>
          </div>
        </div>
      </div>

      <!-- 商品清单 -->
      <div class="detail-section">
        <div class="detail-section-title">商品清单</div>
        <div v-for="(item, idx) in task.items" :key="idx" class="goods-item">
          <span class="goods-name">{{ item.name }}</span>
          <span class="goods-qty">x{{ item.quantity }}</span>
          <span class="goods-price">¥{{ money(item.price) }}</span>
        </div>
        <div class="goods-summary">
          <span>商品合计</span>
          <span>¥{{ money(itemsTotal) }}</span>
        </div>
        <div class="goods-summary goods-fee">
          <span>配送费</span>
          <span class="fee-value">¥{{ money(task.deliveryFee) }}</span>
        </div>
        <div class="goods-summary goods-fee">
          <span>顾客实付</span>
          <span class="fee-value">¥{{ money(task.totalAmount) }}</span>
        </div>
      </div>

      <div class="detail-placeholder"></div>

      <!-- 底部操作 -->
      <div class="detail-footer safe-bottom">
        <template v-if="task.status === 'pending'">
          <span class="footer-fee">配送费 ¥{{ money(task.deliveryFee) }}</span>
          <van-button type="primary" round :loading="acting" @click="accept">接单</van-button>
        </template>
        <template v-else-if="task.status === 'delivering'">
          <span class="footer-tip">配送中，请尽快送达</span>
          <van-button type="primary" round :loading="acting" @click="finish">确认送达</van-button>
        </template>
        <template v-else>
          <span class="footer-tip done">本单已完成，配送费 ¥{{ money(task.deliveryFee) }}</span>
        </template>
      </div>
    </template>

    <van-empty v-else description="任务不存在或已删除" />
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding-bottom: 80px;
}

.detail-loading {
  padding: 80px 0;
}

.detail-section {
  margin: 12px 12px 0;
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.detail-section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}

.detail-status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px 0;
}

.detail-order-no {
  font-size: 12px;
  color: #969799;
}

.detail-row {
  display: flex;
  gap: 10px;
  padding: 8px 0;
}

.detail-row + .detail-row {
  border-top: 1px solid #f5f6f7;
}

.detail-row-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.detail-row-icon.shop {
  background: #fff7f0;
  color: #ff976a;
}

.detail-row-icon.location {
  background: #eef6ff;
  color: #1989fa;
}

.detail-row-icon.contact {
  background: #f0f9eb;
  color: #07c160;
}

.detail-row-body {
  flex: 1;
  min-width: 0;
}

.detail-row-title {
  font-size: 14px;
  font-weight: 500;
  color: #323233;
  word-break: break-all;
}

.detail-row-sub {
  margin-top: 3px;
  font-size: 12px;
  color: #969799;
}

.detail-tel {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 5px;
  font-size: 13px;
  color: #1989fa;
  text-decoration: none;
}

.goods-item {
  display: flex;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  color: #323233;
}

.goods-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.goods-qty {
  color: #969799;
  margin: 0 14px;
}

.goods-price {
  color: #323233;
}

.goods-summary {
  display: flex;
  justify-content: space-between;
  padding-top: 10px;
  margin-top: 4px;
  border-top: 1px dashed #ebedf0;
  font-size: 13px;
  color: #646566;
}

.goods-fee .fee-value {
  color: #ee0a24;
  font-weight: 600;
}

.detail-placeholder {
  height: 12px;
}

.detail-footer {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  width: 100%;
  max-width: 750px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  z-index: 10;
}

.safe-bottom {
  padding-bottom: calc(10px + env(safe-area-inset-bottom));
}

.footer-fee {
  font-size: 16px;
  font-weight: 700;
  color: #ee0a24;
}

.footer-tip {
  font-size: 13px;
  color: #646566;
}

.footer-tip.done {
  color: #07c160;
}

.detail-footer :deep(.van-button) {
  min-width: 150px;
}
</style>
