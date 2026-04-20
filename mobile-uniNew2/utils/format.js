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
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return fallback;

  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hour = String(d.getHours()).padStart(2, '0');
  const minute = String(d.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hour}:${minute}`;
}
