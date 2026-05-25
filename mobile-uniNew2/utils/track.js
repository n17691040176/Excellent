function safeStringify(payload = {}) {
  try {
    return JSON.stringify(payload);
  } catch (error) {
    return '{}';
  }
}

const shouldLogTrackEvent = Boolean(import.meta.env?.DEV);

export function trackEvent(event, payload = {}) {
  const data = {
    event,
    ...payload,
    ts: Date.now()
  };

  if (!shouldLogTrackEvent) {
    return;
  }

  // 轻量埋点：开发环境先输出日志，后续可替换为真实埋点上报接口
  console.log('[track]', safeStringify(data));
}

export function trackPageView(pageName, payload = {}) {
  trackEvent('page_view', {
    page: pageName,
    ...payload
  });
}
