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
  { label: '待支付', status: 1 },
  { label: '已支付', status: 2 },
  { label: '待接单', status: 3 },
  { label: '配送中', status: 5 },
  { label: '已完成', status: 8 },
  { label: '已取消', status: 9 },
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
    <van-tabs v-model:active="active" color="#ff6d1f" title-active-color="#ff6d1f" sticky>
      <van-tab v-for="t in tabs" :key="t.label" :title="t.label" />
    </van-tabs>

    <van-pull-refresh v-model="loading" @refresh="load">
      <div class="list">
        <div v-for="o in filtered" :key="o.id" class="order-card" @click="router.push(`/orders/${o.id}`)">
          <div class="o-head">
            <span class="o-merchant"><van-icon name="shop-o" /> {{ o.merchantName }}</span>
            <span class="o-status" :class="{ done: o.status === 8, cancel: o.status === 9, pay: o.status === 1 }">
              {{ ORDER_STATUS[o.status] || o.status }}
            </span>
          </div>
          <div class="o-summary">{{ summary(o) }}</div>
          <div class="o-foot">
            <span class="o-amount">实付 ¥{{ money(o.actualAmount) }}</span>
            <div class="o-actions" @click.stop>
              <van-button
                v-if="o.status === 1"
                size="small"
                type="danger"
                round
                @click="goPay(o)"
              >
                去支付
              </van-button>
              <van-button v-if="o.status === 8" size="small" plain type="primary" round @click="router.push(`/orders/${o.id}?review=1`)">
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
  padding-bottom: 70px;
}
.list {
  padding: 12px;
  min-height: 40vh;
}
.order-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
}
.o-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
}
.o-merchant {
  display: flex;
  align-items: center;
  gap: 4px;
}
.o-status {
  font-size: 12px;
  font-weight: 400;
  color: #ff6d1f;
}
.o-status.done {
  color: #07c160;
}
.o-status.cancel {
  color: #969799;
}
.o-status.pay {
  color: #ee0a24;
}
.o-summary {
  font-size: 13px;
  color: #646566;
  margin: 8px 0;
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
  font-size: 15px;
  font-weight: 700;
  color: #323233;
}
.o-actions {
  display: flex;
  gap: 8px;
}
</style>
