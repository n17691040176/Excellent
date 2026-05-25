from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import (
    AgentLevelCode,
    BusinessIdentity,
    OrderType,
    PayStatus,
    ProductOwnerType,
    QualificationStatus,
    QualificationType,
    SupplierStatus,
)
from app.models.order import Order, OrderItem
from app.models.package import Package
from app.models.product import Product, ProductQualification
from app.models.supplier import AgentLevel, AgentQualification, Supplier, SupplierAgreement, SupplierEntryOrder
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.utils.helpers import generate_order_no, now, quantize_amount


class SupplierService:
    PRICE_LIMIT_RATE = Decimal('0.20')

    @staticmethod
    def apply_supplier(db: Session, current_user: User, payload: dict) -> Supplier:
        base_price = payload.get('base_product_price') or 0
        entry_fee = max(Decimal('500.00'), quantize_amount(base_price))
        supplier = Supplier(
            user_id=current_user.id,
            supplier_name=payload['supplier_name'],
            contact_name=payload['contact_name'],
            contact_phone=payload['contact_phone'],
            qualification_desc=payload.get('qualification_desc'),
            entry_fee_amount=entry_fee,
            referral_user_id=current_user.parent_id,
            status=SupplierStatus.PENDING,
        )
        db.add(supplier)
        db.flush()
        db.add(
            SupplierEntryOrder(
                supplier_id=supplier.id,
                order_no=generate_order_no('SE'),
                base_product_price=base_price or None,
                entry_fee_amount=entry_fee,
                referral_user_id=current_user.parent_id,
                referral_reward_amount=quantize_amount(entry_fee * Decimal('0.15')) if current_user.parent_id else 0,
                status='CREATED',
                created_at=now(),
            )
        )
        db.commit()
        db.refresh(supplier)
        return supplier

    @staticmethod
    def my_suppliers(db: Session, user_id: int) -> list[Supplier]:
        return db.query(Supplier).filter(Supplier.user_id == user_id).order_by(Supplier.id.desc()).all()

    @staticmethod
    def _get_latest_entry_order(db: Session, supplier_id: int) -> SupplierEntryOrder | None:
        return db.query(SupplierEntryOrder).filter(
            SupplierEntryOrder.supplier_id == supplier_id,
        ).order_by(SupplierEntryOrder.id.desc()).first()

    @staticmethod
    def _get_latest_paid_entry_order(db: Session, supplier_id: int) -> SupplierEntryOrder | None:
        return db.query(SupplierEntryOrder).filter(
            SupplierEntryOrder.supplier_id == supplier_id,
            SupplierEntryOrder.status == 'PAID',
        ).order_by(SupplierEntryOrder.id.desc()).first()

    @staticmethod
    def _get_active_supplier_agreement(db: Session, supplier_id: int) -> SupplierAgreement | None:
        return db.query(SupplierAgreement).filter(
            SupplierAgreement.supplier_id == supplier_id,
            SupplierAgreement.is_active.is_(True),
        ).order_by(SupplierAgreement.id.desc()).first()

    @staticmethod
    def _serialize_supplier_for_admin(db: Session, supplier: Supplier) -> dict:
        latest_entry_order = SupplierService._get_latest_entry_order(db, supplier.id)
        active_agreement = SupplierService._get_active_supplier_agreement(db, supplier.id)
        approved_qualification_count = int(
            db.query(func.count(ProductQualification.id)).filter(
                ProductQualification.supplier_id == supplier.id,
                ProductQualification.audit_status == QualificationStatus.APPROVED,
            ).scalar() or 0
        )
        pending_qualification_count = int(
            db.query(func.count(ProductQualification.id)).filter(
                ProductQualification.supplier_id == supplier.id,
                ProductQualification.audit_status == QualificationStatus.PENDING,
            ).scalar() or 0
        )
        return {
            'id': supplier.id,
            'user_id': supplier.user_id,
            'supplier_name': supplier.supplier_name,
            'contact_name': supplier.contact_name,
            'contact_phone': supplier.contact_phone,
            'qualification_desc': supplier.qualification_desc,
            'entry_fee_amount': float(supplier.entry_fee_amount),
            'entry_fee_paid': bool(supplier.entry_fee_paid),
            'referral_user_id': supplier.referral_user_id,
            'status': supplier.status.value,
            'created_at': supplier.created_at.isoformat() if getattr(supplier, 'created_at', None) else None,
            'updated_at': supplier.updated_at.isoformat() if getattr(supplier, 'updated_at', None) else None,
            'active_agreement': bool(active_agreement),
            'agreement_type': active_agreement.agreement_type if active_agreement else None,
            'agreement_signed_at': active_agreement.signed_at.isoformat() if active_agreement and active_agreement.signed_at else None,
            'latest_entry_order_status': latest_entry_order.status if latest_entry_order else None,
            'latest_entry_order_paid_at': latest_entry_order.paid_at.isoformat() if latest_entry_order and latest_entry_order.paid_at else None,
            'approved_qualification_count': approved_qualification_count,
            'pending_qualification_count': pending_qualification_count,
        }

    @staticmethod
    def list_for_admin(db: Session, current_user: User) -> list[dict]:
        query = db.query(Supplier)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(Supplier.user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        rows = query.order_by(Supplier.id.desc()).all()
        return [SupplierService._serialize_supplier_for_admin(db, row) for row in rows]

    @staticmethod
    def add_agreement(db: Session, supplier_id: int, agreement_type: str, file_url: str) -> SupplierAgreement:
        supplier = db.get(Supplier, supplier_id)
        if not supplier:
            raise NotFoundError('Supplier not found')
        agreement = SupplierAgreement(
            supplier_id=supplier_id,
            agreement_type=agreement_type,
            file_url=file_url,
            signed_at=now(),
            created_at=now(),
        )
        db.add(agreement)
        db.commit()
        db.refresh(agreement)
        return agreement

    @staticmethod
    def _format_qualification_type_label(qualification_type: QualificationType) -> str:
        return {
            QualificationType.ENTRY_FEE: '入场费资格',
            QualificationType.PACKAGE_QUOTA: '套餐上架额度',
            QualificationType.AGENT_QUALIFICATION: '代理上架额度',
        }[qualification_type]

    @staticmethod
    def _build_product_compliance_snapshot(product: Product | None) -> dict:
        if not product:
            return {
                'drop_shipping_enabled': False,
                'price_limit_ok': False,
                'market_price': None,
                'sale_price': None,
                'price_ratio': None,
                'summary': '商品不存在',
            }

        market_price = quantize_amount(product.market_price) if product.market_price is not None else None
        sale_price = quantize_amount(product.sale_price)
        price_ratio = None
        price_limit_ok = False
        if market_price and market_price > 0:
            price_ratio = (sale_price / market_price * Decimal('100')).quantize(Decimal('0.01'))
            price_limit_ok = sale_price <= quantize_amount(market_price * SupplierService.PRICE_LIMIT_RATE)

        return {
            'drop_shipping_enabled': bool(product.drop_shipping_enabled),
            'price_limit_ok': price_limit_ok,
            'market_price': float(market_price) if market_price is not None else None,
            'sale_price': float(sale_price),
            'price_ratio': float(price_ratio) if price_ratio is not None else None,
            'summary': f"一件代发{'已开启' if product.drop_shipping_enabled else '未开启'} / 价格比例 {float(price_ratio) if price_ratio is not None else '--'}%",
        }

    @staticmethod
    def list_my_qualifications(db: Session, user_id: int) -> list[dict]:
        rows = db.query(ProductQualification).filter(
            ProductQualification.applicant_user_id == user_id
        ).order_by(ProductQualification.id.desc()).all()
        return [SupplierService._serialize_qualification_row(db, row) for row in rows]

    @staticmethod
    def _get_owned_supplier(db: Session, current_user: User, supplier_id: int) -> Supplier:
        supplier = db.get(Supplier, supplier_id)
        if not supplier:
            raise NotFoundError('Supplier not found')
        if supplier.user_id != current_user.id:
            raise ConflictError('Supplier not owned by current user')
        return supplier

    @staticmethod
    def _ensure_product_compliance(product: Product) -> None:
        if not product.drop_shipping_enabled:
            raise ConflictError('Product must enable drop shipping')
        if product.market_price is None:
            raise ConflictError('Product market price required')

        market_price = quantize_amount(product.market_price)
        sale_price = quantize_amount(product.sale_price)
        if market_price <= 0:
            raise ConflictError('Product market price must be greater than 0')

        price_ceiling = quantize_amount(market_price * SupplierService.PRICE_LIMIT_RATE)
        if sale_price > price_ceiling:
            raise ConflictError('Product sale price exceeds 20% of market price')

    @staticmethod
    def _count_qualifications_by_source(
        db: Session,
        user_id: int,
        qualification_type: QualificationType,
        source_ref_id: int,
        statuses: tuple[QualificationStatus, ...],
        exclude_qualification_id: int | None = None,
    ) -> int:
        query = db.query(func.count(ProductQualification.id)).filter(
            ProductQualification.applicant_user_id == user_id,
            ProductQualification.qualification_type == qualification_type,
            ProductQualification.source_ref_id == source_ref_id,
            ProductQualification.audit_status.in_(statuses),
        )
        if exclude_qualification_id is not None:
            query = query.filter(ProductQualification.id != exclude_qualification_id)
        return int(query.scalar() or 0)

    @staticmethod
    def _ensure_no_active_qualification_for_product(
        db: Session,
        user_id: int,
        product_id: int,
        exclude_qualification_id: int | None = None,
    ) -> None:
        query = db.query(ProductQualification).filter(
            ProductQualification.applicant_user_id == user_id,
            ProductQualification.product_id == product_id,
            ProductQualification.audit_status.in_((QualificationStatus.PENDING, QualificationStatus.APPROVED)),
        )
        if exclude_qualification_id is not None:
            query = query.filter(ProductQualification.id != exclude_qualification_id)
        existed = query.first()
        if existed:
            raise ConflictError('Active qualification already exists for this product')

    @staticmethod
    def _validate_entry_fee_source(db: Session, supplier: Supplier | None) -> int:
        if not supplier:
            raise ConflictError('Entry-fee qualification requires supplier_id')
        if supplier.status not in {SupplierStatus.APPROVED, SupplierStatus.ACTIVE}:
            raise ConflictError('Supplier must be approved before applying by entry fee')
        if not SupplierService._get_active_supplier_agreement(db, supplier.id):
            raise ConflictError('Active supplier agreement required')

        entry_order = SupplierService._get_latest_paid_entry_order(db, supplier.id)
        if not entry_order and not supplier.entry_fee_paid:
            raise ConflictError('Supplier entry fee unpaid')
        return entry_order.id if entry_order else supplier.id

    @staticmethod
    def _validate_package_quota_source(
        db: Session,
        current_user: User,
        supplier: Supplier | None,
        source_ref_id: int | None,
        exclude_qualification_id: int | None = None,
    ) -> int:
        if not supplier:
            raise ConflictError('Package quota qualification requires supplier_id')
        if not SupplierService._get_active_supplier_agreement(db, supplier.id):
            raise ConflictError('Active supplier agreement required')
        if source_ref_id is None:
            raise ConflictError('Package quota source_ref_id required')

        order = db.get(Order, source_ref_id)
        if not order:
            raise NotFoundError('Package order not found')
        if order.user_id != current_user.id:
            raise ConflictError('Package order not owned by current user')
        if order.order_type != OrderType.PACKAGE_ORDER:
            raise ConflictError('Selected source is not a package order')
        if order.pay_status != PayStatus.PAID:
            raise ConflictError('Package order not paid')
        if not order.source_ref_id:
            raise ConflictError('Package order source missing')

        package = db.get(Package, int(order.source_ref_id))
        if not package:
            raise NotFoundError('Package not found')
        if package.grants_product_quota <= 0:
            raise ConflictError('Selected package does not grant product quota')

        used_quota = SupplierService._count_qualifications_by_source(
            db,
            current_user.id,
            QualificationType.PACKAGE_QUOTA,
            order.id,
            (QualificationStatus.PENDING, QualificationStatus.APPROVED),
            exclude_qualification_id=exclude_qualification_id,
        )
        if used_quota >= package.grants_product_quota:
            raise ConflictError('Package product quota exhausted')
        return order.id

    @staticmethod
    def _validate_agent_qualification_source(
        db: Session,
        current_user: User,
        source_ref_id: int | None,
        exclude_qualification_id: int | None = None,
    ) -> tuple[int, AgentQualification, AgentLevel]:
        if source_ref_id is None:
            raise ConflictError('Agent qualification source_ref_id required')

        agent_qualification = db.get(AgentQualification, source_ref_id)
        if not agent_qualification:
            raise NotFoundError('Agent qualification not found')
        if agent_qualification.user_id != current_user.id:
            raise ConflictError('Agent qualification not owned by current user')
        if agent_qualification.qualification_status != QualificationStatus.APPROVED:
            raise ConflictError('Agent qualification not approved')
        if not agent_qualification.agreement_signed:
            raise ConflictError('Agent agreement required')

        current_time = now()
        if agent_qualification.effective_at and agent_qualification.effective_at > current_time:
            raise ConflictError('Agent qualification not effective yet')
        if agent_qualification.expired_at and agent_qualification.expired_at < current_time:
            raise ConflictError('Agent qualification expired')

        agent_level = db.get(AgentLevel, agent_qualification.agent_level_id)
        if not agent_level:
            raise NotFoundError('Agent level not found')
        if agent_level.requires_agreement and not agent_qualification.agreement_signed:
            raise ConflictError('Agent level agreement required')

        quota_total = agent_qualification.product_quota or agent_level.max_product_count
        if quota_total <= 0:
            raise ConflictError('Agent product quota unavailable')

        used_quota = SupplierService._count_qualifications_by_source(
            db,
            current_user.id,
            QualificationType.AGENT_QUALIFICATION,
            agent_qualification.id,
            (QualificationStatus.PENDING, QualificationStatus.APPROVED),
            exclude_qualification_id=exclude_qualification_id,
        )
        if used_quota >= quota_total:
            raise ConflictError('Agent product quota exhausted')
        return agent_qualification.id, agent_qualification, agent_level

    @staticmethod
    def _resolve_qualification_source(
        db: Session,
        current_user: User,
        qualification_type: QualificationType,
        supplier: Supplier | None,
        source_ref_id: int | None,
        exclude_qualification_id: int | None = None,
    ) -> tuple[int, AgentQualification | None, AgentLevel | None]:
        if qualification_type == QualificationType.ENTRY_FEE:
            return SupplierService._validate_entry_fee_source(db, supplier), None, None
        if qualification_type == QualificationType.PACKAGE_QUOTA:
            resolved_source_ref_id = SupplierService._validate_package_quota_source(
                db,
                current_user,
                supplier,
                source_ref_id,
                exclude_qualification_id=exclude_qualification_id,
            )
            return resolved_source_ref_id, None, None
        resolved_source_ref_id, agent_qualification, agent_level = SupplierService._validate_agent_qualification_source(
            db,
            current_user,
            source_ref_id,
            exclude_qualification_id=exclude_qualification_id,
        )
        return resolved_source_ref_id, agent_qualification, agent_level

    @staticmethod
    def _build_source_snapshot(
        db: Session,
        qualification: ProductQualification,
        supplier: Supplier | None,
        applicant: User | None,
    ) -> dict:
        base: dict[str, object] = {
            'source_type': qualification.qualification_type.value,
            'source_name': None,
            'source_status': None,
            'source_status_text': '--',
            'quota_total': None,
            'quota_used': None,
            'quota_remaining': None,
            'agreement_active': bool(supplier and SupplierService._get_active_supplier_agreement(db, supplier.id)),
            'summary': '--',
        }

        if qualification.qualification_type == QualificationType.ENTRY_FEE:
            if supplier:
                paid_entry_order = SupplierService._get_latest_paid_entry_order(db, supplier.id)
                base.update(
                    {
                        'source_name': supplier.supplier_name,
                        'source_status': supplier.status.value,
                        'source_status_text': '已缴入场费' if paid_entry_order or supplier.entry_fee_paid else '待缴入场费',
                        'summary': f"供应商 {supplier.supplier_name} / {'已签协议' if base['agreement_active'] else '缺少协议'}",
                    }
                )
            return base

        if qualification.qualification_type == QualificationType.PACKAGE_QUOTA:
            order = db.get(Order, qualification.source_ref_id) if qualification.source_ref_id else None
            package = db.get(Package, int(order.source_ref_id)) if order and order.source_ref_id else None
            quota_total = package.grants_product_quota if package else 0
            quota_used = SupplierService._count_qualifications_by_source(
                db,
                qualification.applicant_user_id,
                QualificationType.PACKAGE_QUOTA,
                qualification.source_ref_id or 0,
                (QualificationStatus.PENDING, QualificationStatus.APPROVED),
            ) if qualification.source_ref_id else 0
            base.update(
                {
                    'source_name': package.package_name if package else None,
                    'source_status': order.pay_status.value if order else None,
                    'source_status_text': '套餐已支付' if order and order.pay_status == PayStatus.PAID else '套餐未支付',
                    'quota_total': quota_total,
                    'quota_used': quota_used,
                    'quota_remaining': max(quota_total - quota_used, 0),
                    'summary': f"{package.package_name if package else '套餐'} / 剩余 {max(quota_total - quota_used, 0)}/{quota_total}",
                }
            )
            return base

        agent_qualification = db.get(AgentQualification, qualification.source_ref_id) if qualification.source_ref_id else None
        agent_level = db.get(AgentLevel, agent_qualification.agent_level_id) if agent_qualification else None
        quota_total = (agent_qualification.product_quota if agent_qualification and agent_qualification.product_quota else agent_level.max_product_count if agent_level else 0)
        quota_used = SupplierService._count_qualifications_by_source(
            db,
            qualification.applicant_user_id,
            QualificationType.AGENT_QUALIFICATION,
            qualification.source_ref_id or 0,
            (QualificationStatus.PENDING, QualificationStatus.APPROVED),
        ) if qualification.source_ref_id else 0
        effective = agent_qualification and (not agent_qualification.effective_at or agent_qualification.effective_at <= now())
        not_expired = agent_qualification and (not agent_qualification.expired_at or agent_qualification.expired_at >= now())
        active_text = '代理资格有效' if agent_qualification and effective and not_expired else '代理资格受限'
        base.update(
            {
                'source_name': agent_level.level_name if agent_level else None,
                'source_status': agent_qualification.qualification_status.value if agent_qualification else None,
                'source_status_text': active_text,
                'quota_total': quota_total,
                'quota_used': quota_used,
                'quota_remaining': max(quota_total - quota_used, 0),
                'agreement_active': bool(agent_qualification and agent_qualification.agreement_signed),
                'summary': f"{agent_level.level_name if agent_level else '代理资格'} / 剩余 {max(quota_total - quota_used, 0)}/{quota_total}",
                'effective_at': agent_qualification.effective_at.isoformat() if agent_qualification and agent_qualification.effective_at else None,
                'expired_at': agent_qualification.expired_at.isoformat() if agent_qualification and agent_qualification.expired_at else None,
            }
        )
        if applicant and agent_level:
            base['applicant_identity'] = applicant.business_identity.value
        return base

    @staticmethod
    def _serialize_qualification_row(db: Session, row: ProductQualification) -> dict:
        product = db.get(Product, row.product_id)
        supplier = db.get(Supplier, row.supplier_id) if row.supplier_id else None
        applicant = db.get(User, row.applicant_user_id)
        source_snapshot = SupplierService._build_source_snapshot(db, row, supplier, applicant)
        product_compliance = SupplierService._build_product_compliance_snapshot(product)
        return {
            'id': row.id,
            'product_id': row.product_id,
            'product_name': product.product_name if product else None,
            'applicant_user_id': row.applicant_user_id,
            'applicant_phone': applicant.phone if applicant else None,
            'supplier_id': row.supplier_id,
            'supplier_name': supplier.supplier_name if supplier else None,
            'qualification_type': row.qualification_type.value,
            'qualification_type_label': SupplierService._format_qualification_type_label(row.qualification_type),
            'source_ref_id': row.source_ref_id,
            'audit_status': row.audit_status.value,
            'audit_remark': row.audit_remark,
            'audited_by': row.audited_by,
            'audited_at': row.audited_at.isoformat() if row.audited_at else None,
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'source_snapshot': source_snapshot,
            'source_summary': source_snapshot['summary'],
            'source_status': source_snapshot['source_status_text'],
            'source_quota_total': source_snapshot.get('quota_total'),
            'source_quota_used': source_snapshot.get('quota_used'),
            'source_quota_remaining': source_snapshot.get('quota_remaining'),
            'agreement_active': source_snapshot.get('agreement_active'),
            'product_compliance': product_compliance,
            'product_compliance_summary': product_compliance['summary'],
            'product_owner_type': product.owner_type.value if product else None,
            'product_owner_id': product.owner_id if product else None,
        }

    @staticmethod
    def _serialize_qualification_ledger_row(db: Session, row: ProductQualification) -> dict:
        qualification_data = SupplierService._serialize_qualification_row(db, row)
        product = db.get(Product, row.product_id)
        supplier = db.get(Supplier, row.supplier_id) if row.supplier_id else None
        occupancy_active = row.audit_status in (QualificationStatus.PENDING, QualificationStatus.APPROVED)
        occupancy_status = {
            QualificationStatus.PENDING: 'OCCUPYING',
            QualificationStatus.APPROVED: 'EFFECTIVE',
            QualificationStatus.REJECTED: 'RELEASED',
        }[row.audit_status]
        occupancy_status_label = {
            QualificationStatus.PENDING: '占用中',
            QualificationStatus.APPROVED: '已生效',
            QualificationStatus.REJECTED: '已释放',
        }[row.audit_status]
        owner_bound = bool(
            product
            and supplier
            and product.owner_type == ProductOwnerType.SUPPLIER
            and product.owner_id == supplier.id
        )
        return {
            **qualification_data,
            'occupancy_status': occupancy_status,
            'occupancy_status_label': occupancy_status_label,
            'occupancy_active': occupancy_active,
            'occupied_at': row.created_at.isoformat() if row.created_at else None,
            'released_at': row.audited_at.isoformat() if row.audit_status == QualificationStatus.REJECTED and row.audited_at else None,
            'release_reason': row.audit_remark if row.audit_status == QualificationStatus.REJECTED else None,
            'owner_bound': owner_bound,
            'owner_bound_label': '已绑定归属' if owner_bound else '未绑定归属',
            'product_status': product.status.value if product else None,
            'product_status_label': product.status.value if product else None,
        }

    @staticmethod
    def _upgrade_business_identity_to(user: User, target_identity: BusinessIdentity) -> None:
        identity_rank = {
            BusinessIdentity.NORMAL_MEMBER: 0,
            BusinessIdentity.SUPPLIER: 1,
            BusinessIdentity.LOCAL_MERCHANT: 1,
            BusinessIdentity.COUNTY_AGENT: 2,
            BusinessIdentity.CITY_AGENT: 3,
        }
        if identity_rank[target_identity] > identity_rank.get(user.business_identity, 0):
            user.business_identity = target_identity

    @staticmethod
    def _upgrade_business_identity(user: User, agent_level_code: AgentLevelCode) -> None:
        SupplierService._upgrade_business_identity_to(
            user,
            {
                AgentLevelCode.COUNTY_AGENT: BusinessIdentity.COUNTY_AGENT,
                AgentLevelCode.CITY_AGENT: BusinessIdentity.CITY_AGENT,
            }[agent_level_code],
        )

    @staticmethod
    def _bind_product_owner_from_qualification(
        product: Product,
        supplier: Supplier | None,
        db: Session,
    ) -> tuple[bool, str | None]:
        if not supplier:
            return False, None
        if product.owner_type == ProductOwnerType.SUPPLIER and product.owner_id == supplier.id:
            return False, None

        order_count = int(
            db.query(func.count(OrderItem.id)).filter(OrderItem.product_id == product.id).scalar() or 0
        )
        if order_count > 0:
            return False, '商品已有历史订单，未自动改写归属'

        product.owner_type = ProductOwnerType.SUPPLIER
        product.owner_id = supplier.id
        return True, None

    @staticmethod
    def apply_product_qualification(db: Session, current_user: User, payload: dict) -> ProductQualification:
        product = db.get(Product, payload['product_id'])
        if not product:
            raise NotFoundError('Product not found')
        SupplierService._ensure_product_compliance(product)

        supplier_id = payload.get('supplier_id')
        supplier = None
        if supplier_id is not None:
            supplier = SupplierService._get_owned_supplier(db, current_user, supplier_id)

        qualification_type = QualificationType(payload['qualification_type'])
        SupplierService._ensure_no_active_qualification_for_product(db, current_user.id, product.id)
        resolved_source_ref_id, _, _ = SupplierService._resolve_qualification_source(
            db,
            current_user,
            qualification_type,
            supplier,
            payload.get('source_ref_id'),
        )

        qualification = ProductQualification(
            product_id=product.id,
            applicant_user_id=current_user.id,
            supplier_id=supplier_id,
            qualification_type=qualification_type,
            source_ref_id=resolved_source_ref_id,
            audit_status=QualificationStatus.PENDING,
            created_at=now(),
        )
        db.add(qualification)
        db.commit()
        db.refresh(qualification)
        return qualification

    @staticmethod
    def list_qualifications_for_admin(db: Session, current_user: User) -> list[dict]:
        query = db.query(ProductQualification)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(ProductQualification.applicant_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        rows = query.order_by(ProductQualification.id.desc()).all()
        return [SupplierService._serialize_qualification_row(db, row) for row in rows]

    @staticmethod
    def list_qualification_ledgers_for_admin(db: Session, current_user: User) -> list[dict]:
        query = db.query(ProductQualification)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(ProductQualification.applicant_user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        rows = query.order_by(ProductQualification.id.desc()).all()
        return [SupplierService._serialize_qualification_ledger_row(db, row) for row in rows]

    @staticmethod
    def audit_product_qualification(
        db: Session,
        qualification_id: int,
        current_user: User,
        audit_status: str,
        audit_remark: str | None = None,
    ) -> ProductQualification:
        qualification = db.get(ProductQualification, qualification_id)
        if not qualification:
            raise NotFoundError('Qualification not found')
        if not AdminScopeService.is_super_admin(current_user):
            applicant = db.get(User, qualification.applicant_user_id)
            if not applicant:
                raise NotFoundError('Applicant not found')
            AdminScopeService.ensure_user_visible(current_user, applicant)
        if qualification.audit_status != QualificationStatus.PENDING:
            raise ConflictError('Qualification already audited')

        target_status = QualificationStatus(audit_status)
        if target_status not in {QualificationStatus.APPROVED, QualificationStatus.REJECTED}:
            raise ConflictError('Audit status must be APPROVED or REJECTED')

        product = db.get(Product, qualification.product_id)
        if not product:
            raise NotFoundError('Product not found')
        SupplierService._ensure_product_compliance(product)

        applicant = db.get(User, qualification.applicant_user_id)
        if not applicant:
            raise NotFoundError('Applicant not found')
        supplier = db.get(Supplier, qualification.supplier_id) if qualification.supplier_id else None
        agent_qualification = None
        agent_level = None
        owner_bound = False
        owner_bind_remark = None
        if target_status == QualificationStatus.APPROVED:
            SupplierService._ensure_no_active_qualification_for_product(
                db,
                qualification.applicant_user_id,
                qualification.product_id,
                exclude_qualification_id=qualification.id,
            )
            _, agent_qualification, agent_level = SupplierService._resolve_qualification_source(
                db,
                applicant,
                qualification.qualification_type,
                supplier,
                qualification.source_ref_id,
                exclude_qualification_id=qualification.id,
            )
            owner_bound, owner_bind_remark = SupplierService._bind_product_owner_from_qualification(product, supplier, db)

        qualification.audit_status = target_status
        qualification.audit_remark = audit_remark
        qualification.audited_by = current_user.id
        qualification.audited_at = now()
        db.flush()

        if target_status == QualificationStatus.APPROVED and supplier:
            SupplierService._upgrade_business_identity_to(applicant, BusinessIdentity.SUPPLIER)

        if qualification.qualification_type == QualificationType.AGENT_QUALIFICATION and qualification.source_ref_id:
            current_agent_qualification = agent_qualification or db.get(AgentQualification, qualification.source_ref_id)
            if current_agent_qualification:
                current_agent_qualification.used_quota = SupplierService._count_qualifications_by_source(
                    db,
                    qualification.applicant_user_id,
                    QualificationType.AGENT_QUALIFICATION,
                    current_agent_qualification.id,
                    (QualificationStatus.APPROVED,),
                )
                if target_status == QualificationStatus.APPROVED and agent_level:
                    SupplierService._upgrade_business_identity(applicant, agent_level.level_code)

        if owner_bound and supplier:
            qualification.audit_remark = (
                f'{qualification.audit_remark}；已自动绑定供应商归属#{supplier.id}'
                if qualification.audit_remark else f'已自动绑定供应商归属#{supplier.id}'
            )
        elif owner_bind_remark:
            qualification.audit_remark = (
                f'{qualification.audit_remark}；{owner_bind_remark}'
                if qualification.audit_remark else owner_bind_remark
            )

        db.commit()
        db.refresh(qualification)
        return qualification

    @staticmethod
    def ensure_default_agent_levels(db: Session) -> None:
        if db.query(AgentLevel).count() > 0:
            return
        db.add_all(
            [
                AgentLevel(level_code=AgentLevelCode.COUNTY_AGENT, level_name='区县代理', max_product_count=2),
                AgentLevel(level_code=AgentLevelCode.CITY_AGENT, level_name='市代理', max_product_count=5),
            ]
        )
        db.commit()
