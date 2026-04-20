function safeStringify(payload = {}) {
  try {
    return JSON.stringify(payload);
  } catch (error) {
    return '{}';
  }
}

export function trackEvent(event, payload = {}) {
  const data = {
    event,
    ...payload,
    ts: Date.now()
  };

  // 轻量埋点：先输出日志，后续可替换为真实埋点上报接口
  console.log('[track]', safeStringify(data));
}

export function trackPageView(pageName, payload = {}) {
  trackEvent('page_view', {
    page: pageName,
    ...payload
  });
}
