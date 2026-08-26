const API_BASE_URL_KEY = 'excellent_api_base_url'
const INVITE_WEB_BASE_URL_KEY = 'excellent_invite_web_base_url'
const APP_ENV_KEY = 'excellent_app_env'

const BUILD_APP_ENV = (typeof globalThis !== 'undefined' && globalThis.__APP_ENV__) || ''
const BUILD_API_BASE_URL = (typeof globalThis !== 'undefined' && globalThis.__API_BASE_URL__) || ''
const BUILD_INVITE_WEB_BASE_URL = (typeof globalThis !== 'undefined' && globalThis.__INVITE_WEB_BASE_URL__) || ''

export const APP_ENV = {
	LOCAL: 'local',
	DEV: 'dev',
	PROD: 'prod'
}

const ENV_MAP = {
	[APP_ENV.LOCAL]: {
		apiBaseUrl: 'http://127.0.0.1:8000/api/',
		inviteWebBaseUrl: 'http://127.0.0.1:5174'
	},
	[APP_ENV.DEV]: {
		apiBaseUrl: 'http://175.27.228.166:8000/api/',
		inviteWebBaseUrl: 'http://175.27.228.166:5174'
	},
	[APP_ENV.PROD]: {
		apiBaseUrl: '/api/',
		inviteWebBaseUrl: 'https://zyhskj.shop'
	}
}

function isH5Runtime() {
	return typeof window !== 'undefined' && typeof window.location !== 'undefined';
}

function isLocalHostname(hostname = '') {
	return ['127.0.0.1', 'localhost', '::1'].includes(String(hostname).toLowerCase());
}

function shouldIgnoreCrossContextUrl(url) {
	if (!isH5Runtime() || !url) return false;

	try {
		const target = new URL(String(url), window.location.origin);
		const currentHostIsLocal = isLocalHostname(window.location.hostname);
		const targetHostIsLocal = isLocalHostname(target.hostname);

		if (!currentHostIsLocal && targetHostIsLocal) {
			return true;
		}

		if (currentHostIsLocal && !targetHostIsLocal) {
			return true;
		}

		return false;
	} catch (error) {
		return false;
	}
}

function normalizeBaseUrl(url, fallback = '') {
	if (!url) return fallback
	return String(url).replace(/\/+$/, '')
}

function isLocalHost(hostname = '') {
	return ['127.0.0.1', 'localhost', '::1'].includes(String(hostname).toLowerCase())
}

function isLocalUrl(url = '') {
	if (!url) return false

	try {
		const parsed = new URL(String(url), 'http://placeholder.local')
		return isLocalHost(parsed.hostname)
	} catch (error) {
		return false
	}
}

function getEnvValue(key) {
	let value = ''
	// #ifdef VITE
	value = import.meta.env?.[key] || ''
	// #endif
	return value
}

function getRuntimeValue(key) {
	try {
		return uni.getStorageSync(key)
	} catch (error) {
		return ''
	}
}

function resolveBaseUrl(runtimeKey, envValue, fallback) {
	const rawRuntimeValue = uni.getStorageSync(runtimeKey)
	const rejectLocalUrl = getAppEnv() === APP_ENV.PROD
	const runtimeValue = shouldIgnoreCrossContextUrl(rawRuntimeValue) || (rejectLocalUrl && isLocalUrl(rawRuntimeValue)) ? '' : rawRuntimeValue
	const resolvedEnvValue = shouldIgnoreCrossContextUrl(envValue) || (rejectLocalUrl && isLocalUrl(envValue)) ? '' : envValue
	const resolvedFallback = shouldIgnoreCrossContextUrl(fallback) || (rejectLocalUrl && isLocalUrl(fallback)) ? '' : fallback
	const resolved = normalizeBaseUrl(runtimeValue || resolvedEnvValue || resolvedFallback, resolvedFallback)
	const source = runtimeValue ? 'runtime' : (resolvedEnvValue ? 'env' : 'default')
	return {
		value: resolved,
		source,
		runtimeValue: normalizeBaseUrl(rawRuntimeValue || ''),
		envValue: normalizeBaseUrl(resolvedEnvValue || ''),
		fallback: normalizeBaseUrl(resolvedFallback, resolvedFallback)
	}
}

