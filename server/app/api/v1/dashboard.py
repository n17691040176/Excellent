from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.services.dashboard_service import DashboardService

admin_router = APIRouter(prefix='/admin/dashboard')


@admin_router.get('/overview')
def overview(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': DashboardService.overview(db, current_user)}
