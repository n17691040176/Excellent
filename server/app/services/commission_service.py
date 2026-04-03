from decimal import Decimal

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.commission import CommissionConfig, CommissionFlow, UserCommission, WithdrawRequest
from app.models.enums import AssetType, CommissionStatus, WithdrawStatus, WithdrawType
from app.models.order import Order
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.utils.helpers import now, quantize_amount


class CommissionService:
    @staticmethod
    def get_config(db: Session) -> CommissionConfig:
        config = db.query(CommissionConfig).filter(CommissionConfig.is_active.is_(True)).first()
        if not config:
            config = CommissionConfig(level1_rate=5, level2_rate=2, is_active=True, updated_at=now())
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    @staticmethod
    def summary(db: Session, user_id: int) -> dict:
        data = db.query(UserCommission).filter(UserCommission.user_id == user_id).first()
        if not data:
            return {'frozen_amount': 0, 'available_amount': 0, 'total_amount': 0, 'withdrawn_amount': 0}
        return {
            'frozen_amount': float(data.frozen_amount),
            'available_amount': float(data.available_amount),
            'total_amount': float(data.total_amount),
            'withdrawn_amount': float(data.withdrawn_amount),
        }

    @staticmethod
    def flows(db: Session, user_id: int) -> list[CommissionFlow]:
        return db.query(CommissionFlow).filter(CommissionFlow.beneficiary_user_id == user_id).order_by(CommissionFlow.id.desc()).all()

    @staticmethod
    def freeze_for_order(db: Session, order: Order, buyer: User) -> None:
        config = CommissionService.get_config(db)
        beneficiaries = []
        if buyer.parent_id:
            beneficiaries.append((buyer.parent_id, Decimal(str(config.level1_rate)) / Decimal('100'), 1))
        if buyer.grandparent_id:
            beneficiaries.append((buyer.grandparent_id, Decimal(str(config.level2_rate)) / Decimal('100'), 2))
        for user_id, rate, level in beneficiaries:
            amount = quantize_amount(Decimal(str(order.paid_amount)) * rate)
            commission = db.query(UserCommission).filter(UserCommission.user_id == user_id).first()
            if not commission:
                commission = UserCommission(user_id=user_id, updated_at=now())
                db.add(commission)
                db.flush()
            commission.frozen_amount = quantize_amount(commission.frozen_amount) + amount
            commission.total_amount = quantize_amount(commission.total_amount) + amount
            commission.updated_at = now()
            db.add(
                CommissionFlow(
                    beneficiary_user_id=user_id,
                    source_user_id=buyer.id,
                    order_id=order.id,
                    team_id=buyer.team_id,
                    level=level,
                    rate=rate * 100,
                    base_amount=order.paid_amount,
                    commission_amount=amount,
                    status=CommissionStatus.FROZEN,
                    created_at=now(),
                )
            )

    @staticmethod
    def settle_for_order(db: Session, order_id: int) -> None:
        flows = db.query(CommissionFlow).filter(
            CommissionFlow.order_id == order_id,
            CommissionFlow.status == CommissionStatus.FROZEN,
        ).all()
        for flow in flows:
            summary = db.query(UserCommission).filter(UserCommission.user_id == flow.beneficiary_user_id).first()
            if not summary:
                continue
            amount = quantize_amount(flow.commission_amount)
            summary.frozen_amount = quantize_amount(summary.frozen_amount) - amount
            summary.available_amount = quantize_amount(summary.available_amount) + amount
            summary.updated_at = now()
            flow.status = CommissionStatus.SETTLED
            flow.settled_at = now()
        db.commit()

    @staticmethod
    def create_withdraw(db: Session, user_id: int, withdraw_type: WithdrawType, amount: float, remark: str | None = None) -> WithdrawRequest:
        quantized = quantize_amount(amount)
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('User not found')
        if withdraw_type == WithdrawType.COMMISSION:
            summary = db.query(UserCommission).filter(UserCommission.user_id == user_id).first()
            if not summary or quantize_amount(summary.available_amount) < quantized:
                raise ConflictError('Commission amount insufficient')
        else:
            asset_type = AssetType.BALANCE if withdraw_type == WithdrawType.BALANCE else AssetType.POINTS
            account = AssetService.get_account(db, user_id, asset_type)
            if quantize_amount(account.available_amount) < quantized:
                raise ConflictError('Asset amount insufficient')
        record = WithdrawRequest(
            user_id=user_id,
            team_id=user.team_id,
            withdraw_type=withdraw_type,
            amount=quantized,
            status=WithdrawStatus.PENDING,
            remark=remark,
            created_at=now(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_withdraws(db: Session, user_id: int) -> list[WithdrawRequest]:
        return db.query(WithdrawRequest).filter(WithdrawRequest.user_id == user_id).order_by(WithdrawRequest.id.desc()).all()

    @staticmethod
    def list_user_commissions_for_admin(db: Session, current_user: User) -> list[UserCommission]:
        query = db.query(UserCommission)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(UserCommission.user_id.in_(AdminScopeService.team_user_ids_subquery(current_user)))
        return query.order_by(UserCommission.id.desc()).all()

    @staticmethod
    def list_flows_for_admin(db: Session, current_user: User) -> list[CommissionFlow]:
        query = db.query(CommissionFlow)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(CommissionFlow.team_id == AdminScopeService.require_team_id(current_user))
        return query.order_by(CommissionFlow.id.desc()).all()

    @staticmethod
    def list_withdraws_for_admin(db: Session, current_user: User) -> list[WithdrawRequest]:
        query = db.query(WithdrawRequest)
        if not AdminScopeService.is_super_admin(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            query = query.outerjoin(User, WithdrawRequest.user_id == User.id).filter(
                or_(
                    WithdrawRequest.team_id == team_id,
                    and_(WithdrawRequest.team_id.is_(None), User.team_id == team_id),
                )
            )
        return query.order_by(WithdrawRequest.id.desc()).all()

    @staticmethod
    def _ensure_withdraw_visible(db: Session, record: WithdrawRequest, current_user: User) -> None:
        if AdminScopeService.is_super_admin(current_user):
            return
        scoped_team_id = AdminScopeService.require_team_id(current_user)
        record_team_id = record.team_id
        if record_team_id is None:
            target_user = db.get(User, record.user_id)
            record_team_id = target_user.team_id if target_user else None
        if record_team_id != scoped_team_id:
            raise ConflictError('Withdraw request out of team scope')

    @staticmethod
    def approve_withdraw(db: Session, withdraw_id: int, current_user: User) -> WithdrawRequest:
        record = db.get(WithdrawRequest, withdraw_id)
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.PENDING:
            raise ConflictError('Withdraw status invalid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)

        amount = quantize_amount(record.amount)
        if record.withdraw_type == WithdrawType.COMMISSION:
            summary = db.query(UserCommission).filter(UserCommission.user_id == record.user_id).first()
            if not summary or quantize_amount(summary.available_amount) < amount:
                raise ConflictError('Commission amount insufficient')
            summary.available_amount = quantize_amount(summary.available_amount) - amount
            summary.withdrawn_amount = quantize_amount(summary.withdrawn_amount) + amount
            summary.updated_at = now()
        else:
            asset_type = AssetType.BALANCE if record.withdraw_type == WithdrawType.BALANCE else AssetType.POINTS
            account = AssetService.get_account(db, record.user_id, asset_type)
            AssetService.consume_amount(
                db,
                record.user_id,
                asset_type,
                amount,
                'WITHDRAW_APPROVE',
                source_id=record.id,
                source_no=str(record.id),
            )
            account.withdrawn_amount = quantize_amount(account.withdrawn_amount) + amount
            account.updated_at = now()

        record.status = WithdrawStatus.APPROVED
        record.reviewed_by = current_user.id
        record.reviewed_at = now()
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def reject_withdraw(db: Session, withdraw_id: int, current_user: User, remark: str | None = None) -> WithdrawRequest:
        record = db.get(WithdrawRequest, withdraw_id)
        if not record:
            raise NotFoundError('Withdraw request not found')
        if record.status != WithdrawStatus.PENDING:
            raise ConflictError('Withdraw status invalid')
        CommissionService._ensure_withdraw_visible(db, record, current_user)
        record.status = WithdrawStatus.REJECTED
        record.reviewed_by = current_user.id
        record.reviewed_at = now()
        if remark:
            record.remark = remark
        db.commit()
        db.refresh(record)
        return record
