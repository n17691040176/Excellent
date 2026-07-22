const INVITE_CODE_PATTERN = /^[A-Za-z0-9_-]{1,32}$/;

function currentWebBaseUrl(locationLike) {
  const origin = String(locationLike?.origin || '').replace(/\/+$/, '');
  if (!origin) return '';

  const pathname = String(locationLike?.pathname || '/');
  const directory = pathname.endsWith('/')
    ? pathname.replace(/\/+$/, '')
    : pathname.replace(/\/[^/]*$/, '');
  return `${origin}${directory}`.replace(/\/+$/, '');
}

export function resolveInviteWebBaseUrl(baseUrl, locationLike = globalThis?.location) {
  const configured = String(baseUrl || '').trim();
  const currentBase = currentWebBaseUrl(locationLike);

  if (!configured) return currentBase;
  if (!currentBase) return configured.replace(/\/+$/, '');

  try {
    const absolute = new URL(configured, `${currentBase}/`);
    return `${absolute.origin}${absolute.pathname}`.replace(/\/+$/, '');
  } catch {
    return currentBase;
  }
}

export function buildInviteUrl(baseUrl, inviteCode, locationLike = globalThis?.location) {
  const base = resolveInviteWebBaseUrl(baseUrl, locationLike);
  const code = String(inviteCode || '').trim();
  if (!base || !code) return '';
  return `${base}/#/pages/login/index?invite_code=${encodeURIComponent(code)}`;
}

export function extractInviteCode(value) {
  const input = String(value || '').trim();
  if (!input) return '';
  if (INVITE_CODE_PATTERN.test(input)) return input;

  const match = input.match(/[?&]invite_code=([^&#]+)/i);
  if (!match) return '';

  try {
    const code = decodeURIComponent(match[1]).trim();
    return INVITE_CODE_PATTERN.test(code) ? code : '';
  } catch {
    return '';
  }
}
