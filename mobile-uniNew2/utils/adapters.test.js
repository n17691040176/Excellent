import assert from 'node:assert/strict';
import test from 'node:test';

import { toOrderView, toProfileOverview } from './adapters.js';

test('visible assets exclude hidden currencies and include available commission', () => {
  const view = toProfileOverview({}, {}, { BALANCE: 10, POINTS: 20, COMMISSION: 30, VOUCHER: 900, AI_COUPON: 800, total_amount: 1730 });
  assert.equal(view.totalAsset, '60.00');
});

test('keeps the recorded payment channel ahead of available-channel defaults', () => {
  const order = toOrderView({
    id: 42,
    order_no: 'ORDER-42',
    status_text: '待支付',
    pay_status: 'UNPAID',
    cash_due: 12,
    pay_channel: 'WECHAT',
    default_pay_channel: 'ALIPAY',
    pay_channel_options: ['BALANCE', 'WECHAT', 'ALIPAY'],
    can_pay: true
  });

  assert.equal(order.payChannel, 'WECHAT');
});

test('normalizes provider aliases when selecting a recorded channel', () => {
  const order = toOrderView({
    id: 43,
    pay_channel: 'wxpay',
    default_pay_channel: 'ALIPAY',
    pay_channel_options: ['ALIPAY'],
    cash_due: 9,
    can_pay: true
  });

  assert.equal(order.payChannel, 'WECHAT');
});
