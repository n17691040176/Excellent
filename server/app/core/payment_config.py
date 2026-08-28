import os
from dataclasses import dataclass, field
from hashlib import md5
from pathlib import Path
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

UNPAID_ORDER_EXPIRE_MINUTES = 30
ALIPAY_SANDBOX_GATEWAY_URL = 'https://openapi-sandbox.dl.alipaydev.com/gateway.do'
WECHAT_REFUND_NOTIFY_URL_MAX_BYTES = 256


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
    refund_notify_url: str = _env('WECHAT_PAY_REFUND_NOTIFY_URL')
    # Leave this empty at the dataclass level so the payment service can tell
    # whether the canonical variable was explicitly supplied. The service
    # still defaults to WAP when neither canonical nor legacy variable exists.
    h5_type: str = _env('WECHAT_PAY_H5_TYPE')
    # Compatibility aliases for deployments that used the earlier draft
    # names.  The payment service always emits the canonical ``h5_type`` and
    # ``h5_return_url`` fields.
    h5_info_type: str = _env('WECHAT_PAY_H5_INFO_TYPE')
    h5_return_url: str = _env('WECHAT_PAY_H5_RETURN_URL')
    h5_redirect_url: str = _env('WECHAT_PAY_H5_REDIRECT_URL')
    app_pay_subject_prefix: str = _env('WECHAT_PAY_APP_SUBJECT_PREFIX', 'Excellent') or 'Excellent'


@dataclass(frozen=True)
class AlipayConfig:
    enabled: bool = _env_bool('ALIPAY_ENABLED', False)
    app_id: str = _env('ALIPAY_APP_ID')
    private_key_path: str = _env('ALIPAY_PRIVATE_KEY_PATH')
    app_cert_path: str = _env('ALIPAY_APP_CERT_PATH')
    alipay_public_cert_path: str = _env('ALIPAY_PUBLIC_CERT_PATH')
    root_cert_path: str = _env('ALIPAY_ROOT_CERT_PATH')
    notify_url: str = _env('ALIPAY_NOTIFY_URL')
    return_url: str = _env('ALIPAY_RETURN_URL')
    gateway_url: str = _env('ALIPAY_GATEWAY_URL', 'https://openapi.alipay.com/gateway.do') or 'https://openapi.alipay.com/gateway.do'
    payment_method: str = _env('ALIPAY_PAYMENT_METHOD', 'alipay.trade.wap.pay') or 'alipay.trade.wap.pay'
    charset: str = _env('ALIPAY_CHARSET', 'utf-8') or 'utf-8'
    sign_type: str = _env('ALIPAY_SIGN_TYPE', 'RSA2') or 'RSA2'
    sandbox_allow_unverified_query_response: bool = _env_bool(
        'ALIPAY_SANDBOX_ALLOW_UNVERIFIED_QUERY_RESPONSE',
        False,
    )
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
        channels = ['ALIPAY']
        # Mock mode intentionally does not require credentials, but an
        # explicitly enabled channel should still be selectable for local
        # integration testing.  Keep the historical default (only Alipay) when
        # the WeChat switch is left off.
        if active_config.wechat.enabled:
            channels.append('WECHAT')
        return channels

    channels = []
    if active_config.wechat.enabled:
        channels.append('WECHAT')
    if active_config.alipay.enabled:
        channels.append('ALIPAY')
    return channels


def _valid_url(value: str, *, require_https: bool) -> bool:
    candidate = str(value or '')
    if (
        not candidate
        or candidate != candidate.strip()
        or '\\' in candidate
        or any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in candidate)
    ):
        return False
    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname
        # Accessing ``port`` rejects malformed or out-of-range ports.
        _parsed_port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme.lower() not in {'http', 'https'}
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False
    return not require_https or parsed.scheme.lower() == 'https'


def _valid_wechat_refund_notify_url(value: str, *, require_https: bool) -> bool:
    """Validate WeChat's callback-only refund URL contract."""

    try:
        within_limit = len(value.encode('utf-8')) <= WECHAT_REFUND_NOTIFY_URL_MAX_BYTES
    except UnicodeEncodeError:
        return False
    return (
        within_limit
        and '?' not in value
        and '#' not in value
        and _valid_url(value, require_https=require_https)
    )


def load_alipay_certificates(path: str) -> list[x509.Certificate]:
    return x509.load_pem_x509_certificates(Path(path).read_bytes())


def alipay_certificate_sn(certificate: x509.Certificate) -> str:
    content = f'{certificate.issuer.rfc4514_string()}{certificate.serial_number}'
    return md5(content.encode('utf-8'), usedforsecurity=False).hexdigest()


