export function requestPayment(payment = {}) {
  if (!payment || !payment.provider) {
    return Promise.reject(new Error('支付信息不完整'));
  }

  if (payment.status === 'PAID') {
    return Promise.resolve({
      skipped: true,
      paid: true,
      payment
    });
  }

  if (payment.mocked) {
    return Promise.resolve({
      mocked: true,
      payment
    });
  }

  const provider = String(payment.provider || '').toLowerCase();
  const requestPaymentInfo = payment.request_payment || payment.orderInfo || payment.requestPayment || {};

  // H5/WebView uses Alipay's WAP form. Native uni.requestPayment is only
  // available when the host is a compiled App with an Alipay plugin.
  if (provider === 'alipay' && payment.payment_form && typeof document !== 'undefined') {
    const formConfig = payment.payment_form;
    const form = document.createElement('form');
    form.method = formConfig.method || 'POST';
    form.action = formConfig.action;
    form.style.display = 'none';
    Object.entries(formConfig.params || {}).forEach(([key, value]) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = key;
      input.value = String(value ?? '');
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
    return Promise.resolve({ redirected: true, provider, payment });
  }

  return new Promise((resolve, reject) => {
    const handleSuccess = (res) => resolve({ ...res, provider, payment });
    const handleFail = (err) => reject(err);

    if (provider === 'wxpay') {
      uni.requestPayment({
        provider: 'wxpay',
        orderInfo: requestPaymentInfo,
        success: handleSuccess,
        fail: handleFail
      });
      return;
    }

    if (provider === 'alipay') {
      const orderInfo = typeof requestPaymentInfo === 'string'
        ? requestPaymentInfo
        : requestPaymentInfo.orderInfo || '';
      uni.requestPayment({
        provider: 'alipay',
        orderInfo,
        success: handleSuccess,
        fail: handleFail
      });
      return;
    }

    reject(new Error(`Unsupported payment provider: ${provider}`));
  });
}
