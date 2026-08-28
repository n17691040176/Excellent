import assert from 'node:assert/strict';
import test from 'node:test';

import {
  commonPaymentOptions,
  defaultPaymentOption,
  normalizePaymentOptions
} from './payment-options.js';

test('defaults to balance when sufficient and alipay when balance is unavailable', () => {
  const options = normalizePaymentOptions([
    { value: 'BALANCE', purchase_mode: 'CASH_ONLY' },
    { value: 'ALIPAY', purchase_mode: 'CASH_ONLY' }
  ]);

  assert.equal(defaultPaymentOption(options).value, 'BALANCE');

  const insufficientBalance = options.map((item) => ({
    ...item,
    available: item.value === 'BALANCE' ? false : item.available
  }));
  assert.equal(defaultPaymentOption(insufficientBalance).value, 'ALIPAY');
});

test('falls back to another available channel when balance and alipay are unavailable', () => {
  const options = [
    { value: 'BALANCE', available: false },
    { value: 'ALIPAY', available: false },
    { value: 'OTHER', available: true }
  ];

  assert.equal(defaultPaymentOption(options).value, 'OTHER');
});

test('normalizes checkout methods to balance, wechat, and alipay', () => {
  const options = normalizePaymentOptions([
    { value: 'VOUCHER', purchase_mode: 'CASH_ONLY' },
    { value: 'ALIPAY', purchase_mode: 'CASH_ONLY' }
  ]);

  assert.deepEqual(options.map((item) => item.value), ['BALANCE', 'WECHAT', 'ALIPAY']);
  assert.equal(options[0].available, true);
  assert.equal(options[1].available, false);
  assert.equal(options[1].desc, '跳转微信完成支付');
  assert.equal(options[2].available, true);
});

test('honors a configured WeChat channel and its unavailable reason', () => {
  const enabled = normalizePaymentOptions([
    {
      value: 'WECHAT',
      purchase_mode: 'CASH_ONLY',
      available: true,
      desc: '微信 H5 支付'
    }
  ]).find((item) => item.value === 'WECHAT');
  assert.equal(enabled.available, true);
  assert.equal(enabled.desc, '微信 H5 支付');
  assert.equal(enabled.unavailable_reason, '');

  const unavailable = normalizePaymentOptions([
    {
      value: 'WECHAT',
      purchase_mode: 'CASH_ONLY',
      available: false,
      unavailable_reason: '微信全局配置未就绪'
    }
  ]).find((item) => item.value === 'WECHAT');
  assert.equal(unavailable.available, false);
  assert.equal(unavailable.unavailable_reason, '微信全局配置未就绪');
});

test('requires alipay to be available for every product in a combined checkout', () => {
  const options = commonPaymentOptions([
    { payment_options: [{ value: 'ALIPAY', purchase_mode: 'CASH_ONLY' }] },
    { payment_options: [] }
  ]);

  assert.equal(options.find((item) => item.value === 'ALIPAY').available, false);
});

test('preserves backend payment availability and reason', () => {
  const options = normalizePaymentOptions([
    {
      value: 'ALIPAY',
      purchase_mode: 'CASH_ONLY',
      available: false,
      unavailable_reason: '后台未开启支付宝支付'
    }
  ]);
  const alipay = options.find((item) => item.value === 'ALIPAY');

  assert.equal(alipay.available, false);
  assert.equal(alipay.unavailable_reason, '后台未开启支付宝支付');
});
