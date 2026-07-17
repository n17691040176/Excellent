from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'Excellent App Backend'
    app_env: str = 'development'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    app_debug: bool = True
    secret_key: str = 'change-me'
    jwt_expire_minutes: int = 1440
    access_token_expire_minutes: int = 1440

    mysql_host: str = '127.0.0.1'
    mysql_port: int = 3306
    mysql_user: str = 'root'
    mysql_password: str = '123456'
    mysql_db: str = 'excellent_app'
    mysql_pool_size: int = 10
    mysql_max_overflow: int = 20

    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ''

    celery_broker_url: str = 'redis://127.0.0.1:6379/1'
    celery_result_backend: str = 'redis://127.0.0.1:6379/2'

    cors_origins: str = 'http://localhost:5173,http://localhost:5174'
    log_level: str = 'INFO'

    tencent_cos_enabled: bool = False
    tencent_cos_secret_id: str = ''
    tencent_cos_secret_key: str = ''
    tencent_cos_region: str = ''
    tencent_cos_bucket: str = ''
    tencent_cos_endpoint: str = ''
    tencent_cos_public_base_url: str = ''
    tencent_cos_product_prefix: str = 'products'
    tencent_cos_max_upload_size: int = 5 * 1024 * 1024

    # 阿里云一键登录配置
    dynpns_enabled: bool = False
    dynpns_access_key_id: str = ''
    dynpns_access_key_secret: str = ''
    dynpns_signature_secret: str = ''
    dynpns_app_key: str = ''

    # 短信验证码配置（备用）
    sms_enabled: bool = True
    sms_aliyun_access_key_id: str = ''
    sms_aliyun_access_key_secret: str = ''
    sms_sign_name: str = '卓越科技'
    sms_template_code: str = ''
    sms_template_param_name: str = 'code'

    payment_mock_external_payment: bool | None = None
    payment_default_currency: str | None = None
    payment_request_timeout_seconds: int | None = None
    wechat_pay_enabled: bool | None = None
    wechat_pay_app_id: str | None = None
    wechat_pay_mchid: str | None = None
    wechat_pay_api_v3_key: str | None = None
    wechat_pay_merchant_serial_no: str | None = None
    wechat_pay_merchant_private_key_path: str | None = None
    wechat_pay_platform_cert_path: str | None = None
    wechat_pay_notify_url: str | None = None
    wechat_pay_app_pay_subject_prefix: str | None = None
    alipay_enabled: bool | None = None
    alipay_app_id: str | None = None
    alipay_private_key_path: str | None = None
    alipay_public_key_path: str | None = None
    alipay_notify_url: str | None = None
    alipay_return_url: str | None = None
    alipay_gateway_url: str | None = None
    alipay_payment_method: str | None = None
    alipay_charset: str | None = None
    alipay_sign_type: str | None = None
    alipay_seller_id: str | None = None
    alipay_app_subject_prefix: str | None = None

    model_config = SettingsConfigDict(
        env_file=('.env', '.env.alipay.local'),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    @property
    def database_url(self) -> str:
        return (
            f'mysql+pymysql://{self.mysql_user}:{self.mysql_password}'
            f'@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4'
        )

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(',') if item.strip()]

    @property
    def redis_url(self) -> str:
        auth = f':{self.redis_password}@' if self.redis_password else ''
        return f'redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}'


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
