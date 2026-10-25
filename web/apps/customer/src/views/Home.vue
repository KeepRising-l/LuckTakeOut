<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast, showToast } from 'vant'
import TabBar from '@/components/TabBar.vue'
import FoodIcon from '@/components/FoodIcon.vue'
import AiChatPanel from '@/components/AiChatPanel.vue'
import { aiApi, merchantApi, money, orderApi, pickImage } from '@/api'
import type { RecommendedDish, TasteProfile } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const keyword = ref('')
const loading = ref(false)
const merchants = ref<Awaited<ReturnType<typeof merchantApi.nearby>>>([])

/** AI 半屏对话面板：从底部展开，停留在本页 */
const showAi = ref(false)

/** 猜你想吃：口味画像 + 推荐菜品（无历史时后端返回冷启动结果） */
const taste = ref<{ profile: TasteProfile; dishes: RecommendedDish[] } | null>(null)
const reordering = ref(false)

/** 分类入口：餐饮语义线性图标（FoodIcon）+ 暖色圆底 tint */
const cats = [
  { name: '美食', icon: 'noodle', tint: 't1' },
  { name: '奶茶', icon: 'milkTea', tint: 't2' },
  { name: '快餐', icon: 'burger', tint: 't3' },
  { name: '烧烤', icon: 'skewer', tint: 't4' },
  { name: '水果', icon: 'watermelon', tint: 't5' },
  { name: '甜品', icon: 'cake', tint: 't6' },
  { name: '早餐', icon: 'egg', tint: 't7' },
  { name: '夜宵', icon: 'moon', tint: 't8' },
] as const

async function load() {
  loading.value = true
  try {
    merchants.value = await merchantApi.nearby({ page: 1, size: 20 })
  } catch {
    merchants.value = []
  } finally {
    loading.value = false
  }
}

function onSearch() {
  router.push({ path: '/search', query: keyword.value ? { keyword: keyword.value } : {} })
}

async function loadTaste() {
  try {
    taste.value = await aiApi.recommend()
  } catch {
    taste.value = null
  }
}

/** 再点一单：按最近订单生成草稿 → 确认 → 直接支付，不经过购物车与结算页 */
async function onReorder() {
  if (reordering.value) return
  reordering.value = true
  try {
    const d = await aiApi.reorder()
    const summary = d.items.map((i) => `${i.name} ×${i.quantity}`).join('、')
    const confirmed = await showConfirmDialog({
      title: '再点一单',
      message: `${d.merchantName}：${summary}，合计 ¥${money(d.total)}`,
      confirmButtonText: '确认并支付',
      cancelButtonText: '再看看',
    }).then(() => true).catch(() => false)
    if (!confirmed) return

    const r = await aiApi.confirmDraft(d.draftId)
    await orderApi.pay(r.orderId)
    showSuccessToast('支付成功')
    router.push(`/orders/${r.orderId}`)
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    reordering.value = false
  }
}

onMounted(() => {
  if (!auth.isLogin) router.replace('/login')
  else {
    load()
    loadTaste()
  }
})
</script>