def alipay_root_certificate_sn(certificates: list[x509.Certificate]) -> str:
    serial_numbers = [
        alipay_certificate_sn(certificate)
        for certificate in certificates
        if certificate.signature_algorithm_oid.dotted_string.startswith('1.2.840.113549.1.1')
    ]
    return '_'.join(serial_numbers)


def alipay_sandbox_query_bypass_enabled(config: AlipayConfig) -> bool:
    return (
        config.sandbox_allow_unverified_query_response
        and config.gateway_url == ALIPAY_SANDBOX_GATEWAY_URL
    )


def validate_payment_config(app_env: str, config: PaymentConfig | None = None) -> None:
    active_config = config or payment_config
    production = app_env.strip().lower() == 'production'
    errors: list[str] = []

    if production and active_config.mock_external_payment:
        errors.append('PAYMENT_MOCK_EXTERNAL_PAYMENT must be false in production')

    wechat = active_config.wechat
    if wechat.enabled and not active_config.mock_external_payment:
        required_values = {
            'WECHAT_PAY_APP_ID': wechat.app_id,
            'WECHAT_PAY_MCHID': wechat.mchid,
            'WECHAT_PAY_API_V3_KEY': wechat.api_v3_key,
            'WECHAT_PAY_MERCHANT_SERIAL_NO': wechat.merchant_serial_no,
            'WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH': wechat.merchant_private_key_path,
            'WECHAT_PAY_PLATFORM_CERT_PATH': wechat.platform_cert_path,
            'WECHAT_PAY_NOTIFY_URL': wechat.notify_url,
            'WECHAT_PAY_REFUND_NOTIFY_URL': wechat.refund_notify_url,
        }
        errors.extend(
            f'{name} is required when WECHAT_PAY_ENABLED=true'
            for name, value in required_values.items()
            if not value
        )

        # The service defaults to WAP when neither variable is supplied. Keep
        # startup validation aligned with that behavior while still allowing
        # the legacy alias to select an explicit type.
        h5_type = str(wechat.h5_type or wechat.h5_info_type or 'WAP').strip().upper()
        if h5_type not in {'WAP', 'WEB', 'IOS', 'APP', 'ANDROID'}:
            errors.append('WECHAT_PAY_H5_TYPE must be Wap, iOS, or Android')
        if wechat.api_v3_key and len(wechat.api_v3_key.encode('utf-8')) != 32:
            errors.append('WECHAT_PAY_API_V3_KEY must be exactly 32 bytes')

        key_paths = {
            'WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH': wechat.merchant_private_key_path,
            'WECHAT_PAY_PLATFORM_CERT_PATH': wechat.platform_cert_path,
        }
        for name, value in key_paths.items():
            if value and not Path(value).is_file():
                errors.append(f'{name} does not point to a readable file')

        if wechat.merchant_private_key_path and Path(wechat.merchant_private_key_path).is_file():
            try:
                private_key = load_pem_private_key(
                    Path(wechat.merchant_private_key_path).read_bytes(),
                    password=None,
                )
                if not isinstance(private_key, RSAPrivateKey) or private_key.key_size < 2048:
                    errors.append(
                        'WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH must contain an RSA private key of at least 2048 bits'
                    )
            except (OSError, TypeError, ValueError):
                errors.append(
                    'WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH does not contain a valid unencrypted PEM private key'
                )

        if wechat.platform_cert_path and Path(wechat.platform_cert_path).is_file():
            try:
                platform_certificates = x509.load_pem_x509_certificates(
                    Path(wechat.platform_cert_path).read_bytes()
                )
                if not platform_certificates:
                    errors.append('WECHAT_PAY_PLATFORM_CERT_PATH does not contain a certificate')
                else:
                    for certificate in platform_certificates:
                        public_key = certificate.public_key()
                        if not isinstance(public_key, RSAPublicKey) or public_key.key_size < 2048:
                            errors.append(
                                'WECHAT_PAY_PLATFORM_CERT_PATH must contain an RSA certificate of at least 2048 bits'
                            )
                            break
            except (OSError, TypeError, ValueError):
                errors.append('WECHAT_PAY_PLATFORM_CERT_PATH does not contain a valid PEM X.509 certificate')

        url_values = {
            'WECHAT_PAY_NOTIFY_URL': wechat.notify_url,
            'WECHAT_PAY_H5_RETURN_URL': wechat.h5_return_url or wechat.h5_redirect_url,
        }
        for name, value in url_values.items():
            if value and not _valid_url(value, require_https=production):
                scheme = 'HTTPS' if production else 'HTTP(S)'
                errors.append(f'{name} must be a valid {scheme} URL')
        if wechat.refund_notify_url and not _valid_wechat_refund_notify_url(
            wechat.refund_notify_url,
            require_https=production,
        ):
            scheme = 'HTTPS' if production else 'HTTP(S)'
            errors.append(
                'WECHAT_PAY_REFUND_NOTIFY_URL must be a valid '
                f'{scheme} URL without query or fragment and no longer than '
                f'{WECHAT_REFUND_NOTIFY_URL_MAX_BYTES} bytes'
            )

    alipay = active_config.alipay
    if alipay.enabled:
        required_values = {
            'ALIPAY_APP_ID': alipay.app_id,
            'ALIPAY_PRIVATE_KEY_PATH': alipay.private_key_path,
            'ALIPAY_APP_CERT_PATH': alipay.app_cert_path,
            'ALIPAY_PUBLIC_CERT_PATH': alipay.alipay_public_cert_path,
            'ALIPAY_ROOT_CERT_PATH': alipay.root_cert_path,
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
        if (
            alipay.sandbox_allow_unverified_query_response
            and alipay.gateway_url != ALIPAY_SANDBOX_GATEWAY_URL
        ):
            errors.append(
                'ALIPAY_SANDBOX_ALLOW_UNVERIFIED_QUERY_RESPONSE is only allowed '
                f'with ALIPAY_GATEWAY_URL={ALIPAY_SANDBOX_GATEWAY_URL}'
            )

        key_paths = {
            'ALIPAY_PRIVATE_KEY_PATH': alipay.private_key_path,
            'ALIPAY_APP_CERT_PATH': alipay.app_cert_path,
            'ALIPAY_PUBLIC_CERT_PATH': alipay.alipay_public_cert_path,
            'ALIPAY_ROOT_CERT_PATH': alipay.root_cert_path,
        }
        for name, value in key_paths.items():
            if value and not Path(value).is_file():
                errors.append(f'{name} does not point to a readable file')

        private_key = None
        if alipay.private_key_path and Path(alipay.private_key_path).is_file():
            try:
                private_key = load_pem_private_key(Path(alipay.private_key_path).read_bytes(), password=None)
                if not isinstance(private_key, RSAPrivateKey) or private_key.key_size < 2048:
                    errors.append('ALIPAY_PRIVATE_KEY_PATH must contain an RSA private key of at least 2048 bits')
            except (TypeError, ValueError):
                errors.append('ALIPAY_PRIVATE_KEY_PATH does not contain a valid unencrypted PEM private key')

        parsed_certificates: dict[str, list[x509.Certificate]] = {}
        for name, value in {
            'ALIPAY_APP_CERT_PATH': alipay.app_cert_path,
            'ALIPAY_PUBLIC_CERT_PATH': alipay.alipay_public_cert_path,
            'ALIPAY_ROOT_CERT_PATH': alipay.root_cert_path,
        }.items():
            if not value or not Path(value).is_file():
                continue
            try:
                parsed_certificates[name] = load_alipay_certificates(value)
            except ValueError:
                errors.append(f'{name} does not contain a valid PEM X.509 certificate')

        app_certificates = parsed_certificates.get('ALIPAY_APP_CERT_PATH', [])
        if app_certificates:
            app_public_key = app_certificates[0].public_key()
            if not isinstance(app_public_key, RSAPublicKey) or app_public_key.key_size < 2048:
                errors.append('ALIPAY_APP_CERT_PATH must contain an RSA certificate of at least 2048 bits')
            elif isinstance(private_key, RSAPrivateKey) and app_public_key.public_numbers() != private_key.public_key().public_numbers():
                errors.append('ALIPAY_APP_CERT_PATH does not match ALIPAY_PRIVATE_KEY_PATH')

        alipay_certificates = parsed_certificates.get('ALIPAY_PUBLIC_CERT_PATH', [])
        if alipay_certificates:
            alipay_public_key = alipay_certificates[0].public_key()
            if not isinstance(alipay_public_key, RSAPublicKey) or alipay_public_key.key_size < 2048:
                errors.append('ALIPAY_PUBLIC_CERT_PATH must contain an RSA certificate of at least 2048 bits')

        root_certificates = parsed_certificates.get('ALIPAY_ROOT_CERT_PATH', [])
        if root_certificates and not alipay_root_certificate_sn(root_certificates):
            errors.append('ALIPAY_ROOT_CERT_PATH does not contain an RSA root certificate')

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
