<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast, showToast, showFailToast } from 'vant'
import { money } from '@takeout/shared'
import { api, type DeliveryTask, type RiderDetail, type Statistics } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const rider = ref<RiderDetail | null>(null)
const stats = ref<Statistics | null>(null)
const workStatus = ref(2)
const statusSwitching = ref(false)

const activeTab = ref(0)
const pendingTasks = ref<DeliveryTask[]>([])
const myTasks = ref<DeliveryTask[]>([])

const deliveringTasks = computed(() =>
  myTasks.value.filter((t) => t.status === 'accepted' || t.status === 'delivering'),
)
const doneTasks = computed(() => myTasks.value.filter((t) => t.status === 'completed'))

const statusText: Record<string, string> = {
  pending: '待抢单',
  accepted: '已接单',
  delivering: '配送中',
  completed: '已完成',
}

const statusTagType: Record<string, 'primary' | 'success' | 'warning'> = {
  accepted: 'primary',
  delivering: 'warning',
  completed: 'success',
}

let timer: number | undefined

async function loadRider() {
  if (!auth.riderInfo) return
  try {
    rider.value = await api.getRider(auth.riderInfo.riderId)
    workStatus.value = rider.value.workStatus
  } catch {
    /* 静默失败 */
  }
}

async function loadStats() {
  try {
    stats.value = await api.getStatistics()
  } catch {
    /* 静默失败 */
  }
}

async function loadTasks() {
  if (!auth.riderInfo) return
  const rid = auth.riderInfo.riderId
  try {
    const [pending, tasks] = await Promise.all([api.getPending(), api.getTasks(rid)])
    pendingTasks.value = pending.list || []
    myTasks.value = tasks.list || []
  } catch {
    /* 静默失败 */
  }
}

function refreshAll() {
  loadRider()
  loadStats()
  loadTasks()
}

async function toggleStatus(checked: boolean) {
  if (!auth.riderInfo || statusSwitching.value) return
  const next = checked ? 1 : 2
  statusSwitching.value = true
  try {
    await api.setStatus(auth.riderInfo.riderId, next)
    workStatus.value = next
    showSuccessToast(next === 1 ? '已上线，开始接单' : '已下线')
  } catch (e) {
    showFailToast((e as Error).message || '操作失败')
  } finally {
    statusSwitching.value = false
  }
}