<template>
  <div class="home-page">
    <header class="home-header">
      <div class="brand-row">
        <span class="brand-mark serif">拾味</span>
        <div class="addr-bar" @click="router.push('/addresses')">
          <van-icon name="location-o" />
          <span class="addr-text">{{ auth.user?.nickname ? `${auth.user.nickname} 的收货地址` : '请选择收货地址' }}</span>
          <van-icon name="arrow-down" />
        </div>
      </div>
      <div class="search-bar" @click="onSearch">
        <van-icon name="search" />
        <span>{{ keyword || '搜索商家、菜品' }}</span>
      </div>
    </header>

    <div class="cat-grid">
      <div v-for="(c, i) in cats" :key="c.name" class="cat-item tk-rise" :style="{ '--i': i }" @click="router.push('/search')">
        <div class="cat-tile" :class="c.tint">
          <FoodIcon :name="c.icon" :size="24" />
        </div>
        <span>{{ c.name }}</span>
      </div>
    </div>

    <section v-if="taste && taste.dishes.length" class="rec-block tk-rise">
      <div class="rec-head">
        <div class="rec-head-text">
          <span class="rec-title">猜你想吃</span>
          <span v-if="taste.profile.orderCount" class="rec-sub">
            常点「{{ taste.profile.topMerchants[0]?.name }}」· 客单价 ¥{{ money(taste.profile.avgAmount) }}
          </span>
          <span v-else class="rec-sub">还没有历史订单，先看看人气菜</span>
        </div>
        <van-button
          v-if="taste.profile.orderCount"
          class="rec-reorder"
          size="small"
          round
          plain
          type="primary"
          :loading="reordering"
          @click="onReorder"
        >
          再点一单
        </van-button>
      </div>
      <div class="rec-scroll">
        <div
          v-for="d in taste.dishes"
          :key="d.productId"
          class="rec-card"
          @click="router.push(`/shop/${d.merchantId}`)"
        >
          <van-image class="rec-img" radius="10" fit="cover" :src="d.image">
            <template #loading><van-icon name="photo-o" /></template>
          </van-image>
          <div class="rec-name">{{ d.name }}</div>
          <div class="rec-price">¥{{ money(d.price) }}</div>
          <div class="rec-reason">{{ d.reason }}</div>
        </div>
      </div>
    </section>

    <div class="section-head">
      <span class="section-title">附近商家</span>
      <span class="section-sub">准时达 · 品质放心</span>
    </div>
    <van-list v-model:loading="loading" :finished="true" finished-text="没有更多了">
      <div
        v-for="(m, i) in merchants"
        :key="m.id"
        class="merchant-card tk-rise"
        :style="{ '--i': i }"
        @click="router.push(`/shop/${m.id}`)"
      >
        <van-image class="m-img" radius="10" fit="cover" :src="pickImage(m)">
          <template #loading><van-icon name="shop-o" /></template>
        </van-image>
        <div class="m-info">
          <div class="m-name">{{ m.name }}</div>
          <div class="m-rate">
            <van-rate :model-value="m.rating ?? 0" readonly allow-half size="12" />
            <span>{{ m.rating != null ? `${m.rating} 分` : '暂无评分' }}</span>
          </div>
          <div class="m-desc">{{ m.description }}</div>
          <div class="m-meta">
            <span class="m-fee">配送 ¥{{ m.deliveryFee }}</span>
          </div>
        </div>
      </div>
      <van-empty v-if="!loading && !merchants.length" description="附近暂无商家">
        <van-button round size="small" type="primary" plain @click="load">刷新试试</van-button>
      </van-empty>
    </van-list>

    <!-- AI 悬浮入口：点击从底部展开半屏对话面板，停留在本页 -->
    <div v-if="!showAi" class="ai-fab" @click="showAi = true">
      <van-icon name="chat-o" />
      <span>AI</span>
    </div>
    <van-popup v-model:show="showAi" position="bottom" round :style="{ height: '52vh' }">
      <AiChatPanel closable @close="showAi = false" />
    </van-popup>

    <TabBar />
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  padding-bottom: 76px;
}

/* ---------- 顶部 Hero ---------- */
.home-header {
  background:
    radial-gradient(120% 80% at 85% 0%, rgba(255, 255, 255, 0.22) 0%, transparent 55%),
    linear-gradient(160deg, #ff8a3d 0%, #ff6f1c 58%, #f2570a 100%);
  padding: calc(env(safe-area-inset-top) + 14px) var(--gutter) 44px;
  color: #fff;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.brand-mark {
  flex-shrink: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 3px 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.65);
  border-radius: var(--radius-sm);
}
.addr-bar {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  padding: 5px 10px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(4px);
}
.addr-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-bar {
  background: #fff;
  border-radius: var(--radius-pill);
  height: 40px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 16px;
  color: var(--ink-3);
  font-size: 14px;
  box-shadow: var(--shadow-2);
}
.search-bar .van-icon {
  font-size: 17px;
  color: var(--brand-500);
}

