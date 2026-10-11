<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { aiApi, money } from '@/api'
import type { AiDraft, AiSession } from '@/api'

const router = useRouter()

interface Msg {
  role: 'user' | 'ai'
  text: string
  draft?: AiDraft
  confirmed?: boolean
}

const messages = ref<Msg[]>([
  { role: 'ai', text: '您好，我是 AI 点餐助手～可以直接告诉我想吃什么，比如「来一份川香小馆的招牌套餐」，我帮您下单。' },
])
const input = ref('')
const sending = ref(false)
const session = ref<AiSession>()
const listRef = ref<HTMLElement>()

async function ensureSession() {
  if (session.value) return session.value
  session.value = await aiApi.createSession()
  return session.value
}

function scrollBottom() {
  nextTick(() => {
    listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
  })
}

async function send(text?: string) {
  const msg = (text ?? input.value).trim()
  if (!msg || sending.value) return
  input.value = ''
  messages.value.push({ role: 'user', text: msg })
  scrollBottom()
  sending.value = true
  try {
    const s = await ensureSession()
    const { reply, draft } = await aiApi.chat(s.sessionId, msg)
    messages.value.push({ role: 'ai', text: reply, draft })
  } catch (e) {
    messages.value.push({ role: 'ai', text: `出错了：${(e as Error).message}` })
  } finally {
    sending.value = false
    scrollBottom()
  }
}

async function confirmDraft(msg: Msg) {
  if (!msg.draft || msg.confirmed) return
  try {
    const r = await aiApi.confirmDraft(msg.draft.draftId)
    msg.confirmed = true
    messages.value.push({
      role: 'ai',
      text: `下单成功！订单号 ${r.orderNo}，实付 ¥${money(r.actualAmount)}，可到「订单」中查看并支付。`,
    })
    scrollBottom()
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
  <div class="ai-page">
    <van-nav-bar title="AI 点餐助手" left-arrow @click-left="router.back()" />

    <div ref="listRef" class="msg-list">
      <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
        <div class="avatar">
          <van-icon :name="m.role === 'ai' ? 'service-o' : 'user-o'" />
        </div>
        <div class="bubble-wrap">
          <div class="bubble">{{ m.text }}</div>
          <div v-if="m.draft" class="draft-card">
            <div class="d-head"><van-icon name="shop-o" /> {{ m.draft.merchantName }} · 订单确认</div>
            <div v-for="(it, k) in m.draft.items" :key="k" class="d-item">
              <span>{{ it.name }} x{{ it.quantity }}</span>
              <span v-if="it.price != null">¥{{ money(it.price * it.quantity) }}</span>
            </div>
            <div class="d-addr" v-if="m.draft.address">送至：{{ m.draft.address }}</div>
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
        <div class="avatar"><van-icon name="service-o" /></div>
        <div class="bubble-wrap"><div class="bubble typing">对方正在输入...</div></div>
      </div>
    </div>

    <div class="input-bar">
      <van-field v-model="input" placeholder="想吃什么？告诉我～" @keyup.enter="send()" />
      <van-button type="primary" round :disabled="!input.trim() || sending" @click="send()">发送</van-button>
    </div>
  </div>
</template>

<style scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.msg-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #fff;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar .van-icon {
  font-size: 20px;
  color: #ff6d1f;
}
.bubble-wrap {
  max-width: 76%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bubble {
  background: #fff;
  border-radius: 4px 12px 12px 12px;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-all;
}
.msg-row.user .bubble {
  background: #ff6d1f;
  color: #fff;
  border-radius: 12px 4px 12px 12px;
}
.typing {
  color: #969799;
  font-size: 12px;
}
.draft-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid #ffe1cf;
}
.d-head {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f2f3f5;
}
.d-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 6px 0;
  color: #646566;
}
.d-addr {
  font-size: 12px;
  color: #969799;
  padding: 6px 0;
  border-top: 1px dashed #f2f3f5;
}
.d-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.d-total {
  font-size: 13px;
}
.d-total em {
  color: #ff6d1f;
  font-style: normal;
  font-size: 17px;
  font-weight: 700;
}
.input-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px calc(8px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid #f2f3f5;
}
.input-bar .van-field {
  background: #f7f8fa;
  border-radius: 20px;
  padding: 8px 14px;
}
.input-bar .van-button {
  padding: 0 18px;
}
</style>
