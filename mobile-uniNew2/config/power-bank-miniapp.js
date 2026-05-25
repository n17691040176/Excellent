const DEFAULT_QUERY = {
  channel: 'excellent_app'
};

export const POWER_BANK_MINIAPP_CONFIG = {
  title: '共享充电宝',
  miniProgram: {
    enabled: true,
    appId: 'wx7866a1515b865305',
    path: '',
    query: DEFAULT_QUERY,
    envVersion: 'release',
    openMode: 'app',
    extraData: {}
  },
  webView: {
    enabled: false,
    url: ''
  },
  fallbackPath: '/subpackages/assets/index?tab=power_bank'
};

function encodeQuery(params = {}) {
  const entries = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '');
  if (!entries.length) return '';
  return entries
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&');
}

function splitPathAndQuery(path = '') {
  const [basePath, rawQuery = ''] = String(path || '').split('?');
  const params = {};
  rawQuery.split('&').forEach((part) => {
    if (!part) return;
    const [key, value = ''] = part.split('=');
    if (key) {
      params[decodeURIComponent(key)] = decodeURIComponent(value);
    }
  });
  return { basePath, params };
}

function mergeContextQuery(context = {}) {
  return {
    ...POWER_BANK_MINIAPP_CONFIG.miniProgram.query,
    user_id: context.userId,
    invite_code: context.inviteCode
  };
}

export function buildPowerBankMiniProgramPath(context = {}) {
  const { basePath, params } = splitPathAndQuery(POWER_BANK_MINIAPP_CONFIG.miniProgram.path);
  if (!basePath) return '';
  const query = encodeQuery({
    ...params,
    ...mergeContextQuery(context)
  });
  return `${basePath}${query ? `?${query}` : ''}`;
}

export function buildPowerBankWebViewUrl(context = {}) {
  const baseUrl = POWER_BANK_MINIAPP_CONFIG.webView.url;
  if (!baseUrl) return '';
  const connector = baseUrl.includes('?') ? '&' : '?';
  const query = encodeQuery(mergeContextQuery(context));
  return `${baseUrl}${query ? `${connector}${query}` : ''}`;
}