/* ---------- 分类入口 ---------- */
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px 0;
  background: var(--surface);
  margin: -28px var(--gutter) 0;
  border-radius: var(--radius-lg);
  padding: 18px 6px 14px;
  position: relative;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
}
.cat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  font-size: var(--text-sm);
  color: var(--ink-1);
}
.cat-tile {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--dur-fast) var(--ease-spring);
}
.cat-item:active .cat-tile {
  transform: scale(0.9);
}
/* 八个低饱和暖色圆，图标统一 --brand-600 */
.t1 { background: #ffe7d3; color: #f2570a; }
.t2 { background: #fdeee0; color: #d9730d; }
.t3 { background: #fdf0d8; color: #c98a0a; }
.t4 { background: #fbe6da; color: #c2551f; }
.t5 { background: #eaf3e4; color: #4c8a3f; }
.t6 { background: #fbe9ec; color: #c2456b; }
.t7 { background: #fdf3df; color: #b97b12; }
.t8 { background: #e9edf4; color: #4a5f8a; }

/* ---------- 区块标题 ---------- */
.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 18px var(--gutter) 10px;
}
.section-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  font-family: var(--font-serif);
  letter-spacing: 0.5px;
}
.section-sub {
  font-size: var(--text-xs);
  color: var(--ink-3);
}

/* ---------- 商家卡片 ---------- */
.merchant-card {
  display: flex;
  gap: 12px;
  background: var(--surface);
  margin: 0 var(--gutter) 10px;
  border-radius: var(--radius-lg);
  padding: 12px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
  transition: transform var(--dur-fast) var(--ease-spring), box-shadow var(--dur-fast) var(--ease-spring);
}
.merchant-card:active {
  transform: scale(0.98);
  box-shadow: none;
}
.m-img {
  width: 88px;
  height: 88px;
  flex-shrink: 0;
}
.m-img .van-icon {
  font-size: 32px;
  color: var(--ink-4);
  line-height: 88px;
}
.m-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.m-name {
  font-size: var(--text-xl);
  font-weight: 600;
  font-family: var(--font-serif);
}
.m-rate {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
.m-desc {
  font-size: var(--text-sm);
  color: var(--ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.m-fee {
  font-size: var(--text-xs);
  color: var(--brand-700);
  background: var(--brand-50);
  border-radius: var(--radius-sm);
  padding: 2px 7px;
}

/* ---------- 猜你想吃 ---------- */
.rec-block {
  margin: 18px var(--gutter) 0;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  padding: 14px 14px 12px;
  box-shadow: var(--shadow-1);
}
.rec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.rec-head-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.rec-title {
  font-size: var(--text-lg);
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--ink-1);
}
.rec-sub {
  font-size: var(--text-xs);
  color: var(--ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rec-reorder {
  flex-shrink: 0;
}
.rec-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 2px;
  -webkit-overflow-scrolling: touch;
}
.rec-scroll::-webkit-scrollbar { display: none; }
.rec-card {
  flex: 0 0 96px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.rec-img {
  width: 96px;
  height: 72px;
  background: var(--surface-2);
}
.rec-name {
  font-size: var(--text-sm);
  color: var(--ink-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rec-price {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--brand-600);
  font-variant-numeric: tabular-nums;
}
.rec-reason {
  font-size: var(--text-xs);
  color: var(--ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------- AI 悬浮入口 ---------- */
.ai-fab {
  position: fixed;
  right: 16px;
  bottom: calc(76px + env(safe-area-inset-bottom));
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: linear-gradient(140deg, #ff8a3d 0%, #ff6f1c 60%, #f2570a 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  box-shadow: var(--shadow-brand);
  z-index: 10;
  transition: transform var(--dur-fast) var(--ease-spring);
}
.ai-fab:active {
  transform: scale(0.88);
}
.ai-fab .van-icon {
  font-size: 21px;
}
</style>
