<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchOrders, fetchOrder, acceptOrder, cancelOrder, reviewRefund,
  ORDER_STATUS_TEXT, ORDER_STATUS_TAG,
  type Order, type OrderStatus,
} from '@/api'
import { money, datetime } from '@takeout/shared'

const tabs: { label: string; value: '' | OrderStatus }[] = [
  { label: '全部', value: '' },
  { label: '待支付', value: 10 },
  { label: '已支付', value: 20 },
  { label: '待接单', value: 30 },
  { label: '配送中', value: 40 },
  { label: '已完成', value: 50 },
  { label: '退款审核', value: 70 },
  { label: '已取消', value: 60 },
]

const activeStatus = ref<'' | OrderStatus>('')
const page = ref(1)
const size = ref(10)
const total = ref(0)
const list = ref<Order[]>([])
const loading = ref(false)

const drawer = ref(false)
const detail = ref<Order | null>(null)

async function load() {
  loading.value = true
  try {
    const data = await fetchOrders({
      page: page.value,
      size: size.value,
      status: activeStatus.value || undefined,
    })
    list.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onTab() {
  page.value = 1
  load()
}
function onPage(p: number) {
  page.value = p
  load()
}

async function openDetail(row: Order) {
  try {
    detail.value = await fetchOrder(row.id)
    drawer.value = true
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onAccept(row: Order) {
  await ElMessageBox.confirm(`确认接单 ${row.orderNumber} 吗？`, '接单确认', { type: 'warning' })
  try {
    await acceptOrder(row.id)
    ElMessage.success('已接单')
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onCancel(row: Order) {
  await ElMessageBox.confirm(`确认取消订单 ${row.orderNumber} 吗？`, '取消确认', { type: 'warning' })
  try {
    await cancelOrder(row.id)
    ElMessage.success('已取消')
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onRefundReview(row: Order, approve: boolean, remark = '') {
  await ElMessageBox.confirm(
    `顾客申请退款：${row.refundReason || '未填写原因'}。确认${approve ? '同意并模拟退款到账' : '拒绝该申请'}吗？`,
    approve ? '同意退款' : '拒绝退款',
    { type: 'warning' },
  )
  try {
    const updated = await reviewRefund(row.id, approve, remark)
    ElMessage.success(approve ? '已同意退款（模拟到账）' : '已拒绝退款申请')
    drawer.value = false
    detail.value = null
    load()
    return updated
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onRejectRefund(row: Order) {
  const { value } = await ElMessageBox.prompt('请填写拒绝原因（可选）', '拒绝退款', {
    inputPlaceholder: '如：已出餐，不便退款',
    inputValue: '',
  }).catch(() => ({ value: null }))
  if (value === null) return
  await onRefundReview(row, false, value || '')
}

const canCancel = (s: number) => [10, 20, 30].includes(s)

onMounted(load)
</script>

<template>
  <div class="orders">
    <el-card shadow="never">
      <el-tabs v-model="activeStatus" @tab-change="onTab">
        <el-tab-pane v-for="t in tabs" :key="t.value" :label="t.label" :name="t.value" />
      </el-tabs>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="orderNumber" label="订单号" min-width="180" />
        <el-table-column label="金额" width="110">
          <template #default="{ row }">¥{{ money(row.totalAmount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(ORDER_STATUS_TAG as any)[row.status] || 'info'" size="small">
              {{ ORDER_STATUS_TEXT[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="170">
          <template #default="{ row }">{{ datetime(row.createTime) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="290" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button v-if="row.status === 20" link type="primary" @click="onAccept(row)">接单</el-button>
            <el-button v-if="row.status === 70" link type="warning" @click="onRefundReview(row, true)">同意退款</el-button>
            <el-button v-if="row.status === 70" link type="danger" @click="onRejectRefund(row)">拒绝</el-button>
            <el-button v-if="canCancel(row.status)" link type="danger" @click="onCancel(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="onPage"
      />
    </el-card>

    <el-drawer v-model="drawer" title="订单详情" size="420px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="订单号">{{ detail.orderNumber }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="(ORDER_STATUS_TAG as any)[detail.status] || 'info'" size="small">
              {{ ORDER_STATUS_TEXT[detail.status] || detail.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="下单时间">{{ datetime(detail.createTime) }}</el-descriptions-item>
          <el-descriptions-item label="顾客">{{ detail.customerName }} {{ detail.customerPhone }}</el-descriptions-item>
          <el-descriptions-item label="配送地址">{{ detail.deliveryAddress }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ detail.remark || '无' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.refundReason" label="退款原因">
            {{ detail.refundReason }}
            <el-tag
              v-if="detail.refundStatus != null && detail.refundStatus !== 10"
              :type="detail.refundStatus === 20 ? 'success' : 'danger'"
              size="small"
              class="refund-tag"
            >
              {{ detail.refundStatus === 20 ? '已同意' : '已拒绝' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ detail.paymentMethod || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="detail.status === 70" class="refund-actions">
          <el-button type="warning" @click="onRefundReview(detail, true)">同意退款</el-button>
          <el-button type="danger" plain @click="onRejectRefund(detail)">拒绝退款</el-button>
        </div>

        <h4 class="items-title">商品清单</h4>
        <el-table :data="detail.items" size="small">
          <el-table-column prop="productName" label="商品" min-width="120" />
          <el-table-column label="单价" width="90">
            <template #default="{ row }">¥{{ money(row.price) }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="70" />
          <el-table-column label="小计" width="90">
            <template #default="{ row }">¥{{ money(row.amount) }}</template>
          </el-table-column>
        </el-table>
        <div class="total-line">合计：<span class="total-amount">¥{{ money(detail.totalAmount) }}</span></div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.items-title { margin: 18px 0 8px; }
.total-line { text-align: right; margin-top: 12px; color: var(--ink-2); }
.total-amount { color: var(--brand-600); font-size: 18px; font-weight: 700; }
.refund-tag { margin-left: 6px; }
.refund-actions { margin-top: 16px; display: flex; gap: 10px; }
</style>
