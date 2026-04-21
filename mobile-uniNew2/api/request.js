import { getApiBaseUrl } from '../config'

function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '')
  if (!entries.length) return ''

  return entries
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')
}

function joinUrl(baseUrl, path) {
  if (!path) return baseUrl
  if (/^https?:\/\//i.test(path)) return path
  if (!baseUrl) return path
  return `${baseUrl.replace(/\/$/, '')}/${String(path).replace(/^\//, '')}`
}

function request(options = {}) {
  const {
    url,
    method = 'GET',
    data,
    params,
    header = {},
    hideLoading = false,
    timeout = 60000
  } = options

  const baseUrl = getApiBaseUrl()
  const query = buildQuery(params)
  const finalUrl = joinUrl(baseUrl, query ? `${url}${url.includes('?') ? '&' : '?'}${query}` : url)

  if (!hideLoading) {
    uni.showLoading({ title: '加载中', mask: true })
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: finalUrl,
      method,
      data,
      header,
      timeout,
      success: (res) => {
        resolve(res)
      },
      fail: (err) => {
        reject(err)
      },
      complete: () => {
        if (!hideLoading) {
          uni.hideLoading()
        }
      }
    })
  })
}

request.get = (url, options = {}) => request({ ...options, url, method: 'GET' })
request.post = (url, data, options = {}) => request({ ...options, url, method: 'POST', data })
request.put = (url, data, options = {}) => request({ ...options, url, method: 'PUT', data })
request.patch = (url, data, options = {}) => request({ ...options, url, method: 'PATCH', data })
request.delete = (url, options = {}) => request({ ...options, url, method: 'DELETE' })

export default request
