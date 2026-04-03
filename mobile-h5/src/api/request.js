import axios from 'axios'
import { showFailToast, showLoadingToast, closeToast } from 'vant'

import router from '@/router'
import { clearAuth, getToken } from '@/utils/auth'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 15000
})

service.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (!config.hideLoading) {
    showLoadingToast({
      duration: 0,
      forbidClick: true,
      loadingType: 'spinner',
      message: '加载中...'
    })
  }
  return config
})

service.interceptors.response.use(
  (response) => {
    closeToast()
    const payload = response.data
    if (payload?.code !== 0) {
      showFailToast(payload?.message || '请求失败')
      return Promise.reject(payload)
    }
    return payload.data
  },
  (error) => {
    closeToast()
    const status = error?.response?.status
    if (status === 401) {
      clearAuth()
      showFailToast('登录失效，请重新登录')
      router.replace('/login')
    } else {
      showFailToast(error?.response?.data?.message || error.message || '服务异常')
    }
    return Promise.reject(error)
  }
)

export default service
