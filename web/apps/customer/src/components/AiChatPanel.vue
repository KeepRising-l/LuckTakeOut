<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { storage } from '@takeout/shared'
import { aiApi, money, orderApi } from '@/api'
import type { AiDraft } from '@/api'

/** AI 对话面板：首页半屏弹层与 /ai 页共用；closable 时带标题栏与关闭按钮 */
defineProps<{ closable?: boolean }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()

interface Msg {
  role: 'user' | 'ai'
  text: string
  draft?: AiDraft
  confirmed?: boolean
  /** 用户气泡候补：与后续消息合并成一条一起发送 */
  pending?: boolean
}

const messages = ref<Msg[]>([
  { role: 'ai', text: '您好，我是 AI 点餐助手～可以直接告诉我想吃什么，比如「来一份川香小馆的招牌套餐」，我帮您下单。' },
])
/** 最近会话恢复：24h 内复用上次会话（误关面板/刷新不丢上下文），过期或失效自动新建 */
const SESSION_KEY = 'customerAiSession'
const SESSION_TTL_MS = 24 * 60 * 60 * 1000

/** 面板内只依赖 sessionId；恢复的旧会话仅有 id，其余字段用不到 */
type ActiveSession = { sessionId: string }

function loadStoredSession(): ActiveSession | undefined {
  const raw = storage.getJSON<{ id: string; ts: number }>(SESSION_KEY)
  if (raw && Date.now() - raw.ts < SESSION_TTL_MS) return { sessionId: raw.id }
  storage.remove(SESSION_KEY)
  return undefined
}

function touchStoredSession(id: string) {
  storage.setJSON(SESSION_KEY, { id, ts: Date.now() })
}

const input = ref('')
const sending = ref(false)
const thinkingSeconds = ref(0)
const session = ref<ActiveSession | undefined>(loadStoredSession())
const listRef = ref<HTMLElement>()

/** 待发送消息缓冲：短暂停顿后合并为一条发送，处理中发消息不阻塞 */
const outbox = ref<string[]>([])
let flushTimer: ReturnType<typeof setTimeout> | undefined
const MERGE_WAIT_MS = 1800

async function ensureSession(): Promise<ActiveSession> {
  if (session.value) return session.value
  const created = await aiApi.createSession()
  const s = { sessionId: created.sessionId }
  session.value = s
  touchStoredSession(s.sessionId)
  return s
}

function scrollBottom() {
  nextTick(() => {
    listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
  })
}

function send(text?: string) {
  const msg = (text ?? input.value).trim()
  if (!msg) return
  input.value = ''
  // 与上一条还没发出的候补气泡合并展示，之后作为一条消息发给模型
  const last = messages.value[messages.value.length - 1]
  if (outbox.value.length && last?.role === 'user' && last.pending) {
    last.text += `\n（补充：${msg}）`
  } else {
    messages.value.push({ role: 'user', text: msg, pending: true })
  }
  outbox.value.push(msg)
  scrollBottom()
  scheduleFlush()
}

function scheduleFlush() {
  if (flushTimer) clearTimeout(flushTimer)
  flushTimer = setTimeout(flushOutbox, MERGE_WAIT_MS)
}

async function flushOutbox() {
  flushTimer = undefined
  if (sending.value || !outbox.value.length) return
  const text = outbox.value.join('\n')
  outbox.value = []
  // 候补气泡转正
  for (const m of messages.value) {
    if (m.role === 'user' && m.pending) delete m.pending
  }

  sending.value = true
  thinkingSeconds.value = 0
  const timer = setInterval(() => { thinkingSeconds.value += 1 }, 1000)
  try {
    const s = await ensureSession()
    let replyData: { reply: string; draft?: AiDraft | null }
    try {
      replyData = await aiApi.chat(s.sessionId, text)
    } catch (e) {
      if (!(((e as Error).message || '').includes('会话不存在'))) throw e
      // 恢复的会话已失效（服务端无此会话）：清掉重建重试一次
      session.value = undefined
      storage.remove(SESSION_KEY)
      const fresh = await ensureSession()
      replyData = await aiApi.chat(fresh.sessionId, text)
    }
    touchStoredSession(s.sessionId)
    messages.value.push({ role: 'ai', text: replyData.reply, draft: replyData.draft ?? undefined })
  } catch (e) {
    messages.value.push({ role: 'ai', text: `出错了：${(e as Error).message}` })
  } finally {
    clearInterval(timer)
    sending.value = false
    scrollBottom()
    // 等待期间又攒了新消息（或正在合并窗口内），稍候继续
    if (outbox.value.length) scheduleFlush()
  }
}

async function confirmDraft(msg: Msg) {
  if (!msg.draft || msg.confirmed) return
  try {
    const r = await aiApi.confirmDraft(msg.draft.draftId)
    msg.confirmed = true
    // 确认即支付：不跳购物车/结算页，直接完成支付并进入订单详情
    try {
      await orderApi.pay(r.orderId)
      messages.value.push({
        role: 'ai',
        text: `已下单并支付成功！订单号 ${r.orderNo}，实付 ¥${money(r.actualAmount)}。正在为你跳转订单详情…`,
      })
      scrollBottom()
      setTimeout(() => router.push(`/orders/${r.orderId}`), 1200)
    } catch (payErr) {
      messages.value.push({
        role: 'ai',
        text: `订单已创建（${r.orderNo}，¥${money(r.actualAmount)}），但支付未完成：${(payErr as Error).message}。可到「订单」中继续支付。`,
      })
      scrollBottom()
    }
  } catch (e) {
    showToast((e as Error).message)
  }
}

