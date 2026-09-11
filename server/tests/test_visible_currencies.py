from decimal import Decimal as D

from test_city_partner import db as shared_db
from test_city_partner import user

from app.api.v1.assets import summary
from app.models.asset import UserAssetAccount
from app.models.commission import UserCommission
from app.models.enums import AssetType
from app.services.asset_service import AssetService
from app.services.page_decoration_service import PageDecorationService
from app.utils.helpers import now

# Re-export the shared pytest fixture without shadowing an unused import.
db = shared_db


def test_public_summary_only_exposes_three_currencies_without_changing_hidden_accounts(db, monkeypatch):
    buyer = user(db)
    for asset_type, amount in [(AssetType.BALANCE, 10), (AssetType.POINTS, 20),
                               (AssetType.VOUCHER, 900), (AssetType.AI_COUPON, 800)]:
        db.add(UserAssetAccount(user_id=buyer.id, asset_type=asset_type, available_amount=amount,
                               total_amount=amount, updated_at=now()))
    commission = db.query(UserCommission).filter_by(user_id=buyer.id).one()
    commission.available_amount = D('30')
    commission.frozen_amount = D('40')
    commission.total_amount = D('70')
    db.commit()
    monkeypatch.setattr(AssetService, 'ensure_user_asset_accounts', lambda *_: False)
    monkeypatch.setattr(AssetService, 'settle_power_bank_income', lambda *_: None)
    result = summary(db, buyer)['data']
    assert result == {'BALANCE': 10, 'COMMISSION': 30, 'POINTS': 20, 'balance': 10,
                      'commission': 30, 'points': 20, 'total_amount': 60}
    assert db.query(UserAssetAccount).filter_by(user_id=buyer.id, asset_type=AssetType.VOUCHER).one().available_amount == 900
    assert commission.available_amount == 30 and commission.frozen_amount == 40


def test_saved_builtin_home_copy_hides_retired_currencies_without_mutation():
    original = PageDecorationService.default_mobile_uni_home_payload()
    asset_item = next(item for item in original['quick_section']['items'] if item['title'] == '我的资产')
    asset_item['desc'] = '查看余额、消费金、积分和充电宝'
    original['zone_section']['items'][1]['tip'] = '兑换券 5-7 折抵扣，返 AI 券'
    displayed = PageDecorationService.normalize_mobile_uni_home_payload(original)
    assert next(item for item in displayed['quick_section']['items'] if item['title'] == '我的资产')['desc'] == '查看余额、佣金和积分'
    assert displayed['zone_section']['items'][1]['tip'] == '精选商品，支持余额和积分'
    assert asset_item['desc'] == '查看余额、消费金、积分和充电宝'
