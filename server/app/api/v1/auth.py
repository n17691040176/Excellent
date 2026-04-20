from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.schemas.auth import CodeLoginRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, SendLoginCodeRequest
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix='/auth')


@router.post('/register')
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    token, user = AuthService.register(db, payload.phone, payload.password, payload.nickname, payload.invite_code)
    return {'code': 0, 'message': 'success', 'data': {'access_token': token, 'token_type': 'bearer', 'user': user}}


@router.post('/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token, user = AuthService.login(db, payload.phone, payload.password)
    return {'code': 0, 'message': 'success', 'data': {'access_token': token, 'token_type': 'bearer', 'user': user}}


@router.post('/send-login-code')
def send_login_code(payload: SendLoginCodeRequest):
    return {'code': 0, 'message': 'success', 'data': AuthService.send_login_code(payload.phone)}


@router.post('/login-by-code')
def login_by_code(payload: CodeLoginRequest, db: Session = Depends(get_db)):
    token, user = AuthService.login_by_code(db, payload.phone, payload.code)
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
def me(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': UserService.serialize_app_user(db, current_user)}
