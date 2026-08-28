import assert from 'node:assert/strict';
import test from 'node:test';

import {
  paymentRedirectUrl,
  requestPayment
} from './payment.js';

function withoutGlobal(name) {
  const previous = globalThis[name];
  delete globalThis[name];
  return () => {
    if (previous === undefined) delete globalThis[name];
    else globalThis[name] = previous;
  };
}

test('prefers the composed payment_url over a raw H5 URL', () => {
  assert.equal(
    paymentRedirectUrl({
      payment_url: 'https://pay.example/checkout?redirect_url=%2Forders%2F1',
      h5_url: 'https://pay.example/raw',
      redirect_url: 'https://pay.example/redirect'
    }),
    'https://pay.example/checkout?redirect_url=%2Forders%2F1'
  );
  assert.equal(
    paymentRedirectUrl({
      payment_url: { redirect_url: 'https://pay.example/object' },
      h5_url: 'https://pay.example/raw'
    }),
    'https://pay.example/object'
  );
});

test('redirects WeChat H5 payments without invoking the native bridge', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  try {
    let assigned = '';
    let nativeCalls = 0;
    globalThis.window = { location: { assign: (url) => { assigned = url; } } };
    globalThis.uni = {
      requestPayment: () => { nativeCalls += 1; }
    };

    const result = await requestPayment({
      provider: 'wxpay',
      payment_url: 'https://pay.example/checkout?redirect_url=%2Forders%2F1',
      h5_url: 'https://pay.example/raw',
      status: 'PENDING'
    });

    assert.equal(result.redirected, true);
    assert.equal(assigned, 'https://pay.example/checkout?redirect_url=%2Forders%2F1');
    assert.equal(nativeCalls, 0);
  } finally {
    restoreUni();
    restoreWindow();
  }
});

test('uses the uni navigation bridge only for relative payment URLs', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  const restorePlus = withoutGlobal('plus');
  try {
    let navigation;
    globalThis.uni = {
      navigateTo: (options) => { navigation = options; }
    };

    const result = await requestPayment({
      provider: 'wxpay',
      h5_url: '/pages/payment/redirect?out_trade_no=TX-1',
      status: 'PENDING'
    });

    assert.equal(result.redirected, true);
    assert.deepEqual(navigation, { url: '/pages/payment/redirect?out_trade_no=TX-1' });
  } finally {
    restorePlus();
    restoreUni();
    restoreWindow();
  }
});

test('does not send an external URL through uni.navigateTo', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  const restorePlus = withoutGlobal('plus');
  try {
    let nativeCalls = 0;
    let navigationCalls = 0;
    globalThis.uni = {
      navigateTo: () => { navigationCalls += 1; },
      requestPayment: () => { nativeCalls += 1; }
    };

    await assert.rejects(
      requestPayment({ provider: 'wxpay', h5_url: 'https://pay.example/checkout' }),
      /H5支付地址无法打开/
    );
    assert.equal(navigationCalls, 0);
    assert.equal(nativeCalls, 0);
  } finally {
    restorePlus();
    restoreUni();
    restoreWindow();
  }
});

test('rejects protocol-relative payment URLs', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  const restorePlus = withoutGlobal('plus');
  try {
    globalThis.uni = { navigateTo: () => { throw new Error('unexpected navigation'); } };

    await assert.rejects(
      requestPayment({ provider: 'wxpay', h5_url: '//pay.example/checkout' }),
      /H5支付地址无法打开/
    );
  } finally {
    restorePlus();
    restoreUni();
    restoreWindow();
  }
});

test('rejects malformed or backslash-normalized external URLs', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  const restorePlus = withoutGlobal('plus');
  try {
    globalThis.uni = { navigateTo: () => { throw new Error('unexpected navigation'); } };

    for (const h5Url of ['https://?x', '\\\\pay.example\\checkout']) {
      await assert.rejects(
        requestPayment({ provider: 'wxpay', h5_url: h5Url }),
        /H5支付地址无法打开/
      );
    }
  } finally {
    restorePlus();
    restoreUni();
    restoreWindow();
  }
});

test('keeps native payment available in an App-plus runtime with window present', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  const restorePlus = withoutGlobal('plus');
  try {
    let request;
    globalThis.window = { location: {} };
    globalThis.plus = {};
    globalThis.uni = {
      requestPayment: (options) => {
        request = options;
        options.success({ errMsg: 'requestPayment:ok' });
      }
    };

    const result = await requestPayment({
      provider: 'wxpay',
      request_payment: { prepayid: 'prepay-app' },
      status: 'PENDING'
    });

    assert.equal(request.provider, 'wxpay');
    assert.equal(result.provider, 'wxpay');
  } finally {
    restorePlus();
    restoreUni();
    restoreWindow();
  }
});

test('keeps native WeChat payment for builds without an H5 URL', async () => {
  const restoreWindow = withoutGlobal('window');
  const restoreUni = withoutGlobal('uni');
  const restorePlus = withoutGlobal('plus');
  try {
    let request;
    globalThis.uni = {
      requestPayment: (options) => {
        request = options;
        options.success({ errMsg: 'requestPayment:ok' });
      }
    };

    const result = await requestPayment({
      provider: 'wxpay',
      request_payment: { prepayid: 'prepay-1' },
      status: 'PENDING'
    });

    assert.equal(request.provider, 'wxpay');
    assert.deepEqual(request.orderInfo, { prepayid: 'prepay-1' });
    assert.equal(result.provider, 'wxpay');
  } finally {
    restorePlus();
    restoreUni();
    restoreWindow();
  }
});
