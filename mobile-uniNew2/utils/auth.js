const TOKEN_KEY = 'excellent_token';
const USER_CACHE_KEY = 'excellent_user_cache';

export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || '';
}

export function setToken(token) {
  if (!token) {
    uni.removeStorageSync(TOKEN_KEY);
    return;
  }
  uni.setStorageSync(TOKEN_KEY, token);
}

export function getUserCache() {
  return uni.getStorageSync(USER_CACHE_KEY) || null;
}

export function setUserCache(user) {
  if (!user) {
    uni.removeStorageSync(USER_CACHE_KEY);
    return;
  }
  uni.setStorageSync(USER_CACHE_KEY, user);
}

export function clearAuth() {
  uni.removeStorageSync(TOKEN_KEY);
  uni.removeStorageSync(USER_CACHE_KEY);
}
