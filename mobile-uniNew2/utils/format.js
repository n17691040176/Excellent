export function formatMoney(value, options = {}) {
  const { fallback = '0.00', withThousands = true } = options;
  const num = Number(value);
  if (Number.isNaN(num)) return fallback;
  const fixed = num.toFixed(2);
  if (!withThousands) return fixed;
  const [intPart, decimalPart] = fixed.split('.');
  const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${formattedInt}.${decimalPart}`;
}

export function formatDateTime(value, fallback = '--') {
  if (!value) return fallback;
  const raw = typeof value === 'string' ? value.trim() : value;
  const hasOffset = typeof raw === 'string' && /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const looksLikeServerTime = typeof raw === 'string'
    && /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$/.test(raw);
  const normalized = looksLikeServerTime && !hasOffset ? `${raw.replace(' ', 'T')}Z` : raw;
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return fallback;

  const shanghai = new Date(d.getTime() + 8 * 60 * 60 * 1000);
  const year = shanghai.getUTCFullYear();
  const month = String(shanghai.getUTCMonth() + 1).padStart(2, '0');
  const day = String(shanghai.getUTCDate()).padStart(2, '0');
  const hour = String(shanghai.getUTCHours()).padStart(2, '0');
  const minute = String(shanghai.getUTCMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hour}:${minute}`;
}
