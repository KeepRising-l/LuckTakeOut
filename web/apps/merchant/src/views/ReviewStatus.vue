<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchCurrent } from '@/api'
import { STATUS_APPROVED, useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const detail = ref<{ name: string; phone: string; address: string; description: string } | null>(null)

const status = computed(() => auth.info.status)

const view = computed(() => {
  if (status.value === STATUS_APPROVED) {
    return {
      tag: 'success',
      title: '入驻审核已通过',
      desc: '您的店铺已通过平台审核，可以进入商户中心使用经营功能。',
    }
  }
  if (status.value === 30) {
    return {
      tag: 'danger',
      title: '入驻申请未通过',
      desc: '很抱歉，您的入驻申请未通过平台审核。如有疑问请联系平台运营。',
    }
  }
  return {
    tag: 'warning',
    title: '入驻申请审核中',
    desc: '您的入驻资料已提交，平台正在审核。审核通过后即可使用菜品管理与订单处理功能。',
  }
})

async function load() {
  loading.value = true
  try {
    const data = await fetchCurrent()
    auth.setStatus(data.status)
    detail.value = {
      name: data.name,
      phone: data.phone,
      address: data.address,
      description: data.description,
    }
    if (data.status === STATUS_APPROVED) {
      ElMessage.success('审核已通过，正在进入商户中心')
      router.replace('/')
    }
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(load)
</script>

<template>
  <div class="review-page" v-loading="loading">
    <div class="review-card">
      <el-result :icon="view.tag === 'success' ? 'success' : view.tag === 'danger' ? 'error' : 'warning'"
        :title="view.title" :sub-title="view.desc">
        <template #extra>
          <el-button v-if="status === 20" type="primary" @click="router.push('/')">
            进入商户中心
          </el-button>
          <el-button @click="load">刷新审核状态</el-button>
          <el-button text @click="onLogout">退出登录</el-button>
        </template>
      </el-result>

      <el-descriptions v-if="detail" title="已提交的入驻资料" :column="1" border size="small">
        <el-descriptions-item label="店铺名称">{{ detail.name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detail.phone || '—' }}</el-descriptions-item>
        <el-descriptions-item label="店铺地址">{{ detail.address || '—' }}</el-descriptions-item>
        <el-descriptions-item label="店铺简介">{{ detail.description || '—' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<style scoped>
.review-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  background: linear-gradient(135deg, #fff1e5 0%, #ffe3c9 45%, #ffd3b3 100%);
}
.review-card {
  width: 620px;
  background: #fff;
  border-radius: 12px;
  padding: 8px 28px 28px;
  box-shadow: 0 12px 40px rgba(204, 87, 25, 0.15);
}
</style>
