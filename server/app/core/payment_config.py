import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key


def _settings_value(name: str) -> str | None:
    try:
        from app.core.config import settings

        value = getattr(settings, name.lower(), None)
    except Exception:  # pragma: no cover - protects isolated tooling imports
        value = None
    return None if value is None else str(value)


def _env(name: str, default: str = '') -> str:
    value = os.getenv(name)
    if value is None:
        value = _settings_value(name)
    return (default if value is None else value).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _default_mock_external_payment() -> bool:
    app_env = os.getenv('APP_ENV')
    if not app_env:
        try:
            from app.core.config import settings

            app_env = settings.app_env
        except Exception:  # pragma: no cover - only protects isolated tooling imports
            app_env = 'development'
    return app_env.strip().lower() != 'production'


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
    payment_method: str = _env('ALIPAY_PAYMENT_METHOD', 'alipay.trade.wap.pay') or 'alipay.trade.wap.pay'
    charset: str = _env('ALIPAY_CHARSET', 'utf-8') or 'utf-8'
    sign_type: str = _env('ALIPAY_SIGN_TYPE', 'RSA2') or 'RSA2'
    seller_id: str = _env('ALIPAY_SELLER_ID')
    app_pay_subject_prefix: str = _env('ALIPAY_APP_SUBJECT_PREFIX', 'Excellent') or 'Excellent'


@dataclass(frozen=True)
class PaymentConfig:
    mock_external_payment: bool = _env_bool(
        'PAYMENT_MOCK_EXTERNAL_PAYMENT',
        _default_mock_external_payment(),
    )
    default_currency: str = _env('PAYMENT_DEFAULT_CURRENCY', 'CNY') or 'CNY'
    request_timeout_seconds: int = _env_int('PAYMENT_REQUEST_TIMEOUT_SECONDS', 15)
    wechat: WechatPayConfig = field(default_factory=WechatPayConfig)
    alipay: AlipayConfig = field(default_factory=AlipayConfig)


payment_config = PaymentConfig()


def enabled_external_payment_channels(config: PaymentConfig | None = None) -> list[str]:
    active_config = config or payment_config
    if active_config.mock_external_payment:
        return ['ALIPAY']

    channels = []
    if active_config.alipay.enabled:
        channels.append('ALIPAY')
    return channels


def _valid_url(value: str, *, require_https: bool) -> bool:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return False
    return not require_https or parsed.scheme.lower() == 'https'


def validate_payment_config(app_env: str, config: PaymentConfig | None = None) -> None:
    active_config = config or payment_config
    production = app_env.strip().lower() == 'production'
    errors: list[str] = []

    if production and active_config.mock_external_payment:
        errors.append('PAYMENT_MOCK_EXTERNAL_PAYMENT must be false in production')

    alipay = active_config.alipay
    if alipay.enabled:
        required_values = {
            'ALIPAY_APP_ID': alipay.app_id,
            'ALIPAY_PRIVATE_KEY_PATH': alipay.private_key_path,
            'ALIPAY_PUBLIC_KEY_PATH': alipay.public_key_path,
            'ALIPAY_NOTIFY_URL': alipay.notify_url,
            'ALIPAY_GATEWAY_URL': alipay.gateway_url,
        }
        errors.extend(f'{name} is required when ALIPAY_ENABLED=true' for name, value in required_values.items() if not value)

        if alipay.payment_method not in {'alipay.trade.wap.pay', 'alipay.trade.app.pay'}:
            errors.append('ALIPAY_PAYMENT_METHOD must be alipay.trade.wap.pay or alipay.trade.app.pay')
        if alipay.payment_method == 'alipay.trade.wap.pay' and not alipay.return_url:
            errors.append('ALIPAY_RETURN_URL is required for H5 WAP payment')

        if alipay.sign_type.upper() != 'RSA2':
            errors.append('ALIPAY_SIGN_TYPE must be RSA2')

        for name, value in {
            'ALIPAY_PRIVATE_KEY_PATH': alipay.private_key_path,
            'ALIPAY_PUBLIC_KEY_PATH': alipay.public_key_path,
        }.items():
            if value and not Path(value).is_file():
                errors.append(f'{name} does not point to a readable file')

        if alipay.private_key_path and Path(alipay.private_key_path).is_file():
            try:
                private_key = load_pem_private_key(Path(alipay.private_key_path).read_bytes(), password=None)
                if not isinstance(private_key, RSAPrivateKey) or private_key.key_size < 2048:
                    errors.append('ALIPAY_PRIVATE_KEY_PATH must contain an RSA private key of at least 2048 bits')
            except (TypeError, ValueError):
                errors.append('ALIPAY_PRIVATE_KEY_PATH does not contain a valid unencrypted PEM private key')

        if alipay.public_key_path and Path(alipay.public_key_path).is_file():
            try:
                public_key = load_pem_public_key(Path(alipay.public_key_path).read_bytes())
                if not isinstance(public_key, RSAPublicKey) or public_key.key_size < 2048:
                    errors.append('ALIPAY_PUBLIC_KEY_PATH must contain an RSA public key of at least 2048 bits')
            except (TypeError, ValueError):
                errors.append('ALIPAY_PUBLIC_KEY_PATH does not contain a valid PEM public key')

        for name, value in {
            'ALIPAY_NOTIFY_URL': alipay.notify_url,
            'ALIPAY_GATEWAY_URL': alipay.gateway_url,
            'ALIPAY_RETURN_URL': alipay.return_url,
        }.items():
            if value and not _valid_url(value, require_https=production):
                scheme = 'HTTPS' if production else 'HTTP(S)'
                errors.append(f'{name} must be a valid {scheme} URL')

    if errors:
        raise RuntimeError('Invalid payment configuration: ' + '; '.join(errors))
