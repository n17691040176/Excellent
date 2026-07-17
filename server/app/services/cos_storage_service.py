from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from qcloud_cos import CosClientError, CosConfig, CosS3Client, CosServiceError

from app.core.config import settings
from app.core.exceptions import AppError


class CosStorageService:
    IMAGE_TYPES = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
        'image/gif': '.gif',
    }

    @staticmethod
    def _ensure_configured() -> None:
        required = {
            'SecretId': settings.tencent_cos_secret_id,
            'SecretKey': settings.tencent_cos_secret_key,
            'Region': settings.tencent_cos_region,
            'Bucket': settings.tencent_cos_bucket,
        }
        missing = [name for name, value in required.items() if not str(value or '').strip()]
        if not settings.tencent_cos_enabled:
            raise AppError('腾讯云 COS 尚未启用')
        if missing:
            raise AppError(f"腾讯云 COS 配置不完整：{', '.join(missing)}")

    @staticmethod
    def _public_base_url() -> str:
        configured_url = str(
            settings.tencent_cos_public_base_url or settings.tencent_cos_endpoint or ''
        ).strip()
        if configured_url:
            if not configured_url.startswith(('http://', 'https://')):
                configured_url = f'https://{configured_url}'
            return configured_url.rstrip('/')

        bucket = str(settings.tencent_cos_bucket or '').strip()
        region = str(settings.tencent_cos_region or '').strip()
        return f'https://{bucket}.cos.{region}.myqcloud.com'

    @staticmethod
    def _client() -> CosS3Client:
        CosStorageService._ensure_configured()
        config = CosConfig(
            Region=settings.tencent_cos_region,
            SecretId=settings.tencent_cos_secret_id,
            SecretKey=settings.tencent_cos_secret_key,
            Scheme='https',
        )
        return CosS3Client(config)

    @staticmethod
    def _detect_image_type(data: bytes) -> tuple[str, str] | None:
        if data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg', '.jpg'
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png', '.png'
        if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp', '.webp'
        if data.startswith((b'GIF87a', b'GIF89a')):
            return 'image/gif', '.gif'
        return None

    @staticmethod
    def _product_object_key(filename: str, suffix: str) -> str:
        prefix = str(settings.tencent_cos_product_prefix or 'products').strip().strip('/') or 'products'
        month = datetime.now(UTC).strftime('%Y%m')
        original_stem = Path(filename or 'image').stem[:40]
        safe_stem = ''.join(char for char in original_stem if char.isalnum() or char in {'-', '_'}) or 'image'
        return f'{prefix}/{month}/{safe_stem}-{uuid4().hex}{suffix}'

    @staticmethod
    def upload_product_image(filename: str, content_type: str, data: bytes) -> dict:
        if not data:
            raise AppError('上传图片不能为空')
        if len(data) > settings.tencent_cos_max_upload_size:
            max_mb = max(1, settings.tencent_cos_max_upload_size // (1024 * 1024))
            raise AppError(f'图片不能超过 {max_mb}MB')

        detected = CosStorageService._detect_image_type(data)
        if not detected:
            raise AppError('仅支持 JPG、PNG、WebP、GIF 图片')
        detected_type, suffix = detected
        if content_type and content_type not in CosStorageService.IMAGE_TYPES:
            raise AppError('图片文件类型不受支持')

        key = CosStorageService._product_object_key(filename, suffix)
        client = CosStorageService._client()
        try:
            response = client.put_object(
                Bucket=settings.tencent_cos_bucket,
                Body=data,
                Key=key,
                ContentType=detected_type,
                CacheControl='public, max-age=31536000, immutable',
                ACL='public-read',
            )
        except CosServiceError as exc:
            raise AppError(f'COS 上传失败：{exc.get_error_code() or "ServiceError"}') from exc
        except CosClientError as exc:
            raise AppError('COS 上传失败，请检查网络和密钥配置') from exc

        public_base_url = CosStorageService._public_base_url()
        return {
            'key': key,
            'url': f'{public_base_url}/{key}',
            'filename': Path(key).name,
            'size': len(data),
            'content_type': detected_type,
            'etag': str(response.get('ETag') or '').strip('"'),
        }

    @staticmethod
    def delete_object(key: str) -> None:
        normalized_key = str(key or '').strip().lstrip('/')
        if not normalized_key:
            return
        client = CosStorageService._client()
        try:
            client.delete_object(Bucket=settings.tencent_cos_bucket, Key=normalized_key)
        except (CosServiceError, CosClientError) as exc:
            raise AppError('COS 测试文件清理失败') from exc