async function acceptTask(task: DeliveryTask) {
  try {
    await showConfirmDialog({
      title: '确认接单',
      message: `商家：${task.merchantName}\n配送费：¥${money(task.deliveryFee)}`,
      confirmButtonText: '确认接单',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await api.acceptTask(task.id)
    showSuccessToast('接单成功')
    refreshAll()
  } catch (e) {
    showFailToast((e as Error).message || '接单失败')
  }
}

async function finishDeliver(task: DeliveryTask) {
  try {
    await showConfirmDialog({
      title: '确认送达',
      message: `订单 ${task.orderNo} 是否已送达客户？`,
    })
  } catch {
    return
  }
  try {
    await api.updateStatus(task.id, 6)
    showSuccessToast('配送完成')
    loadTasks()
    loadStats()
  } catch (e) {
    showFailToast((e as Error).message || '操作失败')
  }
}

function goDetail(task: DeliveryTask) {
  router.push(`/task/${task.id}`)
}

onMounted(() => {
  if (!auth.isLoggedIn) {
    router.replace('/login')
    return
  }
  refreshAll()
  timer = window.setInterval(loadTasks, 15000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="workbench">
    <header class="wb-header">
      <div class="wb-header-row">
        <div class="wb-rider">
          <div class="wb-avatar">{{ (rider?.name || auth.riderInfo?.name || '骑').slice(0, 1) }}</div>
          <div class="wb-rider-meta">
            <div class="wb-name">{{ rider?.name || auth.riderInfo?.name || '骑手' }}</div>
          </div>
        </div>
        <div class="wb-switch" @click.stop>
          <span class="wb-switch-label">{{ workStatus === 1 ? '接单中' : '休息中' }}</span>
          <van-switch
            :model-value="workStatus === 1"
            :loading="statusSwitching"
            size="22"
            @update:model-value="toggleStatus"
          />
        </div>
      </div>

      <div class="wb-stats">
        <div class="wb-stat">
          <div class="wb-stat-num tk-price">{{ rider?.todayDeliveryCount ?? stats?.todayDeliveryCount ?? 0 }}</div>
          <div class="wb-stat-label">今日单量</div>
        </div>
        <div class="wb-stat">
          <div class="wb-stat-num tk-price">{{ stats?.totalDeliveryCount ?? 0 }}</div>
          <div class="wb-stat-label">累计单量</div>
        </div>
      </div>
    </header>

    <van-tabs v-model:active="activeTab" class="wb-tabs" sticky>
      <van-tab :title="`待抢单 ${pendingTasks.length ? '(' + pendingTasks.length + ')' : ''}`">
        <div class="task-list">
          <van-empty v-if="!pendingTasks.length" description="暂无待抢订单" image="search" />
          <div
            v-for="t in pendingTasks"
            :key="t.id"
            class="task-card"
            @click="goDetail(t)"
          >
            <div class="task-card-top">
              <span class="task-merchant">{{ t.merchantName }}</span>
              <span class="task-fee tk-price">¥{{ money(t.deliveryFee) }}</span>
            </div>
            <div class="task-line">
              <div class="task-icon shop"><van-icon name="shop-o" /></div>
              <span class="task-line-text">取：{{ t.merchantName }}</span>
            </div>
            <div class="task-line">
              <div class="task-icon location"><van-icon name="location-o" /></div>
              <span class="task-line-text">送：{{ t.deliveryAddress }}</span>
            </div>
            <div class="task-card-bottom">
              <span class="task-meta">配送费 ¥{{ money(t.deliveryFee) }}</span>
              <div class="task-btns">
                <van-button type="primary" size="small" round class="task-btn" @click.stop="acceptTask(t)">抢单</van-button>
              </div>
            </div>
          </div>
        </div>
      </van-tab>

      <van-tab :title="`进行中 ${deliveringTasks.length ? '(' + deliveringTasks.length + ')' : ''}`">
        <div class="task-list">
          <van-empty v-if="!deliveringTasks.length" description="暂无进行中的任务" image="search" />
          <div
            v-for="t in deliveringTasks"
            :key="t.id"
            class="task-card"
            @click="goDetail(t)"
          >
            <div class="task-card-top">
              <span class="task-merchant">{{ t.merchantName }}</span>
              <van-tag :type="statusTagType[t.status]" plain round>{{ statusText[t.status] }}</van-tag>
            </div>
            <div class="task-line">
              <div class="task-icon shop"><van-icon name="shop-o" /></div>
              <span class="task-line-text">取：{{ t.merchantName }}</span>
            </div>
            <div class="task-line">
              <div class="task-icon location"><van-icon name="location-o" /></div>
              <span class="task-line-text">送：{{ t.deliveryAddress }}</span>
            </div>
            <div class="task-card-bottom">
              <span class="task-meta">配送费 ¥{{ money(t.deliveryFee) }}</span>
              <div class="task-btns">
                <van-button v-if="t.status === 'delivering'" type="primary" size="small" round class="task-btn" @click.stop="finishDeliver(t)">确认送达</van-button>
              </div>
            </div>
          </div>
        </div>
      </van-tab>

      <van-tab title="已完成">
        <div class="task-list">
          <van-empty v-if="!doneTasks.length" description="暂无已完成任务" image="search" />
          <div
            v-for="t in doneTasks"
            :key="t.id"
            class="task-card task-card--done"
            @click="goDetail(t)"
          >
            <div class="task-card-top">
              <span class="task-merchant">{{ t.merchantName }}</span>
              <van-tag type="success" plain round>已完成</van-tag>
            </div>
            <div class="task-line">
              <div class="task-icon location"><van-icon name="location-o" /></div>
              <span class="task-line-text">送：{{ t.deliveryAddress }}</span>
            </div>
            <div class="task-card-bottom">
              <span class="task-meta">配送费 ¥{{ money(t.deliveryFee) }}</span>
              <span class="task-meta meta-go">查看详情 ›</span>
            </div>
          </div>
        </div>
      </van-tab>
    </van-tabs>

    <van-tabbar route safe-area-inset-bottom>
      <van-tabbar-item replace to="/" icon="orders-o">接单</van-tabbar-item>
      <van-tabbar-item replace to="/profile" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.workbench {
  min-height: 100vh;
  padding-bottom: 60px;
}

.wb-header {
  background:
    radial-gradient(120% 80% at 85% 0%, rgba(255, 255, 255, 0.22) 0%, transparent 55%),
    linear-gradient(160deg, #ff8a3d 0%, #ff6f1c 58%, #f2570a 100%);
  padding: calc(env(safe-area-inset-top) + 18px) 16px 22px;
  color: #fff;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
.wb-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wb-rider {
  display: flex;
  align-items: center;
  gap: 10px;
}
.wb-avatar {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  border: 1.5px solid rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
}
.wb-name {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.wb-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: var(--radius-pill);
  padding: 5px 12px;
  backdrop-filter: blur(4px);
}
.wb-switch-label {
  font-size: var(--text-sm);
  font-weight: 500;
}

.wb-stats {
  margin-top: 18px;
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 14px 0;
  display: flex;
  color: var(--ink-1);
  box-shadow: var(--shadow-2);
}
.wb-stat {
  flex: 1;
  text-align: center;
}
.wb-stat + .wb-stat {
  border-left: 1px solid var(--hairline);
}
.wb-stat-num {
  font-size: 21px;
  color: var(--brand-600);
  font-weight: 700;
}
.wb-stat-label {
  margin-top: 3px;
  font-size: var(--text-sm);
  color: var(--ink-3);
}

.wb-tabs {
  margin-top: 12px;
}

.task-list {
  padding: 12px var(--gutter) 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 300px;
}

.task-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 14px;
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-1);
  transition: transform var(--dur-fast) var(--ease-spring);
}
.task-card:active {
  transform: scale(0.98);
}
.task-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.task-merchant {
  font-size: var(--text-xl);
  font-weight: 600;
  font-family: var(--font-serif);
  color: var(--ink-1);
}
.task-fee {
  font-size: var(--text-2xl);
}
.task-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: var(--text-md);
  color: var(--ink-2);
  margin-top: 5px;
}
.task-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
  margin-top: 1px;
}
.task-icon.shop {
  background: var(--brand-50);
  color: var(--brand-600);
}
.task-icon.location {
  background: var(--color-indigo-soft);
  color: var(--color-indigo);
}
.task-line-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}
.task-card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--hairline);
}
.task-meta {
  font-size: var(--text-sm);
  color: var(--ink-3);
}
.meta-go {
  color: var(--brand-600);
  font-weight: 500;
}
.task-btns {
  display: flex;
  gap: 8px;
}
.task-btn {
  padding: 0 16px;
  font-weight: 600;
}
.task-card--done {
  opacity: 0.88;
}
</style>
