import { clearAuth, getToken } from '../utils/auth'
import { getApiBaseUrl } from '../config/index'

function toQuery(params = {}) {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return query ? `?${query}` : ''
}

function handleUnauthorized() {
  clearAuth()
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  if (!current || current.route !== 'pages/login/index') {
    uni.reLaunch({ url: '/pages/login/index' })
  }
}

function request(method, url, options = {}) {
  const token = getToken()
  const { data, params, header, hideLoading, ...rest } = options
  const requestUrl = `${getApiBaseUrl()}${url}${toQuery(params)}`

  if (!hideLoading) {
    uni.showLoading({ title: '加载中', mask: true })
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: requestUrl,
      method,
      data,
      header: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...header
      },
      timeout: 15000,
      ...rest,
      success(response) {
        const payload = response.data || {}
        if (response.statusCode === 401) {
          handleUnauthorized()
          uni.showToast({ title: '登录失效，请重新登录', icon: 'none' })
          reject(payload)
          return
        }
        if (response.statusCode >= 400) {
          uni.showToast({ title: payload.message || '服务异常', icon: 'none' })
          reject(payload)
          return
        }
        if (payload.code !== 0) {
          uni.showToast({ title: payload.message || '请求失败', icon: 'none' })
          reject(payload)
          return
        }
        resolve(payload.data)
      },
      fail(error) {
        uni.showToast({ title: error.errMsg || '网络异常', icon: 'none' })
        reject(error)
      },
      complete() {
        if (!hideLoading) {
          uni.hideLoading()
        }
      }
    })
  })
}

export default {
  get(url, options) {
    return request('GET', url, options)
  },
  post(url, data, options = {}) {
    return request('POST', url, { ...options, data })
  },
  put(url, data, options = {}) {
    return request('PUT', url, { ...options, data })
  },
  patch(url, data, options = {}) {
    return request('PATCH', url, { ...options, data })
  },
  delete(url, options) {
    return request('DELETE', url, options)
  }
}
