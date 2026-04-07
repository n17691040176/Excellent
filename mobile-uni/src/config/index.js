export const DEFAULT_NATIVE_API_BASE_URL = 'http://YOUR_SERVER_IP:8001'
const RUNTIME_KEY = 'excellent_api_base_url'
export const DEFAULT_INVITE_WEB_BASE_URL = 'http://YOUR_H5_DOMAIN'
const INVITE_WEB_KEY = 'excellent_invite_web_base_url'

export function getApiBaseUrl() {
  const runtime = uni.getStorageSync(RUNTIME_KEY)
  if (runtime) {
    return runtime
  }
  if (typeof window !== 'undefined') {
    return ''
  }
  return DEFAULT_NATIVE_API_BASE_URL
}

export function setApiBaseUrl(url) {
  uni.setStorageSync(RUNTIME_KEY, url)
}

export function clearApiBaseUrl() {
  uni.removeStorageSync(RUNTIME_KEY)
}

export function getInviteWebBaseUrl() {
  return uni.getStorageSync(INVITE_WEB_KEY) || DEFAULT_INVITE_WEB_BASE_URL
}

export function setInviteWebBaseUrl(url) {
  uni.setStorageSync(INVITE_WEB_KEY, url)
}

export function clearInviteWebBaseUrl() {
  uni.removeStorageSync(INVITE_WEB_KEY)
}
