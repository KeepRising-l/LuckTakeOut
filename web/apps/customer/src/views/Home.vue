<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import TabBar from '@/components/TabBar.vue'
import { merchantApi, pickImage } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const keyword = ref('')
const loading = ref(false)
const merchants = ref<Awaited<ReturnType<typeof merchantApi.nearby>>>([])

const cats = [
  { name: '美食', icon: 'bookmark-o' },
  { name: '奶茶', icon: 'gift-o' },
  { name: '快餐', icon: 'clock-o' },
  { name: '烧烤', icon: 'fire-o' },
  { name: '水果', icon: 'flower-o' },
  { name: '甜品', icon: 'coupon-o' },
  { name: '早餐', icon: 'sun-o' },
  { name: '夜宵', icon: 'moon-o' },
]

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

onMounted(() => {
  if (!auth.isLogin) router.replace('/login')
  else load()
})
</script>

<template>
  <div class="home-page">
    <header class="home-header">
      <div class="addr-bar" @click="router.push('/addresses')">
        <van-icon name="location-o" />
        <span class="addr-text">{{ auth.user?.nickname ? `${auth.user.nickname} 的收货地址` : '请选择收货地址' }}</span>
        <van-icon name="arrow-down" />
      </div>
      <div class="search-bar" @click="onSearch">
        <van-icon name="search" />
        <span>搜索商家、菜品</span>
      </div>
    </header>

    <div class="cat-grid">
      <div v-for="c in cats" :key="c.name" class="cat-item" @click="router.push('/search')">
        <van-icon :name="c.icon" />
        <span>{{ c.name }}</span>
      </div>
    </div>

    <div class="section-title">附近商家</div>
    <van-list v-model:loading="loading" :finished="true" finished-text="没有更多了">
      <div v-for="m in merchants" :key="m.id" class="merchant-card" @click="router.push(`/merchant/${m.id}`)">
        <van-image class="m-img" radius="8" fit="cover" :src="pickImage(m)">
          <template #loading><van-icon name="shop-o" /></template>
        </van-image>
        <div class="m-info">
          <div class="m-name">{{ m.name }}</div>
          <div class="m-rate">
            <van-rate :model-value="m.rating ?? 0" readonly allow-half size="12" color="#ff6d1f" />
            <span>{{ m.rating != null ? `${m.rating} 分` : '暂无评分' }}</span>
          </div>
          <div class="m-desc">{{ m.description }}</div>
          <div class="m-meta">
            <span>配送费 ¥{{ m.deliveryFee }}</span>
          </div>
        </div>
      </div>
      <van-empty v-if="!loading && !merchants.length" description="附近暂无商家" />
    </van-list>

    <TabBar />
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.home-header {
  background: linear-gradient(180deg, #ff6d1f, #ff8a45);
  padding: 16px 16px 20px;
  color: #fff;
}
.addr-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
}
.addr-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-bar {
  background: #fff;
  border-radius: 20px;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  color: #969799;
  font-size: 14px;
}
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px 0;
  background: #fff;
  margin: -10px 12px 0;
  border-radius: 12px;
  padding: 16px 0;
  position: relative;
}
.cat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #323233;
}
.cat-item .van-icon {
  font-size: 26px;
  color: #ff6d1f;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  padding: 16px 16px 8px;
}
.merchant-card {
  display: flex;
  gap: 10px;
  background: #fff;
  margin: 0 12px 10px;
  border-radius: 10px;
  padding: 12px;
}
.m-img {
  width: 86px;
  height: 86px;
  flex-shrink: 0;
}
.m-img .van-icon {
  font-size: 32px;
  color: #dcdee0;
  line-height: 86px;
}
.m-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.m-name {
  font-size: 16px;
  font-weight: 600;
}
.m-rate {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #969799;
}
.m-desc {
  font-size: 12px;
  color: #969799;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  font-size: 11px;
  color: #969799;
}
</style>
