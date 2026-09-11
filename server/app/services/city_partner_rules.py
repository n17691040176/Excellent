from decimal import ROUND_DOWN, Decimal, localcontext

from app.core.exceptions import ConflictError
from app.utils.helpers import quantize_amount

CITY_PARTNER_DEFAULTS = {
    'city_partner_commission_enabled': False,
    'city_partner_commission_rule_version': 'v1',
    'city_partner_amount': 0,
    'city_partner_direct_reward_amount': 0,
    'city_partner_upline_initial_amount': 0,
    'city_partner_upline_max_levels': 7,
    'city_partner_upline_decay_rate': 50,
    'city_partner_remainder_account': 'COMPANY',
    'city_partner_calculation_policy': 'DIRECT_HALVING_7_V2',
}


class CityPartnerSettlementError(ConflictError):
    """Business rejection with immutable payment-time inputs for manual refund."""

    def __init__(self, message, order_snapshot):
        super().__init__(message)
        self.order_snapshot = order_snapshot


def city_partner_rule_values(config) -> dict:
    values = {}
    for key, default in CITY_PARTNER_DEFAULTS.items():
        value = config.get(key) if isinstance(config, dict) else getattr(config, key, None)
        values[key] = default if value is None else value
    # These are derived output fields. Historical stored knobs never control
    # new payments; already-paid orders settle from their existing flows.
    direct = Decimal(str(values['city_partner_direct_reward_amount']))
    values['city_partner_upline_initial_amount'] = (direct / 2).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if direct.is_finite() else Decimal(0)
    values['city_partner_upline_max_levels'] = 7
    values['city_partner_upline_decay_rate'] = Decimal('50')
    values['city_partner_calculation_policy'] = 'DIRECT_HALVING_7_V2'
    return values


def upline_amounts(config) -> list[Decimal]:
    return [rounded for _, rounded in upline_calculations(config)]


def upline_calculations(config, quantity=1) -> list[tuple[Decimal, Decimal]]:
    values = city_partner_rule_values(config)
    with localcontext() as context:
        context.prec = 60
        amount = Decimal(str(values['city_partner_direct_reward_amount'])) / 2
        decay = Decimal('0.5')
        amounts = []
        for _ in range(int(values['city_partner_upline_max_levels'])):
            amounts.append((amount * quantity, amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN) * quantity))
            amount *= decay
    return amounts


def validate_city_partner_rule(config, sale_price, cost_price) -> None:
    values = city_partner_rule_values(config)
    for field in ('city_partner_amount', 'city_partner_direct_reward_amount'):
        amount = Decimal(str(values[field]))
        if not amount.is_finite() or amount < 0 or amount != quantize_amount(amount):
            raise ConflictError('City partner amounts must be non-negative amounts with at most two decimal places')
    if values['city_partner_remainder_account'] != 'COMPANY':
        raise ConflictError('City partner remainder account must be COMPANY')
    if not values['city_partner_commission_enabled']:
        return
    if cost_price is None:
        raise ConflictError('Product cost is required for city partner commission')
    sale, cost = Decimal(str(sale_price)), Decimal(str(cost_price))
    if not sale.is_finite() or not cost.is_finite() or sale <= 0 or cost < 0:
        raise ConflictError('Product sale and cost must be valid non-negative money amounts')
    total = sum(upline_amounts(values), Decimal('0'))
    total += Decimal(str(values['city_partner_amount'])) + Decimal(str(values['city_partner_direct_reward_amount']))
    pool = quantize_amount(sale_price) - quantize_amount(cost_price)
    if total > pool:
        raise ConflictError('City partner commission exceeds product profit pool')
