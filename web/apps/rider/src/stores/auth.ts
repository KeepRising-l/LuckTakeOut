import { defineStore } from 'pinia'
import { storage } from '@takeout/shared'
import { api, type RiderInfo } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: storage.get('riderToken') || '',
    riderInfo: storage.getJSON<RiderInfo>('riderInfo'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    async login(username: string, password: string) {
      const data = await api.login(username, password)
      this.token = data.token
      this.riderInfo = { riderId: data.riderId, name: data.name, phone: data.phone }
      storage.set('riderToken', data.token)
      storage.setJSON('riderInfo', this.riderInfo)
    },
    logout() {
      this.token = ''
      this.riderInfo = null
      storage.remove('riderToken')
      storage.remove('riderInfo')
    },
  },
})
