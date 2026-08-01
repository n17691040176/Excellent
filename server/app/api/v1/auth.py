from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AppLoginRequest,
    CodeLoginRequest,
    LoginRequest,
    OneClickLoginRequest,
    OneClickRegisterRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SendLoginCodeRequest,
)
from app.services.auth_service import AuthService
from app.services.dypns_service import DypnsService
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
    token, user = AuthService.login_by_code(db, payload.phone, payload.code, payload.invite_code)
    return {'code': 0, 'message': 'success', 'data': {'access_token': token, 'token_type': 'bearer', 'user': user}}


@router.post('/admin-login')
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    token, user = AuthService.login(db, payload.phone, payload.password, admin_only=True)
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'access_token': token,
            'token_type': 'bearer',
            'user': UserService.serialize_app_user(db, user),
        },
    }


@router.post('/reset-password')
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.phone != payload.phone:
        raise ForbiddenError('Cannot reset another account password')
    AuthService.reset_password(db, payload.phone, payload.new_password)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@router.post('/one-click-login')
def one_click_login(payload: OneClickLoginRequest, db: Session = Depends(get_db)):
    """
    一键登录

    流程:
    1. 前端调用阿里云 SDK 获取 access_token
    2. 后端使用 access_token 换取手机号并验证
    3. 返回登录结果

    返回 is_new_user=True 表示新用户，需要前端引导填写昵称后注册
    """
    result = DypnsService.login_or_register(db, payload.access_token)
    return {'code': 0, 'message': 'success', 'data': result}


@router.post('/one-click-register')
def one_click_register(payload: OneClickRegisterRequest, db: Session = Depends(get_db)):
    """
    一键登录新用户注册

    用于前端补充昵称和邀请码后完成注册
    """
    result = DypnsService.register_with_token(
        db,
        payload.access_token,
        payload.nickname,
        payload.invite_code
    )
    return {'code': 0, 'message': 'success', 'data': result}


@router.post('/app-login')
def app_login(payload: AppLoginRequest, db: Session = Depends(get_db)):
    """
    App端传递手机号免注册登录

    场景: H5嵌入App中，App已验证用户手机号，通过URL参数或postMessage传递手机号给H5
    逻辑:
    1. 手机号已存在 → 直接登录返回token
    2. 手机号不存在 → 自动创建用户并登录（免注册）
    """
    token, user, is_new_user = AuthService.login_or_register_app_user(
        db,
        payload.phone,
        payload.nickname,
        payload.invite_code,
    )
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'access_token': token,
            'token_type': 'bearer',
            'user': UserService.serialize_app_user(db, user),
            'is_new_user': is_new_user,
        }
    }


@router.get('/me')
def me(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': UserService.serialize_app_user(db, current_user)}
