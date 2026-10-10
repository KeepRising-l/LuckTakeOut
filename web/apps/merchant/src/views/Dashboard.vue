<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  fetchOverview,
  fetchRecentOrders,
  fetchOrderStatusStats,
  fetchSales,
  fetchRevenueTrend,
  fetchTopProducts,
  ORDER_STATUS_TEXT,
  type Overview,
  type Order,
} from '@/api'
import { money, datetime } from '@takeout/shared'

const overview = ref<Overview>({
  todayOrders: 0, todayRevenue: 0, totalOrders: 0, totalRevenue: 0, pendingCount: 0,
})
const recentOrders = ref<Order[]>([])

const revenueRef = ref<HTMLElement>()
const salesRef = ref<HTMLElement>()
const topRef = ref<HTMLElement>()
const pieRef = ref<HTMLElement>()
const charts: echarts.ECharts[] = []

const PRIMARY = '#ff6d1f'
const PIE_COLORS: Record<string, string> = {
  PENDING: '#ff9258', CONFIRMED: '#ff6d1f', READY: '#ffb285',
  DELIVERING: '#5470c6', COMPLETED: '#67c23a', CANCELLED: '#c0c4cc',
}

function makeChart(el: HTMLElement | undefined, option: echarts.EChartsOption) {
  if (!el) return
  const c = echarts.init(el)
  c.setOption(option)
  charts.push(c)
}

async function load() {
  const [overviewData, recent, statusStats, sales, trend, top] = await Promise.all([
    fetchOverview(), fetchRecentOrders(), fetchOrderStatusStats(),
    fetchSales(), fetchRevenueTrend(), fetchTopProducts(),
  ])
  overview.value = overviewData
  recentOrders.value = recent

  makeChart(revenueRef.value, {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 28 },
    xAxis: { type: 'category', data: trend.map((t) => t.date) },
    yAxis: { type: 'value' },
    series: [{
      name: '营业额', type: 'line', smooth: true, data: trend.map((t) => t.revenue),
      itemStyle: { color: PRIMARY }, areaStyle: { color: 'rgba(255,109,31,0.12)' },
    }],
  })

  makeChart(salesRef.value, {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 28 },
    xAxis: { type: 'category', data: sales.map((s) => s.date) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ name: '订单量', type: 'bar', data: sales.map((s) => s.count), itemStyle: { color: PRIMARY }, barMaxWidth: 32 }],
  })

  makeChart(topRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 110, right: 30, top: 10, bottom: 24 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: top.map((t) => t.name).reverse(), axisLabel: { width: 100, overflow: 'truncate' } },
    series: [{ name: '销量', type: 'bar', data: top.map((t) => t.count).reverse(), itemStyle: { color: PRIMARY }, barMaxWidth: 18 }],
  })

  makeChart(pieRef.value, {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, itemWidth: 12, itemHeight: 12 },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '44%'],
      data: statusStats.map((s) => ({ name: ORDER_STATUS_TEXT[s.status] || s.status, value: s.count, itemStyle: { color: PIE_COLORS[s.status] } })),
      label: { formatter: '{b}: {c}' },
    }],
  })
}

function onResize() {
  charts.forEach((c) => c.resize())
}

onMounted(async () => {
  try {
    await load()
  } catch (e) {
    console.error(e)
  }
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach((c) => c.dispose())
})
</script>

<template>
  <div class="dashboard">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日订单</div>
          <div class="stat-value">{{ overview.todayOrders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日营业额 (元)</div>
          <div class="stat-value">¥{{ money(overview.todayRevenue) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">总订单</div>
          <div class="stat-value">{{ overview.totalOrders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">总营业额 (元)</div>
          <div class="stat-value">¥{{ money(overview.totalRevenue) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>近7天营业额</template>
          <div ref="revenueRef" class="chart" style="height: 280px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>近7天订单量</template>
          <div ref="salesRef" class="chart" style="height: 280px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>热销 Top10</template>
          <div ref="topRef" class="chart" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>订单状态分布</template>
          <div ref="pieRef" class="chart" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="chart-row">
      <template #header>最近订单</template>
      <el-table :data="recentOrders" stripe>
        <el-table-column prop="orderNumber" label="订单号" min-width="180" />
        <el-table-column label="金额" width="110">
          <template #default="{ row }">¥{{ money(row.totalAmount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(row.status === 'COMPLETED' ? 'success' : row.status === 'CANCELLED' ? 'info' : 'warning')" size="small">
              {{ ORDER_STATUS_TEXT[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="170">
          <template #default="{ row }">{{ datetime(row.createTime) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.stat-card :deep(.el-card__body) { padding: 18px 20px; }
.stat-label { font-size: 13px; color: #909399; }
.stat-value { font-size: 26px; font-weight: 700; margin-top: 8px; color: #303133; }
.chart-row { margin-top: 16px; }
</style>
