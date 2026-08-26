import logging
from contextlib import suppress
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.page_decoration import PageDecoration
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.utils.helpers import iso_datetime

MOBILE_UNI_HOME_KEY = 'mobile_uni_home'
MOBILE_UNI_HOME_TITLE = 'uni 首页装修'
logger = logging.getLogger(__name__)


class PageDecorationService:
    IMAGE_SUFFIX_MAP = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/webp': '.webp',
        'image/gif': '.gif',
    }
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024

    @staticmethod
    def supported_custom_block_types() -> set[str]:
        return {'banner', 'grid', 'coupon_strip', 'zone_feed', 'image_swiper', 'mixed_goods'}

    @staticmethod
    def supported_zone_keys() -> set[str]:
        return {'repurchase', 'selfOperated', 'hotSale', 'localLife'}

    @staticmethod
    def upload_root() -> Path:
        path = Path(__file__).resolve().parents[2] / 'uploads'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def mobile_uni_home_layout() -> list[str]:
        return ['announcement', 'zone_section', 'waterfall_section', 'package_section', 'promo_section', 'quick_section']

    @staticmethod
    def default_home_swiper_block() -> dict:
        return {
            'id': 'home_swiper_main',
            'type': 'image_swiper',
            'enabled': True,
            'title': '首页轮播',
            'section_kicker': 'Featured',
            'count_suffix': '张',
            'kicker': '精选活动',
            'desc': '主推活动、重点分区和新内容统一展示。',
            'tags': ['当日精选', '持续上新'],
            'slide_tags': ['专题推荐', '立即进入'],
            'autoplay': True,
            'items': [
                {
                    'enabled': True,
                    'badge': '商城主推',
                    'title': '热门专区与首单权益一起前置',
                    'desc': '参考主流电商首页，把主推活动、分区会场和转化入口收进首屏轮播。',
                    'image_url': '',
                    'path': '/pages/packages/list',
                    'open_type': 'switchTab',
                },
                {
                    'enabled': True,
                    'badge': '本地生活',
                    'title': '到店服务和联盟商家进入底部导航',
                    'desc': '把本地生活从二级入口抬升到底部栏，门店服务触达更直接。',
                    'image_url': '',
                    'path': '/pages/local-life/index',
                    'open_type': 'switchTab',
                },
                {
                    'enabled': True,
                    'badge': '爆款专区',
                    'title': '首页下滑直达双列瀑布商品流',
                    'desc': '支持下拉刷新和继续加载，持续承接爆款、自营和本地生活内容。',
                    'image_url': '',
                    'path': '/pages/packages/list',
                    'open_type': 'switchTab',
                },
            ],
        }

    @staticmethod
    def default_mobile_uni_home_payload() -> dict:
        home_swiper = PageDecorationService.default_home_swiper_block()
        return {
            'layout': [f"custom:{home_swiper['id']}", *PageDecorationService.mobile_uni_home_layout()],
            'custom_blocks': [home_swiper],
            'announcement': {
                'enabled': True,
                'title': '首页提醒',
                'lines': [
                    '首页首屏统一承接轮播活动、四区导航和推荐商品流。',
                    '订单统一收进“我的”，本地生活已经进入底部导航栏。',
                ],
            },
            'waterfall_section': {
                'enabled': True,
                'title': '推荐好货',
                'subtitle': '下拉刷新，继续发现',
                'page_size': 8,
                'source_keys': ['hotSale', 'selfOperated', 'localLife'],
            },
            'package_section': {
                'enabled': True,
                'title': '套餐入口',
                'desc': '套餐仍保留在首页中段，服务入场资格、抵扣规则和经营权益判断。',
                'limit': 2,
            },
            'promo_section': {
                'enabled': True,
                'title': '会场推荐',
                'subtitle': '运营精选',
                'items': [
                    {
                        'enabled': True,
                        'badge': '新人转化',
                        'title': '首单先看权益和热门专区',
                        'desc': '把新手礼包、主推套餐和爆款商品收进同一层转化入口。',
                        'path': '/pages/packages/list',
                        'open_type': 'switchTab',
                    },
                    {
                        'enabled': True,
                        'badge': '本地生活',
                        'title': '到店服务和联盟商家进入底部栏',
                        'desc': '本地生活从首页运营卡升级为底部导航，门店服务触达更直接。',
                        'path': '/pages/local-life/index',
                        'open_type': 'switchTab',
                    },
                ],
            },
            'zone_section': {
                'enabled': True,
                'title': '四区导航',
                'subtitle': '热门分区',
                'items': [
                    {'enabled': True, 'key': 'repurchase', 'title': '复购区', 'tip': '套餐进入，二次复购 4-6 折', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/packages/list', 'open_type': 'switchTab'},
                    {'enabled': True, 'key': 'selfOperated', 'title': '自营商城', 'tip': '兑换券 5-7 折抵扣，返 AI 券', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/packages/list', 'open_type': 'switchTab'},
                    {'enabled': True, 'key': 'hotSale', 'title': '爆款区', 'tip': '低价抢购，支持积分或余额', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/packages/list', 'open_type': 'switchTab'},
                    {'enabled': True, 'key': 'localLife', 'title': '本地生活', 'tip': '联盟商家服务、门店履约与收益联动', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/local-life/index', 'open_type': 'switchTab'},
                ],
            },
            'quick_section': {
                'enabled': True,
                'title': '我的常用',
                'subtitle': '个人中心',
                'items': [
                    {'enabled': True, 'title': '套餐中心', 'desc': '查看入场资格与权益档位', 'icon_url': '', 'path': '/pages/packages/list', 'open_type': 'switchTab'},
                    {'enabled': True, 'title': '我的团队', 'desc': '管理归属团队与成员结构', 'icon_url': '', 'path': '/subpackages/team/index', 'open_type': 'navigate'},
                    {'enabled': True, 'title': '邀请好友', 'desc': '分享邀请码完成绑定', 'icon_url': '', 'path': '/subpackages/invite/index', 'open_type': 'navigate'},
                    {'enabled': True, 'title': '佣金中心', 'desc': '跟进冻结与可提现状态', 'icon_url': '', 'path': '/subpackages/commission/index', 'open_type': 'navigate'},
                    {'enabled': True, 'title': '我的资产', 'desc': '查看余额、消费金、积分和充电宝', 'icon_url': '', 'path': '/subpackages/assets/index', 'open_type': 'navigate'},
                    {'enabled': True, 'title': '个人中心', 'desc': '维护资料、签到和账号设置', 'icon_url': '', 'path': '/pages/profile/index', 'open_type': 'switchTab'},
                ],
            },
        }

    @staticmethod
    def growth_mobile_uni_home_payload() -> dict:
        payload = deepcopy(PageDecorationService.default_mobile_uni_home_payload())
        payload['announcement']['title'] = '增长重点'
        payload['announcement']['lines'] = [
            '先用首屏轮播和瀑布流拉起点击，再承接套餐和邀请绑定。',
            '订单沉淀到“我的”，首页不再承担订单中心角色。',
        ]
        payload['layout'] = ['custom:home_swiper_main', 'announcement', 'zone_section', 'waterfall_section', 'package_section', 'promo_section', 'quick_section']
        payload['promo_section']['items'] = [
            {
                'enabled': True,
                'badge': '拉新优先',
                'title': '邀请码和热门专区联动转化',
                'desc': '先让用户点击活动和热区，再承接邀请绑定和首单。',
                'path': '/subpackages/invite/index',
                'open_type': 'navigate',
            },
            {
                'enabled': True,
                'badge': '转化优先',
                'title': '瀑布流继续承接套餐和爆款商品',
                'desc': '首屏转化后，继续用双列商品流推动点击和下单。',
                'path': '/pages/packages/list',
                'open_type': 'switchTab',
            },
        ]
        return payload

    @staticmethod
    def local_life_mobile_uni_home_payload() -> dict:
        payload = deepcopy(PageDecorationService.default_mobile_uni_home_payload())
        payload['announcement']['title'] = '本地生活重点'
        payload['announcement']['lines'] = [
            '轮播和瀑布流都会优先承接本地生活内容与服务供给。',
            '本地生活已进入底部导航，首页保留四区导流与推荐承接。',
        ]
        payload['layout'] = ['custom:home_swiper_main', 'announcement', 'zone_section', 'waterfall_section', 'promo_section', 'package_section', 'quick_section']
        payload['promo_section']['items'] = [
            {
                'enabled': True,
                'badge': '门店履约',
                'title': '本地生活订单围绕核销节点组织',
                'desc': '支付后待核销，核销完成后再进入佣金释放和结算。',
                'path': '/subpackages/life/orders',
                'open_type': 'navigate',
            },
            {
                'enabled': True,
                'badge': '商家经营',
                'title': '先看联盟商家，再看服务供给',
                'desc': '让线下团队更快判断门店规模和商品服务承接能力。',
                'path': '/pages/local-life/index',
                'open_type': 'switchTab',
            },
        ]
        payload['zone_section']['items'] = [
            {'enabled': True, 'key': 'localLife', 'title': '本地生活', 'tip': '联盟商家服务、门店履约与收益联动', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/local-life/index', 'open_type': 'switchTab'},
            {'enabled': True, 'key': 'repurchase', 'title': '复购区', 'tip': '套餐进入，二次复购 4-6 折', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/packages/list', 'open_type': 'switchTab'},
            {'enabled': True, 'key': 'selfOperated', 'title': '自营商城', 'tip': '兑换券 5-7 折抵扣，返 AI 券', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/packages/list', 'open_type': 'switchTab'},
            {'enabled': True, 'key': 'hotSale', 'title': '爆款区', 'tip': '低价抢购，支持积分或余额', 'icon_url': '', 'link_text': '进入专区', 'show_count': True, 'path': '/pages/packages/list', 'open_type': 'switchTab'},
        ]
        payload['waterfall_section'] = {
            'enabled': True,
            'title': '本地优选',
            'subtitle': '门店服务和热点专区混排推荐',
            'page_size': 8,
            'source_keys': ['localLife', 'hotSale', 'selfOperated'],
        }
        return payload

    @staticmethod
    def _clean_text(value, fallback='') -> str:
        return str(value or fallback).strip()

    @staticmethod
    def _clean_text_field(source, field, fallback='') -> str:
        if isinstance(source, dict) and field in source:
            return PageDecorationService._clean_text(source.get(field))
        return PageDecorationService._clean_text(fallback)

    @staticmethod
    def _clean_bool(value, fallback=True) -> bool:
        if isinstance(value, bool):
            return value
        if value in {'true', '1', 1}:
            return True
        if value in {'false', '0', 0}:
            return False
        return fallback

    @staticmethod
    def _clean_string_list(values, fallback=None) -> list[str]:
        items = values if isinstance(values, list) else fallback or []
        return [str(item).strip() for item in items if str(item).strip()]

    @staticmethod
    def _clean_layout(values, fallback=None) -> list[str]:
        default_layout = fallback or PageDecorationService.mobile_uni_home_layout()
        source = values if isinstance(values, list) else default_layout
        rows: list[str] = []
        allowed = set(PageDecorationService.mobile_uni_home_layout())
        for item in source:
            key = str(item or '').strip()
            if key and key in allowed and key not in rows:
                rows.append(key)
        for key in default_layout:
            if key not in rows:
                rows.append(key)
        return rows

    @staticmethod
    def _clean_layout_with_custom(values, fallback=None, custom_blocks=None) -> list[str]:
        base = PageDecorationService._clean_layout(values, fallback)
        blocks = custom_blocks if isinstance(custom_blocks, list) else []
        allowed_custom = {f"custom:{item['id']}" for item in blocks if item.get('id')}
        source = values if isinstance(values, list) else []
        custom_rows: list[str] = []
        for item in source:
            key = str(item or '').strip()
            if key in allowed_custom and key not in custom_rows:
                custom_rows.append(key)
        for item in blocks:
            key = f"custom:{item['id']}"
            if key not in custom_rows:
                custom_rows.append(key)
        rows: list[str] = []
        for item in source:
            key = str(item or '').strip()
            if key in base and key not in rows:
                rows.append(key)
            if key in custom_rows and key not in rows:
                rows.append(key)
        for key in base + custom_rows:
            if key not in rows:
                rows.append(key)
        return rows

    @staticmethod
    def _clean_identifier(value, fallback='block') -> str:
        text = str(value or fallback).strip().lower()
        chars = []
        for char in text:
            if char.isalnum() or char in {'_', '-'}:
                chars.append(char)
            elif char in {' ', ':'}:
                chars.append('_')
        return ''.join(chars).strip('_') or fallback

    @staticmethod
    def _clean_choice(value, allowed: set[str], fallback: str) -> str:
        text = PageDecorationService._clean_text(value, fallback)
        return text if text in allowed else fallback

    @staticmethod
    def _normalize_grid_items(items) -> list[dict]:
        rows = []
        source = items if isinstance(items, list) else []
        for item in source:
            item = item or {}
            row = {
                'enabled': PageDecorationService._clean_bool(item.get('enabled'), True),
                'title': PageDecorationService._clean_text(item.get('title')),
                'desc': PageDecorationService._clean_text(item.get('desc')),
                'icon_url': PageDecorationService._clean_text(item.get('icon_url')),
                'path': PageDecorationService._clean_text(item.get('path')),
                'open_type': PageDecorationService._clean_text(item.get('open_type'), 'navigate'),
            }
            if row['enabled'] or row['title'] or row['desc'] or row['icon_url'] or row['path']:
                rows.append(row)
        return rows

    @staticmethod
    def _normalize_swiper_items(items) -> list[dict]:
        rows = []
        source = items if isinstance(items, list) else []
        for item in source:
            item = item or {}
            row = {
                'enabled': PageDecorationService._clean_bool(item.get('enabled'), True),
                'badge': PageDecorationService._clean_text(item.get('badge')),
                'title': PageDecorationService._clean_text(item.get('title')),
                'desc': PageDecorationService._clean_text(item.get('desc')),
                'image_url': PageDecorationService._clean_text(item.get('image_url')),
                'path': PageDecorationService._clean_text(item.get('path')),
                'open_type': PageDecorationService._clean_text(item.get('open_type'), 'navigate'),
            }
            if row['enabled'] or row['badge'] or row['title'] or row['desc'] or row['image_url'] or row['path']:
                rows.append(row)
        return rows

    @staticmethod
    def _normalize_mixed_goods_items(items) -> list[dict]:
        rows = []
        source = items if isinstance(items, list) else []
        for item in source:
            item = item or {}
            row = {
                'enabled': PageDecorationService._clean_bool(item.get('enabled'), True),
                'tag': PageDecorationService._clean_text(item.get('tag')),
                'title': PageDecorationService._clean_text(item.get('title')),
                'desc': PageDecorationService._clean_text(item.get('desc')),
                'price_text': PageDecorationService._clean_text(item.get('price_text')),
                'path': PageDecorationService._clean_text(item.get('path')),
                'open_type': PageDecorationService._clean_text(item.get('open_type'), 'navigate'),
            }
            if row['enabled'] or row['tag'] or row['title'] or row['desc'] or row['price_text'] or row['path']:
                rows.append(row)
        return rows

    @staticmethod
    def _normalize_custom_blocks(blocks) -> list[dict]:
        source = blocks if isinstance(blocks, list) else []
        rows = []
        for index, block in enumerate(source, start=1):
            block = block or {}
            block_type = PageDecorationService._clean_text(block.get('type'), 'banner')
            block_id = PageDecorationService._clean_identifier(block.get('id'), f'block_{index}')
            base = {
                'id': block_id,
                'type': block_type if block_type in PageDecorationService.supported_custom_block_types() else 'banner',
                'enabled': PageDecorationService._clean_bool(block.get('enabled'), True),
            }
            if base['type'] == 'grid':
                base.update({
                    'title': PageDecorationService._clean_text(block.get('title')),
                    'subtitle': PageDecorationService._clean_text(block.get('subtitle')),
                    'items': PageDecorationService._normalize_grid_items(block.get('items')),
                })
            elif base['type'] == 'zone_feed':
                base.update({
                    'title': PageDecorationService._clean_text(block.get('title')),
                    'subtitle': PageDecorationService._clean_text(block.get('subtitle')),
                    'source_key': PageDecorationService._clean_choice(
                        block.get('source_key'),
                        PageDecorationService.supported_zone_keys(),
                        'repurchase',
                    ),
                    'limit': max(1, min(int(block.get('limit') or 4), 12)),
                    'path': PageDecorationService._clean_text(block.get('path')),
                    'open_type': PageDecorationService._clean_text(block.get('open_type'), 'navigate'),
                })
            elif base['type'] == 'coupon_strip':
                base.update({
                    'badge': PageDecorationService._clean_text(block.get('badge')),
                    'title': PageDecorationService._clean_text(block.get('title')),
                    'desc': PageDecorationService._clean_text(block.get('desc')),
                    'path': PageDecorationService._clean_text(block.get('path')),
                    'open_type': PageDecorationService._clean_text(block.get('open_type'), 'navigate'),
                })
            elif base['type'] == 'image_swiper':
                fallback_block = PageDecorationService.default_home_swiper_block() if block_id == 'home_swiper_main' else {}
                swiper_items = block.get('items') if isinstance(block.get('items'), list) else fallback_block.get('items')
                base.update({
                    'title': PageDecorationService._clean_text_field(block, 'title', fallback_block.get('title', '')),
                    'section_kicker': PageDecorationService._clean_text_field(block, 'section_kicker', fallback_block.get('section_kicker', '')),
                    'count_suffix': PageDecorationService._clean_text_field(block, 'count_suffix', fallback_block.get('count_suffix', '')),
                    'kicker': PageDecorationService._clean_text_field(block, 'kicker', fallback_block.get('kicker', '')),
                    'desc': PageDecorationService._clean_text_field(block, 'desc', fallback_block.get('desc', '')),
                    'tags': PageDecorationService._clean_string_list(block.get('tags'), fallback_block.get('tags', [])),
                    'slide_tags': PageDecorationService._clean_string_list(block.get('slide_tags'), fallback_block.get('slide_tags', [])),
                    'autoplay': PageDecorationService._clean_bool(block.get('autoplay'), True),
                    'items': PageDecorationService._normalize_swiper_items(swiper_items),
                })
            elif base['type'] == 'mixed_goods':
                base.update({
                    'title': PageDecorationService._clean_text(block.get('title')),
                    'subtitle': PageDecorationService._clean_text(block.get('subtitle')),
                    'items': PageDecorationService._normalize_mixed_goods_items(block.get('items')),
                })
            else:
                base.update({
                    'badge': PageDecorationService._clean_text(block.get('badge')),
                    'title': PageDecorationService._clean_text(block.get('title')),
                    'desc': PageDecorationService._clean_text(block.get('desc')),
                    'button_text': PageDecorationService._clean_text(block.get('button_text'), '立即查看'),
                    'path': PageDecorationService._clean_text(block.get('path')),
                    'open_type': PageDecorationService._clean_text(block.get('open_type'), 'navigate'),
                })
            rows.append(base)
        return rows

    @staticmethod
    def _normalize_item_list(items, defaults, field_rules) -> list[dict]:
        source = items if isinstance(items, list) else defaults
        rows = []
        for item in source:
            item = item or {}
            row: dict[str, object] = {'enabled': PageDecorationService._clean_bool(item.get('enabled'), True)}
            for field, fallback in field_rules.items():
                row[field] = PageDecorationService._clean_text(item.get(field), fallback)
            if row['enabled'] or any(value for key, value in row.items() if key != 'enabled'):
                rows.append(row)
        return rows

    @staticmethod
    def _normalize_zone_items(items, defaults) -> list[dict]:
        source = items if isinstance(items, list) else defaults
        rows = []
        for item in source:
            item = item or {}
            row = {
                'enabled': PageDecorationService._clean_bool(item.get('enabled'), True),
                'key': PageDecorationService._clean_text(item.get('key')),
                'title': PageDecorationService._clean_text(item.get('title')),
                'tip': PageDecorationService._clean_text(item.get('tip')),
                'icon_url': PageDecorationService._clean_text(item.get('icon_url')),
                'link_text': PageDecorationService._clean_text_field(item, 'link_text', '进入专区'),
                'show_count': PageDecorationService._clean_bool(item.get('show_count'), True),
                'path': PageDecorationService._clean_text(item.get('path')),
                'open_type': PageDecorationService._clean_text(item.get('open_type'), 'navigate'),
            }
            if row['enabled'] or any(value for key, value in row.items() if key not in {'enabled', 'show_count'}):
                rows.append(row)
        return rows

    @staticmethod
    def store_mobile_home_image(filename: str, content_type: str, data: bytes) -> dict:
        if not data:
            raise AppError('上传图片不能为空')
        if len(data) > PageDecorationService.MAX_UPLOAD_SIZE:
            raise AppError('图片不能超过 5MB')
        if not str(content_type or '').startswith('image/'):
            raise AppError('仅支持上传图片文件')

        suffix = Path(filename or '').suffix.lower()
        if suffix not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            suffix = PageDecorationService.IMAGE_SUFFIX_MAP.get(content_type, '.jpg')

        upload_root: Path | None = None
        target_path: Path | None = None
        try:
            upload_root = PageDecorationService.upload_root()
            month_dir = datetime.now(UTC).strftime('%Y%m')
            target_dir = upload_root / 'decorations' / 'mobile-home' / month_dir
            target_name = f'{uuid4().hex}{suffix}'
            target_path = target_dir / target_name
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(data)
        except OSError as exc:
            # Do not leak a raw PermissionError/IOError as an opaque HTTP 500.
            # The container entrypoint repairs the normal volume-permission case,
            # while this response still gives operators a useful failure mode for
            # a read-only mount, full disk, or other storage outage.
            if target_path is not None:
                with suppress(OSError):
                    target_path.unlink(missing_ok=True)
            logger.exception('Failed to persist mobile decoration image at %s', target_path or '<upload-root>')
            raise AppError('图片存储暂时不可用，请稍后重试', code=50002, status_code=503) from exc

        relative_path = target_path.relative_to(upload_root).as_posix()
        return {
            'path': relative_path,
            'url': f'/uploads/{relative_path}',
            'filename': target_name,
            'size': len(data),
            'content_type': content_type,
        }

    @staticmethod
    def normalize_mobile_uni_home_payload(payload: dict | None) -> dict:
        defaults = PageDecorationService.default_mobile_uni_home_payload()
        source = payload if isinstance(payload, dict) else {}
        announcement = source.get('announcement') or {}
        package_section = source.get('package_section') or {}
        promo_section = source.get('promo_section') or {}
        zone_section = source.get('zone_section') or {}
        quick_section = source.get('quick_section') or {}
        waterfall_section = source.get('waterfall_section') or {}
        custom_blocks_source = source.get('custom_blocks') if isinstance(source.get('custom_blocks'), list) else defaults['custom_blocks']
        custom_blocks = PageDecorationService._normalize_custom_blocks(custom_blocks_source)

        normalized = deepcopy(defaults)
        normalized['custom_blocks'] = custom_blocks
        normalized['layout'] = PageDecorationService._clean_layout_with_custom(
            source.get('layout'),
            defaults['layout'],
            custom_blocks,
        )
        normalized['announcement'] = {
            'enabled': PageDecorationService._clean_bool(announcement.get('enabled'), defaults['announcement']['enabled']),
            'title': PageDecorationService._clean_text_field(announcement, 'title', defaults['announcement']['title']),
            'lines': PageDecorationService._clean_string_list(announcement.get('lines'), defaults['announcement']['lines']),
        }
        normalized['package_section'] = {
            'enabled': PageDecorationService._clean_bool(package_section.get('enabled'), defaults['package_section']['enabled']),
            'title': PageDecorationService._clean_text_field(package_section, 'title', defaults['package_section']['title']),
            'desc': PageDecorationService._clean_text(package_section.get('desc'), defaults['package_section']['desc']),
            'limit': max(1, min(int(package_section.get('limit') or defaults['package_section']['limit']), 6)),
        }
        normalized['promo_section'] = {
            'enabled': PageDecorationService._clean_bool(promo_section.get('enabled'), defaults['promo_section']['enabled']),
            'title': PageDecorationService._clean_text_field(promo_section, 'title', defaults['promo_section']['title']),
            'subtitle': PageDecorationService._clean_text_field(promo_section, 'subtitle', defaults['promo_section']['subtitle']),
            'items': PageDecorationService._normalize_item_list(
                promo_section.get('items'),
                defaults['promo_section']['items'],
                {'badge': '', 'title': '', 'desc': '', 'path': '', 'open_type': 'navigate'},
            ),
        }
        normalized['zone_section'] = {
            'enabled': PageDecorationService._clean_bool(zone_section.get('enabled'), defaults['zone_section']['enabled']),
            'title': PageDecorationService._clean_text_field(zone_section, 'title', defaults['zone_section']['title']),
            'subtitle': PageDecorationService._clean_text_field(zone_section, 'subtitle', defaults['zone_section']['subtitle']),
            'items': PageDecorationService._normalize_zone_items(zone_section.get('items'), defaults['zone_section']['items']),
        }
        normalized['waterfall_section'] = {
            'enabled': PageDecorationService._clean_bool(waterfall_section.get('enabled'), defaults['waterfall_section']['enabled']),
            'title': PageDecorationService._clean_text_field(waterfall_section, 'title', defaults['waterfall_section']['title']),
            'subtitle': PageDecorationService._clean_text_field(waterfall_section, 'subtitle', defaults['waterfall_section']['subtitle']),
            'page_size': max(4, min(int(waterfall_section.get('page_size') or defaults['waterfall_section']['page_size']), 20)),
            'source_keys': [
                item
                for item in PageDecorationService._clean_string_list(
                    waterfall_section.get('source_keys'),
                    defaults['waterfall_section']['source_keys'],
                )
                if item in PageDecorationService.supported_zone_keys()
            ] or defaults['waterfall_section']['source_keys'],
        }
        normalized['quick_section'] = {
            'enabled': PageDecorationService._clean_bool(quick_section.get('enabled'), defaults['quick_section']['enabled']),
            'title': PageDecorationService._clean_text_field(quick_section, 'title', defaults['quick_section']['title']),
            'subtitle': PageDecorationService._clean_text_field(quick_section, 'subtitle', defaults['quick_section']['subtitle']),
            'items': PageDecorationService._normalize_item_list(
                quick_section.get('items'),
                defaults['quick_section']['items'],
                {'title': '', 'desc': '', 'icon_url': '', 'path': '', 'open_type': 'navigate'},
            ),
        }
        return normalized

    @staticmethod
    def _record_to_dict(record: PageDecoration | None, payload: dict, team_id: int | None) -> dict:
        return {
            'id': record.id if record else None,
            'page_key': MOBILE_UNI_HOME_KEY,
            'title': MOBILE_UNI_HOME_TITLE,
            'team_id': team_id,
            'payload': payload,
            'updated_at': iso_datetime(record.updated_at) if record else None,
        }

    @staticmethod
    def _query_record(db: Session, team_id: int | None) -> PageDecoration | None:
        return db.query(PageDecoration).filter(
            PageDecoration.page_key == MOBILE_UNI_HOME_KEY,
            PageDecoration.team_id == team_id,
        ).order_by(PageDecoration.id.desc()).first()

    @staticmethod
    def get_mobile_uni_home_for_admin(db: Session, current_user: User) -> dict:
        team_id = None if AdminScopeService.has_global_scope(current_user) else AdminScopeService.require_team_id(current_user)
        record = PageDecorationService._query_record(db, team_id)
        payload = PageDecorationService.normalize_mobile_uni_home_payload(record.payload if record else None)
        return PageDecorationService._record_to_dict(record, payload, team_id)

    @staticmethod
    def save_mobile_uni_home_for_admin(db: Session, current_user: User, payload: dict) -> dict:
        team_id = None if AdminScopeService.has_global_scope(current_user) else AdminScopeService.require_team_id(current_user)
        record = PageDecorationService._query_record(db, team_id)
        normalized = PageDecorationService.normalize_mobile_uni_home_payload(payload)
        if not record:
            record = PageDecoration(
                page_key=MOBILE_UNI_HOME_KEY,
                title=MOBILE_UNI_HOME_TITLE,
                team_id=team_id,
                payload=normalized,
                created_by_user_id=current_user.id,
                updated_by_user_id=current_user.id,
            )
            db.add(record)
        else:
            record.payload = normalized
            record.updated_by_user_id = current_user.id
        db.commit()
        db.refresh(record)
        return PageDecorationService._record_to_dict(record, normalized, team_id)

    @staticmethod
    def get_mobile_uni_home_for_app(db: Session, current_user: User) -> dict:
        record = None
        team_id = current_user.team_id
        if team_id:
            record = PageDecorationService._query_record(db, team_id)
        if not record:
            record = PageDecorationService._query_record(db, None)
        payload = PageDecorationService.normalize_mobile_uni_home_payload(record.payload if record else None)
        return PageDecorationService._record_to_dict(record, payload, team_id if record and record.team_id is not None else None)
