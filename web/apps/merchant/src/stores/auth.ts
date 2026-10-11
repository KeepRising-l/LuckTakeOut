import { storage } from '@takeout/shared'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface MerchantInfo {
  merchantId?: number
  merchantName?: string
  avatar?: string
  /** 入驻审核状态：10 待审核 / 20 已通过 / 30 已驳回 */
  status?: number
}

/** 入驻审核已通过 */
export const STATUS_APPROVED = 20

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(storage.get('merchantToken') || '')
  const info = ref<MerchantInfo>(storage.getJSON<MerchantInfo>('merchantInfo') || {})

  function setAuth(t: string, i: MerchantInfo) {
    token.value = t
    info.value = i
    storage.set('merchantToken', t)
    storage.setJSON('merchantInfo', i)
  }

  function setAvatar(avatar: string) {
    info.value = { ...info.value, avatar }
    storage.setJSON('merchantInfo', info.value)
  }

  function setStatus(status: number) {
    info.value = { ...info.value, status }
    storage.setJSON('merchantInfo', info.value)
  }

  function logout() {
    token.value = ''
    info.value = {}
    storage.remove('merchantToken')
    storage.remove('merchantInfo')
  }

  return { token, info, setAuth, setAvatar, setStatus, logout }
})
