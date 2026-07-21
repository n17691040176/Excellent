const INVITE_CODE_PATTERN = /^[A-Za-z0-9_-]{1,32}$/;

export function buildInviteUrl(baseUrl, inviteCode) {
  const base = String(baseUrl || '').replace(/\/+$/, '');
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
