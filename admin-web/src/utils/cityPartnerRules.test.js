import assert from 'node:assert/strict'
import test from 'node:test'
import { cityPartnerUplineAmounts } from './cityPartnerRules.js'

test('手动设置七级各 0.20 元，不受直推金额影响', () => {
  for (const direct of [0, 0.01, 1, 400]) {
    assert.deepEqual(cityPartnerUplineAmounts({ city_partner_upline_mode: 'MANUAL', city_partner_upline_amounts: Array(7).fill('0.20'), city_partner_direct_reward_amount: direct }), Array(7).fill(0.2))
  }
})

test('七级金额可独立配置，切回自动时只读取直推金额', () => {
  const config = { city_partner_upline_mode: 'MANUAL', city_partner_upline_amounts: ['0', '0.01', '0.2', '1', '2', '3', '4'], city_partner_direct_reward_amount: 400 }
  assert.deepEqual(cityPartnerUplineAmounts(config), [0, 0.01, 0.2, 1, 2, 3, 4])
  config.city_partner_upline_mode = 'AUTO'
  assert.deepEqual(cityPartnerUplineAmounts(config), [200, 100, 50, 25, 12.5, 6.25, 3.12])
})

test('普通商品保留逐级减半并舍去分以下金额', () => {
  assert.deepEqual(cityPartnerUplineAmounts({ city_partner_direct_reward_amount: 400 }), [200, 100, 50, 25, 12.5, 6.25, 3.12])
  assert.deepEqual(cityPartnerUplineAmounts({ city_partner_direct_reward_amount: 1.01 }), [0.5, 0.25, 0.12, 0.06, 0.03, 0.01, 0])
  assert.deepEqual(cityPartnerUplineAmounts(), Array(7).fill(0))
})
