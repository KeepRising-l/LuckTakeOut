<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { merchantApi, productApi, pickImage } from '@/api'

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
    const [byName, products] = await Promise.all([
      merchantApi.nearby({ page: 1, size: 20, keyword: k }),
      productApi.search(k).catch(() => []),
    ])
    // 菜品命中时把所属商户带进结果，按 id 去重
    const extraIds = [...new Set(products.map((p) => p.merchantId).filter((id) => !byName.some((m) => m.id === id)))]
    const extra = await Promise.all(extraIds.slice(0, 10).map((id) => merchantApi.detail(id).catch(() => null)))
    merchants.value = [...byName, ...extra.filter((m): m is NonNullable<typeof m> => !!m)]
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
      shape="round"
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
        <van-tag v-for="k in ['川菜', '奶茶', '套餐', '烧烤', '水果', '甜品']" :key="k" round size="large" class="hot-tag" @click="onSearch(k)">{{ k }}</van-tag>
      </div>
    </div>

    <template v-else>
      <div v-for="(m, i) in merchants" :key="m.id" class="merchant-card tk-rise" :style="{ '--i': i }" @click="router.push(`/shop/${m.id}`)">
        <van-image class="m-img" radius="10" fit="cover" :src="pickImage(m)">
          <template #loading><van-icon name="shop-o" /></template>
        </van-image>
        <div class="m-info">
          <div class="m-name serif">{{ m.name }}</div>
          <div class="m-rate">
            <van-rate :model-value="m.rating ?? 0" readonly allow-half size="11" />
            <span>{{ m.rating != null ? `${m.rating} 分` : '暂无评分' }}</span>
          </div>
          <div class="m-sub">配送费 ¥{{ m.deliveryFee }}</div>
        </div>
      </div>
      <van-empty v-if="!loading && !merchants.length" description="没有找到相关商家">
        <van-button round size="small" type="primary" plain @click="onSearch()">重新搜索</van-button>
      </van-empty>
    </template>
  </div>
</template>

<style scoped>
.search-btn {
  color: var(--brand-600);
  font-size: var(--text-lg);
  font-weight: 500;
  padding-left: 8px;
}
.search-page :deep(.van-search) {
  padding: 8px var(--gutter);
}
.search-page :deep(.van-search__content) {
  background: var(--surface-2);
  border: 1px solid var(--hairline);
}
.hot {
  padding: 20px var(--gutter);
}
.hot-title {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 14px;
  font-family: var(--font-serif);
}
.hot-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.hot-tag {
  color: var(--brand-700);
  background: var(--brand-50);
  border: 1px solid var(--brand-100);
  padding: 6px 14px;
  font-size: var(--text-md);
}
.merchant-card {
  display: flex;
  gap: 10px;
  background: var(--surface);
  margin: 0 var(--gutter) 10px;
  border-radius: var(--radius-lg);
  padding: 12px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
}
.m-img {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}
.m-img .van-icon {
  font-size: 28px;
  color: var(--ink-4);
  line-height: 72px;
}
.m-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
}
.m-name {
  font-size: var(--text-xl);
  font-weight: 600;
}
.m-rate {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
.m-sub {
  font-size: var(--text-sm);
  color: var(--ink-3);
}
</style>
