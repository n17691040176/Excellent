from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, ResetPasswordRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix='/auth')


@router.post('/register')
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    token, user = AuthService.register(db, payload.phone, payload.password, payload.nickname, payload.invite_code)
    return {'code': 0, 'message': 'success', 'data': {'access_token': token, 'token_type': 'bearer', 'user': user}}


@router.post('/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token, user = AuthService.login(db, payload.phone, payload.password)
    return {'code': 0, 'message': 'success', 'data': {'access_token': token, 'token_type': 'bearer', 'user': user}}


@router.post('/admin-login')
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    token, user = AuthService.login(db, payload.phone, payload.password, admin_only=True)
    return {'code': 0, 'message': 'success', 'data': {'access_token': token, 'token_type': 'bearer', 'user': user}}


@router.post('/reset-password')
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    AuthService.reset_password(db, payload.phone, payload.new_password)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@router.get('/me')
def me(current_user=Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': current_user}
