function normalizedUrl(value) {
  if (value === undefined || value === null) return '';
  if (typeof value === 'object') {
    return normalizedUrl(value.redirect_url || value.url || value.href || value.value);
  }
  return String(value).trim();
}

export function paymentRedirectUrl(payment = {}) {
  return normalizedUrl(
    payment.payment_url
      || payment.h5_url
      || payment.redirect_url
      || payment.provider_payload?.payment_url
      || payment.provider_payload?.h5_url
      || payment.provider_payload?.redirect_url
  );
}

function isExternalUrl(url) {
  return /^(?:https?:)?\/\//i.test(String(url || '').trim());
}

function isAppPlusRuntime() {
  const platform = typeof process !== 'undefined' && process.env
    ? String(process.env.UNI_PLATFORM || '').toLowerCase()
    : '';
  return platform === 'app-plus' || typeof globalThis.plus !== 'undefined';
}

function isH5Runtime() {
  return typeof window !== 'undefined' && !isAppPlusRuntime();
}

function isAllowedPaymentUrl(url) {
  const target = String(url || '').trim();
  // Browsers normalize backslashes and protocol-relative URLs in surprising
  // ways; provider redirects must be explicit HTTP(S) destinations.
  if (target.startsWith('//') || target.includes('\\')) return false;
  // Relative paths and HTTP(S) URLs are the only destinations a provider
  // response should be able to send the client to.
  if (/^[a-z][a-z\d+.-]*:/i.test(target)) {
    if (typeof URL !== 'function') return /^https?:\/\/[^\s]+$/i.test(target);
    try {
      const parsed = new URL(target);
      return (
        (parsed.protocol === 'http:' || parsed.protocol === 'https:')
        && Boolean(parsed.hostname)
        && !parsed.username
        && !parsed.password
      );
    } catch (error) {
      return false;
    }
  }
  return true;
}

/**
 * Open a provider-hosted payment page. H5 must leave the current page rather
 * than call uni.requestPayment, which is only implemented by native builds.
 */
export function redirectPaymentH5(url) {
  const target = normalizedUrl(url);
  if (!target) return false;
  if (!isAllowedPaymentUrl(target)) return false;

  if (typeof window !== 'undefined' && window.location) {
    try {
      if (typeof window.location.assign === 'function') {
        window.location.assign(target);
      } else {
        window.location.href = target;
      }
      return true;
    } catch (error) {
      // Some embedded WebViews expose a read-only location object. Try the
      // direct href setter before falling back to the uni navigation bridge.
      try {
        window.location.href = target;
        return true;
      } catch (ignored) {
        // Continue to the uni fallback below.
      }
    }
  }

  if (isExternalUrl(target) && globalThis.plus?.runtime?.openURL) {
    globalThis.plus.runtime.openURL(target);
    return true;
  }

  if (!isExternalUrl(target) && typeof uni !== 'undefined' && typeof uni.navigateTo === 'function') {
    uni.navigateTo({ url: target });
    return true;
  }

  return false;
}

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
  const h5Url = paymentRedirectUrl(payment);

  // Alipay H5 uses a signed POST form. Keep that path ahead of a generic URL
  // when both fields are present; WeChat H5 uses payment_url/h5_url below.
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

  if (h5Url) {
    if (redirectPaymentH5(h5Url)) {
      return Promise.resolve({ redirected: true, provider, payment });
    }
    return Promise.reject(new Error(`${provider} H5支付地址无法打开`));
  }

  // Never fall through to the native bridge from a browser build. A missing
  // H5 URL is a provider configuration error, not a reason to invoke a
  // function that does not exist in the H5 runtime.
  if (isH5Runtime()) {
    return Promise.reject(new Error(`${provider} H5支付参数缺失`));
  }

  return new Promise((resolve, reject) => {
    const handleSuccess = (res) => resolve({ ...res, provider, payment });
    const handleFail = (err) => reject(err);

    if (typeof uni === 'undefined' || typeof uni.requestPayment !== 'function') {
      reject(new Error('当前运行环境不支持支付'));
      return;
    }

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
