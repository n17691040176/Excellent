const PAYMENT_CHANNELS = [
  {
    value: 'BALANCE',
    label: '余额支付',
    desc: '使用账户余额完成支付',
    available: true
  },
  {
    value: 'WECHAT',
    label: '微信支付',
    desc: '跳转微信完成支付',
    available: false,
    unavailable_reason: '微信支付暂未启用'
  },
  {
    value: 'ALIPAY',
    label: '支付宝支付',
    desc: '跳转支付宝完成支付',
    available: false,
    unavailable_reason: '支付宝支付暂未启用'
  }
];

export function paymentOptionKey(item) {
  return `${item.value}|CASH_ONLY`;
}

export function defaultPaymentOption(options = []) {
  const available = options.filter((item) => item.available !== false);
  return available.find((item) => item.value === 'BALANCE')
    || available.find((item) => item.value === 'ALIPAY')
    || available[0]
    || null;
}

function cashOnlyOption(options, channel) {
  const rows = Array.isArray(options) ? options : [];
  return rows.find((item) => (
    item?.value === channel
    && (item.purchase_mode || (item.supports_points ? 'POINTS_CASH' : 'CASH_ONLY')) === 'CASH_ONLY'
  ));
}

export function normalizePaymentOptions(rawOptions = []) {
  return PAYMENT_CHANNELS.map((fallback) => {
    const configured = cashOnlyOption(rawOptions, fallback.value);
    let available = fallback.available;

    if (fallback.value === 'BALANCE') {
      available = configured?.available !== false;
    } else {
      available = Boolean(configured) && configured.available !== false;
    }

    const item = {
      ...fallback,
      ...(configured || {}),
      value: fallback.value,
      label: configured?.label || fallback.label,
      desc: configured?.desc || fallback.desc,
      purchase_mode: 'CASH_ONLY',
      supports_points: false,
      available
    };
    item.unavailable_reason = available
      ? ''
      : configured?.unavailable_reason || fallback.unavailable_reason || `${item.label}暂不可用`;
    item.key = paymentOptionKey(item);
    return item;
  });
}

export function commonPaymentOptions(products = []) {
  if (!products.length) return [];
  const rows = products.map((product) => normalizePaymentOptions(product?.payment_options));
  return PAYMENT_CHANNELS.map((_, index) => {
    const options = rows.map((items) => items[index]);
    const first = options[0];
    const unavailable = options.find((item) => item.available === false);
    return {
      ...first,
      available: !unavailable,
      unavailable_reason: unavailable?.unavailable_reason || ''
    };
  });
}
