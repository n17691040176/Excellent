export function cityPartnerUplineAmounts({ city_partner_upline_mode = 'AUTO', city_partner_upline_amounts = [], city_partner_direct_reward_amount = 0 } = {}) {
  if (city_partner_upline_mode === 'MANUAL') {
    return Array.from({ length: 7 }, (_, index) => Number(city_partner_upline_amounts[index] || 0))
  }
  const directCents = Math.round(Number(city_partner_direct_reward_amount) * 100)
  return Array.from({ length: 7 }, (_, index) => Math.floor(directCents / (2 ** (index + 1))) / 100)
}
