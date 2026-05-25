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
