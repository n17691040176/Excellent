import { defineStore } from 'pinia'

import { authApi } from '@/api/modules/auth'
import { clearAuth, getToken, getUserCache, setToken, setUserCache } from '@/utils/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    userInfo: getUserCache(),
    loaded: false
  }),
  getters: {
    role: (state) => state.userInfo?.global_role || '',
    isAdmin: (state) => ['SUPER_ADMIN', 'TEAM_ADMIN'].includes(state.userInfo?.global_role)
  },
  actions: {
    async login(payload) {
      const data = await authApi.adminLogin(payload)
      this.token = data.access_token
      this.userInfo = data.user
      this.loaded = true
      setToken(data.access_token)
      setUserCache(data.user)
      return data
    },
    async fetchMe() {
      if (!this.token) return null
      const data = await authApi.me()
      this.userInfo = data
      this.loaded = true
      setUserCache(data)
      return data
    },
    logout() {
      this.token = ''
      this.userInfo = null
      this.loaded = false
      clearAuth()
    }
  }
})
