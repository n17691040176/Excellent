const API_BASE_URL_KEY = 'excellent_api_base_url';
const INVITE_WEB_BASE_URL_KEY = 'excellent_invite_web_base_url';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_INVITE_WEB_BASE_URL = 'http://127.0.0.1:8080';

function normalizeBaseUrl(url, fallback = '') {
  if (!url) return fallback;
  return String(url).replace(/\/+$/, '');
}

function resolveBaseUrl(runtimeKey, envValue, fallback) {
  const runtimeValue = uni.getStorageSync(runtimeKey);
  const resolved = normalizeBaseUrl(runtimeValue || envValue || fallback, fallback);
  const source = runtimeValue ? 'runtime' : (envValue ? 'env' : 'default');
  return {
    value: resolved,
    source,
    runtimeValue: normalizeBaseUrl(runtimeValue || ''),
    envValue: normalizeBaseUrl(envValue || ''),
    fallback: normalizeBaseUrl(fallback, fallback)
  };
}

export function getApiBaseUrlConfig() {
  // #ifdef VITE
  const envValue = import.meta.env?.VITE_API_BASE_URL;
  // #endif
  // #ifndef VITE
  const envValue = '';
  // #endif
  return resolveBaseUrl(API_BASE_URL_KEY, envValue, DEFAULT_API_BASE_URL);
}

export function getApiBaseUrl() {
  return getApiBaseUrlConfig().value;
}

export function setApiBaseUrl(url) {
  if (!url) {
    uni.removeStorageSync(API_BASE_URL_KEY);
    return;
  }
  uni.setStorageSync(API_BASE_URL_KEY, normalizeBaseUrl(url));
}

export function clearApiBaseUrl() {
  uni.removeStorageSync(API_BASE_URL_KEY);
}

export function getInviteWebBaseUrlConfig() {
  // #ifdef VITE
  const envValue = import.meta.env?.VITE_INVITE_WEB_BASE_URL;
  // #endif
  // #ifndef VITE
  const envValue = '';
  // #endif
  return resolveBaseUrl(INVITE_WEB_BASE_URL_KEY, envValue, DEFAULT_INVITE_WEB_BASE_URL);
}

export function getInviteWebBaseUrl() {
  return getInviteWebBaseUrlConfig().value;
}

export function setInviteWebBaseUrl(url) {
  if (!url) {
    uni.removeStorageSync(INVITE_WEB_BASE_URL_KEY);
    return;
  }
  uni.setStorageSync(INVITE_WEB_BASE_URL_KEY, normalizeBaseUrl(url));
}

export function clearInviteWebBaseUrl() {
  uni.removeStorageSync(INVITE_WEB_BASE_URL_KEY);
}
