from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.page_decoration import DecorationPayloadRequest
from app.services.page_decoration_service import PageDecorationService

app_router = APIRouter(prefix='/app/decorations')
admin_router = APIRouter(prefix='/admin/decorations')


@app_router.get('/mobile-home')
def app_mobile_home_decoration(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': PageDecorationService.get_mobile_uni_home_for_app(db, current_user)}


@admin_router.get('/mobile-home')
def admin_mobile_home_decoration(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': PageDecorationService.get_mobile_uni_home_for_admin(db, current_user)}


@admin_router.put('/mobile-home')
def admin_save_mobile_home_decoration(
    payload: DecorationPayloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': PageDecorationService.save_mobile_uni_home_for_admin(db, current_user, payload.payload)}
