import os
from dataclasses import dataclass, field


def _env(name: str, default: str = '') -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class WechatPayConfig:
    enabled: bool = _env_bool('WECHAT_PAY_ENABLED', False)
    app_id: str = _env('WECHAT_PAY_APP_ID')
    mchid: str = _env('WECHAT_PAY_MCHID')
    api_v3_key: str = _env('WECHAT_PAY_API_V3_KEY')
    merchant_serial_no: str = _env('WECHAT_PAY_MERCHANT_SERIAL_NO')
    merchant_private_key_path: str = _env('WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH')
    platform_cert_path: str = _env('WECHAT_PAY_PLATFORM_CERT_PATH')
    notify_url: str = _env('WECHAT_PAY_NOTIFY_URL')
    app_pay_subject_prefix: str = _env('WECHAT_PAY_APP_SUBJECT_PREFIX', 'Excellent') or 'Excellent'


@dataclass(frozen=True)
class AlipayConfig:
    enabled: bool = _env_bool('ALIPAY_ENABLED', False)
    app_id: str = _env('ALIPAY_APP_ID')
    private_key_path: str = _env('ALIPAY_PRIVATE_KEY_PATH')
    public_key_path: str = _env('ALIPAY_PUBLIC_KEY_PATH')
    notify_url: str = _env('ALIPAY_NOTIFY_URL')
    return_url: str = _env('ALIPAY_RETURN_URL')
    gateway_url: str = _env('ALIPAY_GATEWAY_URL', 'https://openapi.alipay.com/gateway.do') or 'https://openapi.alipay.com/gateway.do'
    charset: str = _env('ALIPAY_CHARSET', 'utf-8') or 'utf-8'
    sign_type: str = _env('ALIPAY_SIGN_TYPE', 'RSA2') or 'RSA2'
    app_pay_subject_prefix: str = _env('ALIPAY_APP_SUBJECT_PREFIX', 'Excellent') or 'Excellent'


@dataclass(frozen=True)
class PaymentConfig:
    mock_external_payment: bool = _env_bool('PAYMENT_MOCK_EXTERNAL_PAYMENT', True)
    default_currency: str = _env('PAYMENT_DEFAULT_CURRENCY', 'CNY') or 'CNY'
    request_timeout_seconds: int = _env_int('PAYMENT_REQUEST_TIMEOUT_SECONDS', 15)
    wechat: WechatPayConfig = field(default_factory=WechatPayConfig)
    alipay: AlipayConfig = field(default_factory=AlipayConfig)


payment_config = PaymentConfig()
