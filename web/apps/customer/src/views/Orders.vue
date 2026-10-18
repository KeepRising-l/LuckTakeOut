<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showLoadingToast, showToast } from 'vant'
import { orderApi, ORDER_STATUS, money } from '@/api'
import type { Order } from '@/api'
import TabBar from '@/components/TabBar.vue'

const router = useRouter()

const active = ref(0)
const orders = ref<Order[]>([])
const loading = ref(true)

const tabs = [
  { label: '全部', status: 0 },
  { label: '待支付', status: 10 },
  { label: '待接单', status: 30 },
  { label: '配送中', status: 40 },
  { label: '已完成', status: 50 },
  { label: '已取消', status: 60 },
]

const filtered = computed(() => {
  const s = tabs[active.value].status
  return s ? orders.value.filter((o) => o.status === s) : orders.value
})

function summary(o: Order) {
  const names = o.items.map((i) => `${i.productName} x${i.quantity}`)
  return names.length > 2 ? names.slice(0, 2).join('、') + ` 等${o.items.length}件商品` : names.join('、')
}

async function load() {
  showLoadingToast({ message: '加载中...', forbidClick: true, duration: 0 })
  try {
    orders.value = await orderApi.list()
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    loading.value = false
    closeToast()
  }
}

function goPay(o: Order) {
  router.push(`/payment/${o.id}`)
}

onMounted(load)
</script>

<template>
  <div class="orders-page">
    <van-nav-bar title="我的订单" />
    <van-tabs v-model:active="active" color="var(--brand-500)" title-active-color="var(--ink-1)" sticky>
      <van-tab v-for="t in tabs" :key="t.label" :title="t.label" />
    </van-tabs>

    <van-pull-refresh v-model="loading" @refresh="load">
      <div class="list">
        <div
          v-for="o in filtered"
          :key="o.id"
          class="order-card"
          @click="router.push(`/orders/${o.id}`)"
        >
          <div class="o-head">
            <span class="o-merchant"><van-icon name="shop-o" /> {{ o.merchantName }}</span>
            <span class="o-status" :class="`s${o.status}`">
              {{ ORDER_STATUS[o.status] || o.status }}
            </span>
          </div>
          <div class="o-summary">{{ summary(o) }}</div>
          <div class="o-foot">
            <span class="o-amount">实付 <em class="tk-price">¥{{ money(o.actualAmount) }}</em></span>
            <div class="o-actions" @click.stop>
              <van-button
                v-if="o.status === 10"
                size="small"
                type="danger"
                round
                @click="goPay(o)"
              >
                去支付
              </van-button>
              <van-button v-if="o.status === 50" size="small" plain type="primary" round @click="router.push(`/orders/${o.id}?review=1`)">
                评价
              </van-button>
              <van-button size="small" plain round @click="router.push(`/orders/${o.id}`)">查看详情</van-button>
            </div>
          </div>
        </div>
        <van-empty v-if="!loading && !filtered.length" description="暂无相关订单" />
      </div>
    </van-pull-refresh>

    <TabBar />
  </div>
</template>

<style scoped>
.orders-page {
  min-height: 100vh;
  padding-bottom: 76px;
}
.list {
  padding: 12px var(--gutter);
  min-height: 40vh;
}
.order-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 14px;
  margin-bottom: 10px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
  transition: transform var(--dur-fast) var(--ease-spring);
}
.order-card:active {
  transform: scale(0.98);
}
.o-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-xl);
  font-weight: 600;
}
.o-merchant {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-serif);
}
.o-merchant .van-icon {
  color: var(--brand-500);
}
.o-status {
  font-size: var(--text-sm);
  font-weight: 400;
  color: var(--ink-2);
}
/* 状态色固定映射（见设计规范 §7.6） */
.s10 { color: var(--color-tomato); font-weight: 500; }
.s30 { color: var(--color-wheat); font-weight: 500; }
.s40 { color: var(--color-indigo); font-weight: 500; }
.s50 { color: var(--color-fresh); font-weight: 500; }
.s60 { color: var(--ink-3); }
.o-summary {
  font-size: var(--text-md);
  color: var(--ink-2);
  margin: 10px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.o-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.o-amount {
  font-size: var(--text-md);
  color: var(--ink-2);
}
.o-amount em {
  font-style: normal;
  font-size: var(--text-2xl);
}
.o-actions {
  display: flex;
  gap: 8px;
}
</style>
