const TOKEN_KEY = 'excellent_uni_token'
const USER_KEY = 'excellent_uni_user'

export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

export function setToken(token) {
  uni.setStorageSync(TOKEN_KEY, token)
}

export function clearToken() {
  uni.removeStorageSync(TOKEN_KEY)
}

export function getUserCache() {
  return uni.getStorageSync(USER_KEY) || null
}

export function setUserCache(user) {
  uni.setStorageSync(USER_KEY, user)
}

export function clearUserCache() {
  uni.removeStorageSync(USER_KEY)
}

export function clearAuth() {
  clearToken()
  clearUserCache()
}
