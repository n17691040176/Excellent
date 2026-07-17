"""
阿里云短信服务
文档: https://help.aliyun.com/document_detail/419218.html
"""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.core.config import settings


class SmsService:
    """阿里云短信服务"""

    API_GATEWAY = 'https://dysmsapi.aliyuncs.com'
    CODE_EXPIRE_SECONDS = 300

    @classmethod
    def _percent_encode(cls, value: object) -> str:
        return quote(str(value), safe='~')

    @classmethod
    def _generate_signature(cls, params: Mapping[str, object], secret: str, http_method: str = 'GET') -> str:
        """生成阿里云 RPC API 签名。"""
        canonicalized_query = '&'.join(
            f'{cls._percent_encode(key)}={cls._percent_encode(value)}'
            for key, value in sorted(params.items())
        )
        string_to_sign = f'{http_method}&%2F&{cls._percent_encode(canonicalized_query)}'
        digest = hmac.new(
            f'{secret}&'.encode(),
            string_to_sign.encode(),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode('utf-8')

    @classmethod
    def _request_api(cls, action: str, params: dict[str, str]) -> dict:
        """发送请求到阿里云短信 API。"""
        common_params: dict[str, str] = {
            'Format': 'JSON',
            'Version': '2017-05-25',
            'AccessKeyId': settings.sms_aliyun_access_key_id,
            'SignatureVersion': '1.0',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': f'{uuid4().hex}{int(time.time() * 1000)}',
            'Timestamp': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'RegionId': 'cn-hangzhou',
            'Action': action,
        }

        all_params = {**common_params, **params}
        all_params['Signature'] = cls._generate_signature(
            all_params,
            settings.sms_aliyun_access_key_secret,
        )

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f'{cls.API_GATEWAY}/', params=all_params)
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as exc:
            raise Exception(f'短信网络请求失败: {exc}') from exc

        if result.get('Code') != 'OK':
            code = result.get('Code') or 'Unknown'
            message = result.get('Message') or '短信 API 请求失败'
            raise Exception(f'{code}: {message}')

        return result

    @classmethod
    def send_login_code(cls, phone: str, code: str) -> dict:
        """
        发送登录验证码。

        验证码由 AuthService 统一生成、缓存和校验，短信服务只负责发送同一个 code。
        """
        if not settings.sms_enabled:
            raise Exception('短信服务未启用')
        if not settings.sms_aliyun_access_key_id or not settings.sms_aliyun_access_key_secret:
            raise Exception('阿里云短信 AccessKey 未配置')
        if not settings.sms_sign_name or not settings.sms_template_code:
            raise Exception('阿里云短信签名或模板未配置')

        phone = cls._normalize_phone(phone)
        template_param_name = settings.sms_template_param_name.strip() or 'code'
        cls._request_api(
            'SendSms',
            {
                'PhoneNumbers': phone,
                'SignName': settings.sms_sign_name,
                'TemplateCode': settings.sms_template_code,
                'TemplateParam': json.dumps(
                    {template_param_name: code},
                    ensure_ascii=False,
                    separators=(',', ':'),
                ),
            },
        )
        return {
            'success': True,
            'message': '验证码发送成功',
            'expire_seconds': cls.CODE_EXPIRE_SECONDS,
        }

    @classmethod
    def _normalize_phone(cls, phone: str) -> str:
        """标准化手机号格式。"""
        phone = phone.strip().replace(' ', '')
        if phone.startswith('+86'):
            phone = phone[3:]
        return phone
