"""
阿里云号码认证服务（一键登录）
文档: https://help.aliyun.com/document_detail/2805003.html
"""

import hashlib
import hmac
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService


class DypnsService:
    """阿里云一键登录服务"""

    # API 地址
    API_GATEWAY = "https://dypnsapi.aliyuncs.com"

    @classmethod
    def _generate_signature(cls, params: dict, secret: str) -> str:
        """生成签名"""
        sorted_params = sorted(params.items())
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        return hmac.new(
            secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def _request_api(cls, action: str, params: dict) -> dict:
        """发送请求到阿里云"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        common_params = {
            'Format': 'JSON',
            'Version': '2017-05-25',
            'AccessKeyId': settings.dynpns_access_key_id,
            'SignatureVersion': '1.0',
            'SignatureMethod': 'HMAC-SHA256',
            'SignatureNonce': str(int(time.time() * 1000)),
            'Timestamp': timestamp,
            'RegionId': 'cn-hangzhou',
            'Action': action,
        }

        all_params = {**common_params, **params}
        signature = cls._generate_signature(all_params, settings.dynpns_access_key_secret)
        all_params['Signature'] = signature

        url = f"{cls.API_GATEWAY}/"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, data=all_params)
                response.raise_for_status()
                result = response.json()

                if result.get('Code') != 'OK':
                    raise Exception(result.get('Message', 'API请求失败'))

                return result
        except httpx.HTTPError as e:
            raise Exception(f"网络请求失败: {str(e)}") from e

    @classmethod
    def get_phone_with_token(cls, access_token: str) -> str | None:
        """
        使用 SDK 令牌获取手机号

        步骤1: 前端调用阿里云 SDK 获取 access_token
        步骤2: 后端使用 access_token 换取手机号

        注意: 阿里云一键登录需要前端 SDK 配合
        前端需要集成阿里云 SDK: https://help.aliyun.com/document_detail/2805002.html
        """
        if not settings.dynpns_enabled:
            raise Exception("阿里云一键登录未启用")

        params = {
            'AccessToken': access_token,
            'SignatureSecret': settings.dynpns_signature_secret,
            'AppKey': settings.dynpns_app_key,
        }

        result = cls._request_api('GetPhoneWithToken', params)
        return result.get('PhoneNumber')

    @classmethod
    def login_or_register(cls, db: Session, access_token: str) -> dict:
        """
        一键登录主流程

        1. 验证 token 获取手机号
        2. 查询或创建用户
        3. 返回登录凭证
        """
        if not settings.dynpns_enabled:
            raise Exception("阿里云一键登录未启用")

        # 1. 获取手机号
        phone = cls.get_phone_with_token(access_token)
        if not phone:
            raise Exception("无法获取手机号")

        # 清理手机号格式（确保标准格式）
        phone = phone.replace('+86', '').strip()

        # 2. 查询用户
        user = db.query(User).filter(User.phone == phone).first()

        if user:
            # 已存在用户，直接登录
            token, user = AuthService.finalize_login(db, user)
            return {
                'access_token': token,
                'token_type': 'bearer',
                'user': UserService.serialize_app_user(db, user),
                'is_new_user': False
            }
        else:
            # 新用户，需要前端补充信息后注册
            return {
                'need_register': True,
                'phone': phone,
                'is_new_user': True
            }

    @classmethod
    def register_with_token(cls, db: Session, access_token: str, nickname: str = '', invite_code: str | None = None) -> dict:
        """
        一键登录新用户注册

        用于前端补充信息后完成注册
        """
        if not settings.dynpns_enabled:
            raise Exception("阿里云一键登录未启用")

        # 1. 获取手机号
        phone = cls.get_phone_with_token(access_token)
        if not phone:
            raise Exception("无法获取手机号")

        phone = phone.replace('+86', '').strip()

        # 2. 检查用户是否已存在
        existing = db.query(User).filter(User.phone == phone).first()
        if existing:
            raise Exception("用户已存在，请使用密码登录")

        # 3. 创建用户（无密码，一键登录用户）
        user = AuthService.create_passwordless_user(db, phone, nickname or f"用户{phone[-4:]}", invite_code)
        user.is_phone_verified = True
        db.commit()
        db.refresh(user)

        token = AuthService.issue_token(user)
        return {
            'access_token': token,
            'token_type': 'bearer',
            'user': UserService.serialize_app_user(db, user),
            'is_new_user': True
        }
