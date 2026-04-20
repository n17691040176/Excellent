import { clearAuth, getToken } from '../utils/auth';
import { getApiBaseUrl } from '../config/index';
import { getErrorMessageByCode, hideLoading, showError, showLoading } from '../utils/ui';

function toQuery(params = {}) {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&');
  return query ? `?${query}` : '';
}

function handleUnauthorized() {
  clearAuth();
  const pages = getCurrentPages();
  const current = pages[pages.length - 1];
  if (!current || current.route !== 'pages/login/index') {
    uni.reLaunch({ url: '/pages/login/index' });
  }
}

function request(method, url, options = {}) {
  const token = getToken();
  const {
    data,
    params,
    header,
    hideLoading: shouldHideLoading,
    loadingText,
    errorMessage,
    ...rest
  } = options;
  const requestUrl = `${getApiBaseUrl()}${url}${toQuery(params)}`;

  if (!shouldHideLoading) {
    showLoading(loadingText);
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
        const payload = response.data || {};
        const statusCode = response.statusCode;

        if (statusCode === 401) {
          handleUnauthorized();
          showError({ code: 401, message: payload.message }, errorMessage || '登录失效，请重新登录');
          reject(payload);
          return;
        }

        if (statusCode >= 400) {
          showError(
            {
              code: statusCode,
              message: payload.message || getErrorMessageByCode(statusCode, '服务异常')
            },
            errorMessage || '服务异常'
          );
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
      fail(error) {
        showError(error, errorMessage || '网络异常');
        reject(error);
      },
      complete() {
        if (!shouldHideLoading) {
          hideLoading();
        }
      }
    });
  });
}

export default {
  get(url, options) {
    return request('GET', url, options);
  },
  post(url, data, options = {}) {
    return request('POST', url, { ...options, data });
  },
  put(url, data, options = {}) {
    return request('PUT', url, { ...options, data });
  },
  patch(url, data, options = {}) {
    return request('PATCH', url, { ...options, data });
  },
  delete(url, options) {
    return request('DELETE', url, options);
  }
};
