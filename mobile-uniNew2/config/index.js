const API_BASE_URL_KEY = 'excellent_api_base_url'
const INVITE_WEB_BASE_URL_KEY = 'excellent_invite_web_base_url'
const APP_ENV_KEY = 'excellent_app_env'

function isH5Runtime() {
  return typeof window !== 'undefined' && typeof window.location !== 'undefined';
}

function isLocalHostname(hostname = '') {
  return ['127.0.0.1', 'localhost', '::1'].includes(String(hostname).toLowerCase());
}

function shouldIgnoreRuntimeUrl(url) {
  if (!isH5Runtime() || !url) return false;

  try {
    const target = new URL(String(url), window.location.origin);
    return !isLocalHostname(window.location.hostname) && isLocalHostname(target.hostname);
  } catch (error) {
    return false;
  }
}

const DEFAULT_API_BASE_URL = isH5Runtime() ? '' : 'http://127.0.0.1:8000';
const DEFAULT_INVITE_WEB_BASE_URL = 'http://127.0.0.1:8080';
function normalizeBaseUrl(url, fallback = '') {
  if (!url) return fallback
  return String(url).replace(/\/+$/, '')
}

function getEnvValue(key) {
  // #ifdef VITE
  return import.meta.env?.[key]
  // #endif
  // #ifndef VITE
  return ''
  // #endif
}

function getRuntimeValue(key) {
  try {
    return uni.getStorageSync(key)
  } catch (error) {
    return ''
  }
}

function resolveBaseUrl(runtimeKey, envValue, fallback) {
  const rawRuntimeValue = uni.getStorageSync(runtimeKey);
  const runtimeValue = shouldIgnoreRuntimeUrl(rawRuntimeValue) ? '' : rawRuntimeValue;
  const resolved = normalizeBaseUrl(runtimeValue || envValue || fallback, fallback);
  const source = runtimeValue ? 'runtime' : (envValue ? 'env' : 'default');
  return {
    value: resolved,
    source,
    runtimeValue: normalizeBaseUrl(rawRuntimeValue || ''),
    envValue: normalizeBaseUrl(envValue || ''),
    fallback: normalizeBaseUrl(fallback, fallback)
  }
}

export const APP_ENV = {
  LOCAL: 'local',
  DEV: 'dev',
  PROD: 'prod'
}

export function getAppEnv() {
  const runtimeEnv = getRuntimeValue(APP_ENV_KEY)
  const envValue = getEnvValue('VITE_APP_ENV')
  return runtimeEnv || envValue || APP_ENV.LOCAL
}

export function setAppEnv(env) {
  if (!env) {
    uni.removeStorageSync(APP_ENV_KEY)
    return
  }
  uni.setStorageSync(APP_ENV_KEY, String(env))
}

export function clearAppEnv() {
  uni.removeStorageSync(APP_ENV_KEY)
}

export function getAppEnvConfig() {
  const appEnv = getAppEnv()
  return {
    value: appEnv,
    source: getRuntimeValue(APP_ENV_KEY) ? 'runtime' : (getEnvValue('VITE_APP_ENV') ? 'env' : 'default')
  }
}

function getEnvConfig() {
  return ENV_MAP[getAppEnv()] || ENV_MAP.local
}

export function getApiBaseUrlConfig() {
  const envConfig = getEnvConfig()
  return resolveBaseUrl(API_BASE_URL_KEY, getEnvValue('VITE_API_BASE_URL') || envConfig.apiBaseUrl, envConfig.apiBaseUrl)
}

export function getApiBaseUrl() {
  return getApiBaseUrlConfig().value
}

export function setApiBaseUrl(url) {
  if (!url) {
    uni.removeStorageSync(API_BASE_URL_KEY)
    return
  }
  uni.setStorageSync(API_BASE_URL_KEY, normalizeBaseUrl(url))
}

export function clearApiBaseUrl() {
  uni.removeStorageSync(API_BASE_URL_KEY)
}

export function getInviteWebBaseUrlConfig() {
  const envConfig = getEnvConfig()
  return resolveBaseUrl(INVITE_WEB_BASE_URL_KEY, getEnvValue('VITE_INVITE_WEB_BASE_URL') || envConfig.inviteWebBaseUrl, envConfig.inviteWebBaseUrl)
}

export function getInviteWebBaseUrl() {
  return getInviteWebBaseUrlConfig().value
}

export function setInviteWebBaseUrl(url) {
  if (!url) {
    uni.removeStorageSync(INVITE_WEB_BASE_URL_KEY)
    return
  }
  uni.setStorageSync(INVITE_WEB_BASE_URL_KEY, normalizeBaseUrl(url))
}

export function clearInviteWebBaseUrl() {
  uni.removeStorageSync(INVITE_WEB_BASE_URL_KEY)
}
