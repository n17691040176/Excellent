import { getApiBaseUrl } from '../config';
import { clearAuth, getToken } from '../utils/auth';
import { getErrorMessageByCode, hideLoading, showError, showLoading } from '../utils/ui';

function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '');
  if (!entries.length) return '';

  return entries
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&');
}

export function joinUrl(baseUrl, path) {
  if (!path) return baseUrl;
  if (/^https?:\/\//i.test(path)) return path;
  if (!baseUrl) return path;

  const normalizedBase = String(baseUrl).replace(/\/+$/, '');
  let normalizedPath = String(path).replace(/^\/+/, '');
  // API modules use /api/v1 paths while deployments may expose the API base
  // itself as /api. Avoid producing /api/api/v1 in that configuration.
  if (normalizedBase.endsWith('/api') && (normalizedPath === 'api' || normalizedPath.startsWith('api/'))) {
    normalizedPath = normalizedPath.slice(3).replace(/^\/+/, '');
  }

  if (!normalizedBase) return `/${normalizedPath}`;
  return normalizedPath ? `${normalizedBase}/${normalizedPath}` : normalizedBase;
}

function handleUnauthorized() {
  clearAuth();
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  if (!current || current.route !== 'pages/login/index') {
    uni.reLaunch({ url: '/pages/login/index' });
  }
}

function request(options = {}) {
  const {
    url,
    method = 'GET',
    data,
    params,
    header = {},
    hideLoading: shouldHideLoading = false,
    silentError = false,
    loadingText,
    errorMessage,
    timeout = 60000,
    ...rest
  } = options;

  const token = getToken();
  const baseUrl = getApiBaseUrl();
  const query = buildQuery(params);
  const finalUrl = joinUrl(baseUrl, query ? `${url}${url.includes('?') ? '&' : '?'}${query}` : url);

  if (!shouldHideLoading) {
    showLoading(loadingText);
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: finalUrl,
      method,
      data,
      header: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...header
      },
      timeout,
      ...rest,
      success: (res) => {
        const payload = res.data || {};
        const statusCode = Number(res.statusCode || 0);

        if (statusCode === 401) {
          handleUnauthorized();
          showError({ code: 401, message: payload.message }, errorMessage || '登录失效，请重新登录');
          reject(payload);
          return;
        }

        if (statusCode >= 400) {
          if (!silentError) {
            showError(
              {
                code: statusCode,
                message: payload.message || getErrorMessageByCode(statusCode, '服务异常')
              },
              errorMessage || '服务异常'
            );
          }
          reject(payload);
          return;
        }

        if (payload.code !== 0) {
          showError(
            {
              code: payload.code,
              message: payload.message
            },
            errorMessage || '请求失败'
          );
          reject(payload);
          return;
        }

        resolve(payload.data);
      },
      fail: (err) => {
        if (!silentError) showError(err, errorMessage || '网络异常');
        reject(err);
      },
      complete: () => {
        if (!shouldHideLoading) {
          hideLoading();
        }
      }
    });
  });
}

request.get = (url, options = {}) => request({ ...options, url, method: 'GET' });
request.post = (url, data, options = {}) => request({ ...options, url, method: 'POST', data });
request.put = (url, data, options = {}) => request({ ...options, url, method: 'PUT', data });
request.patch = (url, data, options = {}) => request({ ...options, url, method: 'PATCH', data });
request.delete = (url, options = {}) => request({ ...options, url, method: 'DELETE' });

export default request;
