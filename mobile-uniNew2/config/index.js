const API_BASE_URL_KEY = 'excellent_api_base_url'
const INVITE_WEB_BASE_URL_KEY = 'excellent_invite_web_base_url'
const APP_ENV_KEY = 'excellent_app_env'

const ENV_MAP = {
  local: {
    apiBaseUrl: 'http://127.0.0.1:8000',
    inviteWebBaseUrl: 'http://127.0.0.1:5174'
  },
  dev: {
    apiBaseUrl: 'http://156.238.241.213:8000',
    inviteWebBaseUrl: 'http://156.238.241.213:5174'
  },
  prod: {
    apiBaseUrl: '',
    inviteWebBaseUrl: ''
  }
}

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
  const runtimeValue = getRuntimeValue(runtimeKey)
  const resolved = normalizeBaseUrl(runtimeValue || envValue || fallback, fallback)
  const source = runtimeValue ? 'runtime' : (envValue ? 'env' : 'default')
  return {
    value: resolved,
    source,
    runtimeValue: normalizeBaseUrl(runtimeValue || ''),
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
