from pathlib import Path

import pytest

from app.core.exceptions import AppError
from app.services.page_decoration_service import PageDecorationService


def test_store_mobile_home_image_writes_to_upload_root(tmp_path, monkeypatch):
    monkeypatch.setattr(PageDecorationService, 'upload_root', staticmethod(lambda: tmp_path))

    result = PageDecorationService.store_mobile_home_image(
        'hero.png',
        'image/png',
        b'png-bytes',
    )

    target = tmp_path / result['path']
    assert result['url'] == f"/uploads/{result['path']}"
    assert target == next(tmp_path.glob('decorations/mobile-home/*/*.png'))
    assert target.read_bytes() == b'png-bytes'


@pytest.mark.parametrize(
    ('filename', 'content_type', 'data', 'message'),
    [
        ('empty.png', 'image/png', b'', '上传图片不能为空'),
        ('bad.txt', 'text/plain', b'not-an-image', '仅支持上传图片文件'),
    ],
)
def test_store_mobile_home_image_rejects_invalid_input(filename, content_type, data, message):
    with pytest.raises(AppError, match=message):
        PageDecorationService.store_mobile_home_image(filename, content_type, data)


def test_store_mobile_home_image_maps_filesystem_errors_to_service_error(monkeypatch, tmp_path):
    target_root = tmp_path / 'uploads'
    monkeypatch.setattr(PageDecorationService, 'upload_root', staticmethod(lambda: target_root))

    def fail_mkdir(*args, **kwargs):
        raise PermissionError('read-only volume')

    monkeypatch.setattr(Path, 'mkdir', fail_mkdir)

    with pytest.raises(AppError) as error:
        PageDecorationService.store_mobile_home_image('hero.png', 'image/png', b'png-bytes')

    assert error.value.code == 50002
    assert error.value.status_code == 503


def test_store_mobile_home_image_maps_upload_root_errors_to_service_error(monkeypatch):
    def fail_upload_root():
        raise PermissionError('read-only volume')

    monkeypatch.setattr(PageDecorationService, 'upload_root', staticmethod(fail_upload_root))

    with pytest.raises(AppError) as error:
        PageDecorationService.store_mobile_home_image('hero.png', 'image/png', b'png-bytes')

    assert error.value.code == 50002
    assert error.value.status_code == 503
