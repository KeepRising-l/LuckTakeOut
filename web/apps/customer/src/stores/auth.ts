import { defineStore } from 'pinia'
import { storage } from '@takeout/shared'
import type { UserInfo } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: storage.get('customerToken') || '',
    user: storage.getJSON<UserInfo>('customerInfo'),
  }),
  getters: {
    isLogin: (s) => !!s.token,
  },
  actions: {
    setLogin(token: string, user: UserInfo) {
      this.token = token
      this.user = user
      storage.set('customerToken', token)
      storage.setJSON('customerInfo', user)
    },
    logout() {
      this.token = ''
      this.user = null
      storage.remove('customerToken')
      storage.remove('customerInfo')
    },
    async refreshProfile() {
      const { userApi } = await import('@/api')
      const user = await userApi.profile()
      this.user = user
      storage.setJSON('customerInfo', user)
    },
  },
})