export const ENV_CONFIG = ENV_MAP

export function getAppEnv() {
	const runtimeEnv = getRuntimeValue(APP_ENV_KEY)
	const envValue = getEnvValue('VITE_APP_ENV') || BUILD_APP_ENV
	return runtimeEnv || envValue || APP_ENV.DEV
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
	const runtimeEnv = getRuntimeValue(APP_ENV_KEY)
	if (runtimeEnv) {
		return {
			value: runtimeEnv,
			source: 'runtime'
		}
	}

	const envValue = getEnvValue('VITE_APP_ENV') || BUILD_APP_ENV
	if (envValue) {
		return {
			value: envValue,
			source: 'env'
		}
	}

	return {
		value: APP_ENV.DEV,
		source: 'default'
	}
}

function getEnvConfig() {
	const env = String(getAppEnv() || '').toLowerCase()
	return ENV_MAP[env] || ENV_MAP[APP_ENV.LOCAL]
}

export function getApiBaseUrlConfig() {
	const envConfig = getEnvConfig()
	return resolveBaseUrl(API_BASE_URL_KEY, getEnvValue('VITE_API_BASE_URL') || BUILD_API_BASE_URL || envConfig.apiBaseUrl, envConfig.apiBaseUrl)
}

export function getApiBaseUrl() {
	return getApiBaseUrlConfig().value
}

// Uploaded files are served from the API host, but outside the /api prefix.
export function getAssetBaseUrl() {
	const apiBaseUrl = getApiBaseUrl()
	if (!apiBaseUrl) return ''
	return apiBaseUrl.replace(/\/api\/?$/, '').replace(/\/$/, '')
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
	return resolveBaseUrl(INVITE_WEB_BASE_URL_KEY, getEnvValue('VITE_INVITE_WEB_BASE_URL') || BUILD_INVITE_WEB_BASE_URL || envConfig.inviteWebBaseUrl, envConfig.inviteWebBaseUrl)
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

export function clearRuntimeConfig() {
	uni.removeStorageSync(APP_ENV_KEY)
	uni.removeStorageSync(API_BASE_URL_KEY)
	uni.removeStorageSync(INVITE_WEB_BASE_URL_KEY)
}

// ===========================================
// 阿里云一键登录 H5 配置
// ===========================================
const DYNPNS_CONFIG_KEY = 'dynpns_config'

export const DypnsConfig = {
	// 阿里云控制台获取的配置
	APP_KEY: '请填写您的AppKey',
	SIGNATURE_SECRET: '请填写您的签名密钥',

	// 签名密钥（与后端一致）
	getSignatureSecret() {
		try {
			const config = uni.getStorageSync(DYNPNS_CONFIG_KEY)
			return config?.signatureSecret || this.SIGNATURE_SECRET
		} catch {
			return this.SIGNATURE_SECRET
		}
	},

	setConfig(config) {
		uni.setStorageSync(DYNPNS_CONFIG_KEY, config)
	},

	clearConfig() {
		uni.removeStorageSync(DYNPNS_CONFIG_KEY)
	}
}

export function syncRuntimeConfigFromBuild() {
	if (BUILD_APP_ENV && !getRuntimeValue(APP_ENV_KEY)) {
		setAppEnv(BUILD_APP_ENV)
	}

	if (BUILD_API_BASE_URL && !getRuntimeValue(API_BASE_URL_KEY)) {
		setApiBaseUrl(BUILD_API_BASE_URL)
	}

	if (BUILD_INVITE_WEB_BASE_URL && !getRuntimeValue(INVITE_WEB_BASE_URL_KEY)) {
		setInviteWebBaseUrl(BUILD_INVITE_WEB_BASE_URL)
	}

	if (getAppEnv() === APP_ENV.PROD) {
		const apiBaseUrlConfig = getApiBaseUrlConfig()
		if (isLocalUrl(apiBaseUrlConfig.value)) {
			clearApiBaseUrl()
		}

		const inviteWebBaseUrlConfig = getInviteWebBaseUrlConfig()
		if (isLocalUrl(inviteWebBaseUrlConfig.value)) {
			clearInviteWebBaseUrl()
		}
	}
}
