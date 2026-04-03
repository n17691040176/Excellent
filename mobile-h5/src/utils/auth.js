const TOKEN_KEY = 'excellent_h5_token'
const USER_KEY = 'excellent_h5_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUserCache() {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setUserCache(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearUserCache() {
  localStorage.removeItem(USER_KEY)
}

export function clearAuth() {
  clearToken()
  clearUserCache()
}
