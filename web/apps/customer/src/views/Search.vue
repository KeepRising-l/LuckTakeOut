<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { merchantApi, pickImage } from '@/api'

const route = useRoute()
const router = useRouter()

const keyword = ref((route.query.keyword as string) || '')
const loading = ref(false)
const searched = ref(false)
const merchants = ref<Awaited<ReturnType<typeof merchantApi.nearby>>>([])

async function onSearch(kw?: string) {
  const k = (kw ?? keyword.value).trim()
  if (!k) return
  keyword.value = k
  loading.value = true
  try {
    merchants.value = await merchantApi.nearby({ page: 1, size: 20, keyword: k })
    searched.value = true
  } catch {
    merchants.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (keyword.value) onSearch()
})
</script>

<template>
  <div class="search-page">
    <van-nav-bar title="搜索" left-arrow @click-left="router.back()" />
    <van-search
      v-model="keyword"
      placeholder="搜索商家、菜品"
      show-action
      @search="onSearch()"
      @clear="searched = false"
    >
      <template #action>
        <div class="search-btn" @click="onSearch()">搜索</div>
      </template>
    </van-search>

    <div v-if="!searched" class="hot">
      <div class="hot-title">热门搜索</div>
      <div class="hot-tags">
        <van-tag plain size="large" @click="onSearch('川菜')">川菜</van-tag>
        <van-tag plain size="large" @click="onSearch('奶茶')">奶茶</van-tag>
        <van-tag plain size="large" @click="onSearch('套餐')">套餐</van-tag>
      </div>
    </div>

    <template v-else>
      <div v-for="m in merchants" :key="m.id" class="merchant-card" @click="router.push(`/merchant/${m.id}`)">
        <van-image class="m-img" radius="8" fit="cover" :src="pickImage(m)">
          <template #loading><van-icon name="shop-o" /></template>
        </van-image>
        <div class="m-info">
          <div class="m-name">{{ m.name }}</div>
          <div class="m-sub">{{ m.rating != null ? `${m.rating} 分` : '暂无评分' }}</div>
          <div class="m-sub">配送费 ¥{{ m.deliveryFee }}</div>
        </div>
      </div>
      <van-empty v-if="!loading && !merchants.length" description="没有找到相关商家" />
    </template>
  </div>
</template>

<style scoped>
.search-btn {
  color: #ff6d1f;
  font-size: 14px;
}
.hot {
  padding: 24px 16px;
}
.hot-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}
.hot-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.hot-tags .van-tag {
  color: #323233;
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
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}
.m-img .van-icon {
  font-size: 28px;
  color: #dcdee0;
  line-height: 72px;
}
.m-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}
.m-name {
  font-size: 16px;
  font-weight: 600;
}
.m-sub {
  font-size: 12px;
  color: #969799;
}
</style>
