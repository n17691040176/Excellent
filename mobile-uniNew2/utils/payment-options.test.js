import assert from 'node:assert/strict';
import test from 'node:test';

import { commonPaymentOptions, normalizePaymentOptions } from './payment-options.js';

test('normalizes checkout methods to balance, wechat, and alipay', () => {
  const options = normalizePaymentOptions([
    { value: 'VOUCHER', purchase_mode: 'CASH_ONLY' },
    { value: 'ALIPAY', purchase_mode: 'CASH_ONLY' }
  ]);

  assert.deepEqual(options.map((item) => item.value), ['BALANCE', 'WECHAT', 'ALIPAY']);
  assert.equal(options[0].available, true);
  assert.equal(options[1].available, false);
  assert.equal(options[1].desc, '正在开发');
  assert.equal(options[2].available, true);
});

test('requires alipay to be available for every product in a combined checkout', () => {
  const options = commonPaymentOptions([
    { payment_options: [{ value: 'ALIPAY', purchase_mode: 'CASH_ONLY' }] },
    { payment_options: [] }
  ]);

  assert.equal(options.find((item) => item.value === 'ALIPAY').available, false);
});
