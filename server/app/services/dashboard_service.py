from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.commission import CommissionFlow, WithdrawRequest
from app.models.order import Order
from app.models.team import Team
from app.models.user import User
from app.services.admin_scope import AdminScopeService


class DashboardService:
    @staticmethod
    def overview(db: Session, current_user: User) -> dict:
        user_query = db.query(func.count(User.id))
        team_query = db.query(func.count(Team.id))
        order_query = db.query(func.count(Order.id))
        commission_query = db.query(func.coalesce(func.sum(CommissionFlow.commission_amount), 0))
        withdraw_query = db.query(func.count(WithdrawRequest.id)).filter(WithdrawRequest.status == 'PENDING')

        if not AdminScopeService.is_super_admin(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            team_user_ids = AdminScopeService.team_user_ids_subquery(current_user)
            user_query = user_query.filter(User.team_id == team_id)
            team_query = team_query.filter(Team.id == team_id)
            order_query = order_query.filter(Order.team_id == team_id)
            commission_query = commission_query.filter(CommissionFlow.team_id == team_id)
            withdraw_query = withdraw_query.filter(WithdrawRequest.user_id.in_(team_user_ids))

        return {
            'user_total': user_query.scalar() or 0,
            'team_total': team_query.scalar() or 0,
            'order_total': order_query.scalar() or 0,
            'commission_total': float(commission_query.scalar() or 0),
            'withdraw_pending_total': withdraw_query.scalar() or 0,
        }
