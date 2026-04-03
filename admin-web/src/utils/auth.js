const TOKEN_KEY = 'excellent_admin_token'
const USER_KEY = 'excellent_admin_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUserCache() {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setUserCache(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function removeUserCache() {
  localStorage.removeItem(USER_KEY)
}

export function clearAuth() {
  removeToken()
  removeUserCache()
}
