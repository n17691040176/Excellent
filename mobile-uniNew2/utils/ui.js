const DEFAULT_LOADING_TEXT = '加载中...';

const ERROR_CODE_MAP = {
  400: '请求参数异常',
  401: '登录失效，请重新登录',
  403: '暂无权限访问',
  404: '资源不存在',
  408: '请求超时，请稍后重试',
  429: '请求过于频繁，请稍后再试',
  500: '服务开小差了，请稍后再试',
  502: '网关异常，请稍后再试',
  503: '服务不可用，请稍后再试',
  504: '网关超时，请稍后再试'
};

export function getErrorMessageByCode(code, fallback = '请求失败') {
  return ERROR_CODE_MAP[code] || fallback;
}

export function showError(error = {}, fallback = '请求失败') {
  const code = Number(error?.code || error?.statusCode || error?.status);
  const message = error?.message || error?.errMsg || getErrorMessageByCode(code, fallback);
  uni.showToast({ title: message || fallback, icon: 'none' });
}

export function showLoading(title = DEFAULT_LOADING_TEXT) {
  uni.showLoading({ title: title || DEFAULT_LOADING_TEXT, mask: true });
}

export function hideLoading() {
  uni.hideLoading();
}
