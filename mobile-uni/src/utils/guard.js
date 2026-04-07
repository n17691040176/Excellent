import { getToken } from './auth'

export function ensureLogin() {
  if (getToken()) {
    return true
  }
  uni.reLaunch({ url: '/pages/login/index' })
  return false
}
