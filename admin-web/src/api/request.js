import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from '@/router'
import { clearAuth, getToken } from '@/utils/auth'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 15000
})

service.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

service.interceptors.response.use(
  (response) => {
    const payload = response.data
    if (payload?.code !== 0) {
      ElMessage.error(payload?.message || '请求失败')
      return Promise.reject(payload)
    }
    return payload.data
  },
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      clearAuth()
      ElMessage.error('登录失效，请重新登录')
      router.replace('/login')
    } else if (status === 403) {
      router.replace('/403')
    } else {
      ElMessage.error(error?.response?.data?.message || error.message || '服务异常')
    }
    return Promise.reject(error)
  }
)

export default service