onMounted(async () => {
  try {
    await ensureSession()
  } catch {
    /* 首次创建失败不阻塞，发送时会重试 */
  }
})
</script>

<template>
  <div class="ai-panel">
    <div v-if="closable" class="panel-head">
      <span class="ph-title serif">AI 点餐助手</span>
      <van-icon name="cross" class="ph-close" @click="emit('close')" />
    </div>

    <div ref="listRef" class="msg-list">
      <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
        <div class="avatar" :class="m.role">
          <van-icon :name="m.role === 'ai' ? 'service-o' : 'user-o'" />
        </div>
        <div class="bubble-wrap">
          <div class="bubble">{{ m.text }}</div>
          <div v-if="m.draft" class="draft-card">
            <div class="d-head"><van-icon name="shop-o" /> {{ m.draft.merchantName }} · 订单确认</div>
            <div v-for="(it, k) in m.draft.items" :key="k" class="d-item">
              <span>{{ it.name }} x{{ it.quantity }}</span>
              <span v-if="it.price != null" class="d-item-price">¥{{ money(it.price * it.quantity) }}</span>
            </div>
            <div class="d-addr" v-if="m.draft.address">
              <van-icon name="location-o" /> 送至：{{ m.draft.address }}
            </div>
            <div class="d-foot">
              <span class="d-total">合计 <em>¥{{ money(m.draft.total) }}</em></span>
              <van-button
                size="small"
                type="primary"
                round
                :disabled="m.confirmed"
                @click="confirmDraft(m)"
              >
                {{ m.confirmed ? '已下单' : '确认下单' }}
              </van-button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="sending" class="msg-row ai">
        <div class="avatar ai"><van-icon name="service-o" /></div>
        <div class="bubble-wrap"><div class="bubble typing">正在思考… {{ thinkingSeconds > 3 ? `${thinkingSeconds}s` : '' }}</div></div>
      </div>
    </div>

    <div class="input-bar">
      <van-field v-model="input" placeholder="想吃什么？告诉我～" @keyup.enter="send()" />
      <van-button type="primary" round :disabled="!input.trim()" @click="send()">发送</van-button>
    </div>
  </div>
</template>

<style scoped>
.ai-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--canvas);
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 13px 16px 9px;
  border-bottom: 1px solid var(--hairline);
  background: var(--surface);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.ph-title {
  font-size: var(--text-xl);
  font-weight: 700;
  letter-spacing: 0.5px;
}
.ph-close {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-42%);
  font-size: 19px;
  color: var(--ink-3);
  padding: 4px;
}
.msg-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px var(--gutter);
}
.msg-row {
  display: flex;
  gap: 9px;
  margin-bottom: 16px;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
.avatar.ai {
  background: var(--brand-50);
  color: var(--brand-600);
  border: 1px solid var(--brand-100);
}
.avatar.user {
  background: var(--surface-3);
  color: var(--ink-2);
}
.bubble-wrap {
  max-width: 76%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bubble {
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: 4px var(--radius-md) var(--radius-md) var(--radius-md);
  padding: 10px 13px;
  font-size: var(--text-lg);
  line-height: 1.55;
  word-break: break-all;
  white-space: pre-wrap;
  box-shadow: var(--shadow-1);
}
.msg-row.user .bubble {
  background: linear-gradient(135deg, #ff8a3d, #f2570a);
  border: none;
  color: #fff;
  border-radius: var(--radius-md) 4px var(--radius-md) var(--radius-md);
}
.typing {
  color: var(--ink-3);
  font-size: var(--text-md);
}
.draft-card {
  background: var(--surface);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  border: 1px solid var(--brand-100);
  box-shadow: var(--shadow-1);
}
.d-head {
  font-size: var(--text-lg);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;
  padding-bottom: 9px;
  border-bottom: 1px dashed var(--hairline);
}
.d-head .van-icon {
  color: var(--brand-500);
}
.d-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: var(--text-md);
  padding: 6px 0;
  color: var(--ink-2);
}
.d-item-price {
  color: var(--ink-1);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.d-addr {
  font-size: var(--text-sm);
  color: var(--color-indigo);
  padding: 7px 0;
  border-top: 1px dashed var(--hairline);
  display: flex;
  align-items: center;
  gap: 4px;
}
.d-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.d-total {
  font-size: var(--text-md);
}
.d-total em {
  color: var(--brand-600);
  font-style: normal;
  font-size: var(--text-2xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.input-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px var(--gutter) calc(9px + env(safe-area-inset-bottom));
  background: var(--surface);
  border-top: 1px solid var(--hairline);
}
.input-bar :deep(.van-field) {
  background: var(--surface-2);
  border-radius: var(--radius-pill);
  padding: 7px 14px;
}
.input-bar :deep(.van-cell) {
  padding: 0 14px;
}
.input-bar .van-button {
  padding: 0 18px;
  font-weight: 600;
}
</style>
