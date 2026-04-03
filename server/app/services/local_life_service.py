from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import AssetType, OrderStatus, OrderType, PayStatus, ZoneType
from app.models.local_life import (
    AdRevenueFlow,
    DeviceRevenueFlow,
    LocalLifeMerchant,
    LocalLifeOrder,
    LocalLifeService,
    MerchantCommissionRule,
    MerchantStore,
)
from app.models.order import Order, OrderAssetDeduction
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.services.commission_service import CommissionService
from app.utils.helpers import generate_code, generate_order_no, now, quantize_amount


class LocalLifeServiceLayer:
    @staticmethod
    def list_merchants(db: Session) -> list[LocalLifeMerchant]:
        return db.query(LocalLifeMerchant).filter(LocalLifeMerchant.status == 'ACTIVE').order_by(LocalLifeMerchant.id.desc()).all()

    @staticmethod
    def get_merchant(db: Session, merchant_id: int) -> LocalLifeMerchant:
        merchant = db.get(LocalLifeMerchant, merchant_id)
        if not merchant:
            raise NotFoundError('Merchant not found')
        return merchant

    @staticmethod
    def list_stores(db: Session, merchant_id: int) -> list[MerchantStore]:
        return db.query(MerchantStore).filter(
            MerchantStore.merchant_id == merchant_id,
            MerchantStore.status == 'ACTIVE',
        ).order_by(MerchantStore.id.desc()).all()

    @staticmethod
    def list_services(db: Session, merchant_id: int | None = None) -> list[LocalLifeService]:
        query = db.query(LocalLifeService).filter(LocalLifeService.status == 'ON_SHELF')
        if merchant_id is not None:
            query = query.filter(LocalLifeService.merchant_id == merchant_id)
        return query.order_by(LocalLifeService.id.desc()).all()

    @staticmethod
    def get_service(db: Session, service_id: int) -> LocalLifeService:
        service = db.get(LocalLifeService, service_id)
        if not service:
            raise NotFoundError('Service not found')
        return service

    @staticmethod
    def _validate_merchant_payload(payload: dict) -> None:
        if not payload.get('merchant_name'):
            raise ConflictError('Merchant name required')
        if not payload.get('category_name'):
            raise ConflictError('Category name required')
        if not payload.get('contact_phone'):
            raise ConflictError('Contact phone required')
        if payload.get('status') not in {'PENDING', 'ACTIVE', 'DISABLED'}:
            raise ConflictError('Merchant status invalid')

    @staticmethod
    def _validate_store_payload(payload: dict) -> None:
        if not payload.get('store_name'):
            raise ConflictError('Store name required')
        if payload.get('status') not in {'ACTIVE', 'DISABLED'}:
            raise ConflictError('Store status invalid')

    @staticmethod
    def _validate_service_payload(payload: dict) -> None:
        if not payload.get('service_name'):
            raise ConflictError('Service name required')
        if payload.get('sale_price', 0) <= 0:
            raise ConflictError('Service sale price must be greater than 0')
        if payload.get('market_price') is not None and payload['market_price'] < payload['sale_price']:
            raise ConflictError('Service market price cannot be less than sale price')
        if not payload.get('service_type'):
            raise ConflictError('Service type required')
        if not payload.get('verification_type'):
            raise ConflictError('Verification type required')
        if payload.get('status') not in {'ON_SHELF', 'OFF_SHELF'}:
            raise ConflictError('Service status invalid')

    @staticmethod
    def _validate_rule_payload(payload: dict) -> None:
        total = 0
        for field in ['county_agent_rate', 'city_agent_rate', 'user_rate', 'merchant_rate', 'device_rate', 'ad_rate']:
            value = payload.get(field, 0)
            if value < 0 or value > 100:
                raise ConflictError(f'{field} must be between 0 and 100')
            total += value
        if total > 100:
            raise ConflictError('Commission rule total rate cannot exceed 100')

    @staticmethod
    def _resolve_owner_user_id(db: Session, current_user: User, owner_user_id: int | None) -> int:
        resolved_owner_user_id = owner_user_id or current_user.id
        owner_user = db.get(User, resolved_owner_user_id)
        if not owner_user:
            raise NotFoundError('Merchant owner user not found')
        if not AdminScopeService.is_super_admin(current_user):
            AdminScopeService.ensure_user_visible(current_user, owner_user)
        return resolved_owner_user_id

    @staticmethod
    def _ensure_merchant_visible_for_admin(db: Session, merchant_id: int, current_user: User) -> LocalLifeMerchant:
        merchant = db.get(LocalLifeMerchant, merchant_id)
        if not merchant:
            raise NotFoundError('Merchant not found')
        if not AdminScopeService.is_super_admin(current_user):
            owner_user = db.get(User, merchant.owner_user_id) if merchant.owner_user_id else None
            if owner_user:
                AdminScopeService.ensure_user_visible(current_user, owner_user)
            elif merchant.owner_user_id:
                raise NotFoundError('Merchant owner not found')
        return merchant

    @staticmethod
    def _ensure_store_visible_for_admin(db: Session, store_id: int, current_user: User) -> MerchantStore:
        store = db.get(MerchantStore, store_id)
        if not store:
            raise NotFoundError('Store not found')
        LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, store.merchant_id, current_user)
        return store

    @staticmethod
    def _ensure_service_visible_for_admin(db: Session, service_id: int, current_user: User) -> LocalLifeService:
        service = db.get(LocalLifeService, service_id)
        if not service:
            raise NotFoundError('Service not found')
        LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, service.merchant_id, current_user)
        return service

    @staticmethod
    def _ensure_rule_visible_for_admin(db: Session, rule_id: int, current_user: User) -> MerchantCommissionRule:
        rule = db.get(MerchantCommissionRule, rule_id)
        if not rule:
            raise NotFoundError('Commission rule not found')
        if rule.merchant_id:
            LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, rule.merchant_id, current_user)
        return rule

    @staticmethod
    def create_merchant_for_admin(db: Session, current_user: User, payload: dict) -> LocalLifeMerchant:
        LocalLifeServiceLayer._validate_merchant_payload(payload)
        merchant = LocalLifeMerchant(
            owner_user_id=LocalLifeServiceLayer._resolve_owner_user_id(db, current_user, payload.get('owner_user_id')),
            merchant_name=payload['merchant_name'],
            category_name=payload['category_name'],
            contact_phone=payload['contact_phone'],
            city_code=payload.get('city_code'),
            status=payload.get('status', 'PENDING'),
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        return merchant

    @staticmethod
    def update_merchant_for_admin(db: Session, merchant_id: int, current_user: User, payload: dict) -> LocalLifeMerchant:
        merchant = LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, merchant_id, current_user)
        LocalLifeServiceLayer._validate_merchant_payload(payload)
        merchant.owner_user_id = LocalLifeServiceLayer._resolve_owner_user_id(db, current_user, payload.get('owner_user_id'))
        merchant.merchant_name = payload['merchant_name']
        merchant.category_name = payload['category_name']
        merchant.contact_phone = payload['contact_phone']
        merchant.city_code = payload.get('city_code')
        merchant.status = payload.get('status', merchant.status)
        db.commit()
        db.refresh(merchant)
        return merchant

    @staticmethod
    def delete_merchant_for_admin(db: Session, merchant_id: int, current_user: User) -> None:
        merchant = LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, merchant_id, current_user)
        if db.query(MerchantStore).filter(MerchantStore.merchant_id == merchant.id).count() > 0:
            raise ConflictError('Merchant with stores cannot be deleted')
        if db.query(LocalLifeService).filter(LocalLifeService.merchant_id == merchant.id).count() > 0:
            raise ConflictError('Merchant with services cannot be deleted')
        if db.query(MerchantCommissionRule).filter(MerchantCommissionRule.merchant_id == merchant.id).count() > 0:
            raise ConflictError('Merchant with commission rules cannot be deleted')
        db.delete(merchant)
        db.commit()

    @staticmethod
    def create_store_for_admin(db: Session, current_user: User, payload: dict) -> MerchantStore:
        LocalLifeServiceLayer._validate_store_payload(payload)
        merchant = LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, payload['merchant_id'], current_user)
        store = MerchantStore(
            merchant_id=merchant.id,
            store_name=payload['store_name'],
            contact_phone=payload.get('contact_phone'),
            province=payload.get('province'),
            city=payload.get('city'),
            district=payload.get('district'),
            detail_address=payload.get('detail_address'),
            latitude=payload.get('latitude'),
            longitude=payload.get('longitude'),
            status=payload.get('status', 'ACTIVE'),
            created_at=now(),
        )
        db.add(store)
        db.commit()
        db.refresh(store)
        return store

    @staticmethod
    def update_store_for_admin(db: Session, store_id: int, current_user: User, payload: dict) -> MerchantStore:
        store = LocalLifeServiceLayer._ensure_store_visible_for_admin(db, store_id, current_user)
        LocalLifeServiceLayer._validate_store_payload(payload)
        merchant = LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, payload['merchant_id'], current_user)
        store.merchant_id = merchant.id
        store.store_name = payload['store_name']
        store.contact_phone = payload.get('contact_phone')
        store.province = payload.get('province')
        store.city = payload.get('city')
        store.district = payload.get('district')
        store.detail_address = payload.get('detail_address')
        store.latitude = payload.get('latitude')
        store.longitude = payload.get('longitude')
        store.status = payload.get('status', store.status)
        db.commit()
        db.refresh(store)
        return store

    @staticmethod
    def delete_store_for_admin(db: Session, store_id: int, current_user: User) -> None:
        store = LocalLifeServiceLayer._ensure_store_visible_for_admin(db, store_id, current_user)
        if db.query(LocalLifeService).filter(LocalLifeService.store_id == store.id).count() > 0:
            raise ConflictError('Store with services cannot be deleted')
        db.delete(store)
        db.commit()

    @staticmethod
    def create_service_for_admin(db: Session, current_user: User, payload: dict) -> LocalLifeService:
        LocalLifeServiceLayer._validate_service_payload(payload)
        merchant = LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, payload['merchant_id'], current_user)
        if payload.get('store_id'):
            store = LocalLifeServiceLayer._ensure_store_visible_for_admin(db, payload['store_id'], current_user)
            if store.merchant_id != merchant.id:
                raise ConflictError('Store does not belong to merchant')
        service = LocalLifeService(
            merchant_id=merchant.id,
            store_id=payload.get('store_id'),
            service_name=payload['service_name'],
            market_price=payload.get('market_price'),
            sale_price=payload['sale_price'],
            service_type=payload['service_type'],
            verification_type=payload['verification_type'],
            status=payload.get('status', 'ON_SHELF'),
            created_at=now(),
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def update_service_for_admin(db: Session, service_id: int, current_user: User, payload: dict) -> LocalLifeService:
        service = LocalLifeServiceLayer._ensure_service_visible_for_admin(db, service_id, current_user)
        LocalLifeServiceLayer._validate_service_payload(payload)
        merchant = LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, payload['merchant_id'], current_user)
        if payload.get('store_id'):
            store = LocalLifeServiceLayer._ensure_store_visible_for_admin(db, payload['store_id'], current_user)
            if store.merchant_id != merchant.id:
                raise ConflictError('Store does not belong to merchant')
        service.merchant_id = merchant.id
        service.store_id = payload.get('store_id')
        service.service_name = payload['service_name']
        service.market_price = payload.get('market_price')
        service.sale_price = payload['sale_price']
        service.service_type = payload['service_type']
        service.verification_type = payload['verification_type']
        service.status = payload.get('status', service.status)
        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def delete_service_for_admin(db: Session, service_id: int, current_user: User) -> None:
        service = LocalLifeServiceLayer._ensure_service_visible_for_admin(db, service_id, current_user)
        if db.query(LocalLifeOrder).filter(LocalLifeOrder.service_id == service.id).count() > 0:
            raise ConflictError('Service with orders cannot be deleted')
        db.delete(service)
        db.commit()

    @staticmethod
    def create_rule_for_admin(db: Session, current_user: User, payload: dict) -> MerchantCommissionRule:
        LocalLifeServiceLayer._validate_rule_payload(payload)
        merchant_id = payload.get('merchant_id')
        if merchant_id:
            LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, merchant_id, current_user)
        rule = MerchantCommissionRule(**payload)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def update_rule_for_admin(db: Session, rule_id: int, current_user: User, payload: dict) -> MerchantCommissionRule:
        rule = LocalLifeServiceLayer._ensure_rule_visible_for_admin(db, rule_id, current_user)
        LocalLifeServiceLayer._validate_rule_payload(payload)
        merchant_id = payload.get('merchant_id')
        if merchant_id:
            LocalLifeServiceLayer._ensure_merchant_visible_for_admin(db, merchant_id, current_user)
        for field, value in payload.items():
            setattr(rule, field, value)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete_rule_for_admin(db: Session, rule_id: int, current_user: User) -> None:
        rule = LocalLifeServiceLayer._ensure_rule_visible_for_admin(db, rule_id, current_user)
        db.delete(rule)
        db.commit()

    @staticmethod
    def create_order(
        db: Session,
        user_id: int,
        service_id: int,
        store_id: int | None = None,
        quantity: int = 1,
        points_amount: float = 0,
        balance_amount: float = 0,
    ) -> Order:
        service = LocalLifeServiceLayer.get_service(db, service_id)
        buyer = db.get(User, user_id)
        if not buyer:
            raise NotFoundError('User not found')
        if quantity <= 0:
            raise ConflictError('Quantity must be positive')
        if service.status != 'ON_SHELF':
            raise ConflictError('Service unavailable')
        total_amount = quantize_amount(Decimal(str(service.sale_price)) * Decimal(str(quantity)))
        requested_discount = quantize_amount(points_amount) + quantize_amount(balance_amount)
        if requested_discount > total_amount:
            raise ConflictError('Local life asset deduction exceeds order amount')
        order = Order(
            order_no=generate_order_no('LL'),
            user_id=user_id,
            team_id=buyer.team_id,
            order_type=OrderType.LOCAL_LIFE_ORDER,
            zone_type=ZoneType.LOCAL_LIFE,
            source_ref_id=service.id,
            total_amount=total_amount,
            discount_amount=0,
            payable_amount=total_amount,
            paid_amount=0,
            pay_status=PayStatus.UNPAID,
            order_status=OrderStatus.CREATED,
        )
        db.add(order)
        db.flush()

        discount_amount = Decimal('0.00')
        for asset_type, amount in ((AssetType.POINTS, points_amount), (AssetType.BALANCE, balance_amount)):
            q_amount = quantize_amount(amount)
            if q_amount <= 0:
                continue
            AssetService.consume_amount(
                db,
                user_id,
                asset_type,
                q_amount,
                'LOCAL_LIFE_DEDUCT',
                source_id=order.id,
                source_no=order.order_no,
            )
            discount_amount += q_amount
            db.add(
                OrderAssetDeduction(
                    order_id=order.id,
                    asset_type=asset_type.value,
                    deduct_amount=q_amount,
                    created_at=now(),
                )
            )

        order.discount_amount = discount_amount
        order.payable_amount = max(total_amount - discount_amount, Decimal('0.00'))
        order.paid_amount = order.payable_amount

        db.add(
            LocalLifeOrder(
                order_id=order.id,
                merchant_id=service.merchant_id,
                store_id=store_id or service.store_id,
                service_id=service.id,
                verification_code=generate_code('VF', 6),
                created_at=now(),
            )
        )
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def my_orders(db: Session, user_id: int) -> list[Order]:
        return db.query(Order).filter(Order.user_id == user_id, Order.order_type == OrderType.LOCAL_LIFE_ORDER).order_by(Order.id.desc()).all()

    @staticmethod
    def get_order_detail(db: Session, user_id: int, order_id: int) -> dict:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id,
            Order.order_type == OrderType.LOCAL_LIFE_ORDER,
        ).first()
        if not order:
            raise NotFoundError('Local life order not found')

        local_order = db.query(LocalLifeOrder).filter(LocalLifeOrder.order_id == order.id).first()
        service = db.get(LocalLifeService, local_order.service_id) if local_order else None
        merchant = db.get(LocalLifeMerchant, local_order.merchant_id) if local_order else None
        store = db.get(MerchantStore, local_order.store_id) if local_order and local_order.store_id else None
        return {
            'order': order,
            'local_order': local_order,
            'service': service,
            'merchant': merchant,
            'store': store,
        }

    @staticmethod
    def list_orders(db: Session) -> list[Order]:
        return db.query(Order).filter(Order.order_type == OrderType.LOCAL_LIFE_ORDER).order_by(Order.id.desc()).all()

    @staticmethod
    def verify_order(db: Session, verification_code: str, current_user: User) -> LocalLifeOrder:
        local_order = db.query(LocalLifeOrder).filter(LocalLifeOrder.verification_code == verification_code).first()
        if not local_order:
            raise NotFoundError('Verification code invalid')
        if local_order.verified_at:
            raise ConflictError('Order already verified')

        order = db.get(Order, local_order.order_id)
        if order:
            AdminScopeService.ensure_team_visible(current_user, order.team_id)

        local_order.verified_at = now()
        if order:
            if order.pay_status != PayStatus.PAID:
                order.pay_status = PayStatus.PAID
                order.order_status = OrderStatus.PAID
                order.paid_at = now()
                buyer = db.get(User, order.user_id)
                if buyer:
                    CommissionService.freeze_for_order(db, order, buyer)
            order.order_status = OrderStatus.CONFIRMED
            order.confirmed_at = now()

        db.commit()
        if order:
            CommissionService.settle_for_order(db, order.id)
        db.refresh(local_order)
        return local_order

    @staticmethod
    def revenue_summary(db: Session, user_id: int) -> dict:
        device_total = sum(float(item.amount) for item in db.query(DeviceRevenueFlow).filter(DeviceRevenueFlow.beneficiary_user_id == user_id).all())
        ad_total = sum(float(item.amount) for item in db.query(AdRevenueFlow).filter(AdRevenueFlow.beneficiary_user_id == user_id).all())
        return {
            'device_revenue_total': device_total,
            'ad_revenue_total': ad_total,
            'balance_revenue_total': device_total + ad_total,
        }

    @staticmethod
    def list_merchants_for_admin(db: Session, current_user: User) -> list[LocalLifeMerchant]:
        query = db.query(LocalLifeMerchant)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(LocalLifeMerchant.owner_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        return query.order_by(LocalLifeMerchant.id.desc()).all()

    @staticmethod
    def list_stores_for_admin(db: Session, current_user: User) -> list[MerchantStore]:
        query = db.query(MerchantStore)
        if not AdminScopeService.is_super_admin(current_user):
            merchant_ids = db.query(LocalLifeMerchant.id).filter(
                LocalLifeMerchant.owner_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user))
            )
            query = query.filter(MerchantStore.merchant_id.in_(merchant_ids))
        return query.order_by(MerchantStore.id.desc()).all()

    @staticmethod
    def list_services_for_admin(db: Session, current_user: User, merchant_id: int | None = None) -> list[LocalLifeService]:
        query = db.query(LocalLifeService)
        if merchant_id is not None:
            query = query.filter(LocalLifeService.merchant_id == merchant_id)
        if not AdminScopeService.is_super_admin(current_user):
            merchant_ids = db.query(LocalLifeMerchant.id).filter(
                LocalLifeMerchant.owner_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user))
            )
            query = query.filter(LocalLifeService.merchant_id.in_(merchant_ids))
        return query.order_by(LocalLifeService.id.desc()).all()

    @staticmethod
    def list_orders_for_admin(db: Session, current_user: User) -> list[LocalLifeOrder]:
        query = db.query(LocalLifeOrder).join(Order, LocalLifeOrder.order_id == Order.id)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(Order.team_id == AdminScopeService.require_team_id(current_user))
        return query.order_by(LocalLifeOrder.id.desc()).all()

    @staticmethod
    def list_commission_rules_for_admin(db: Session, current_user: User) -> list[MerchantCommissionRule]:
        query = db.query(MerchantCommissionRule)
        if not AdminScopeService.is_super_admin(current_user):
            merchant_ids = db.query(LocalLifeMerchant.id).filter(
                LocalLifeMerchant.owner_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user))
            )
            query = query.filter(MerchantCommissionRule.merchant_id.in_(merchant_ids))
        return query.order_by(MerchantCommissionRule.id.desc()).all()

    @staticmethod
    def list_device_revenues_for_admin(db: Session, current_user: User) -> list[DeviceRevenueFlow]:
        query = db.query(DeviceRevenueFlow)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(DeviceRevenueFlow.beneficiary_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        return query.order_by(DeviceRevenueFlow.id.desc()).all()

    @staticmethod
    def list_ad_revenues_for_admin(db: Session, current_user: User) -> list[AdRevenueFlow]:
        query = db.query(AdRevenueFlow)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(AdRevenueFlow.beneficiary_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        return query.order_by(AdRevenueFlow.id.desc()).all()

    @staticmethod
    def list_commission_rules(db: Session) -> list[MerchantCommissionRule]:
        return db.query(MerchantCommissionRule).order_by(MerchantCommissionRule.id.desc()).all()
