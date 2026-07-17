from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.admin_role import AdminRole, AdminRolePermission
from app.models.enums import GlobalRole
from app.models.user import AdminUserPermission, User

CONFIGURED_KEY = '__configured__'


PERMISSION_GROUPS = [
    {
        'label': '总览',
        'permissions': [
            {'key': 'dashboard:view', 'label': '首页概览'},
            {'key': 'decoration:view', 'label': '查看移动端装修'},
            {'key': 'decoration:edit', 'label': '编辑移动端装修'},
        ],
    },
    {
        'label': '用户增长',
        'permissions': [
            {'key': 'users:view', 'label': '查看用户'},
            {'key': 'users:manage-commerce', 'label': '管理用户资料与资产'},
            {'key': 'users:status', 'label': '启用或禁用用户'},
            {'key': 'teams:view', 'label': '查看团队'},
            {'key': 'teams:edit', 'label': '管理团队'},
            {'key': 'invites:view', 'label': '邀请裂变'},
        ],
    },
    {
        'label': '商品交易',
        'permissions': [
            {'key': 'products:view', 'label': '查看商品'},
            {'key': 'products:create', 'label': '新增商品'},
            {'key': 'products:edit', 'label': '编辑商品与分类'},
            {'key': 'products:submit-review', 'label': '提交商品审核'},
            {'key': 'products:shelf', 'label': '商品上下架'},
            {'key': 'products:audit', 'label': '审核商品'},
            {'key': 'orders:view', 'label': '查看订单'},
            {'key': 'orders:manage', 'label': '管理订单'},
            {'key': 'shipments:view', 'label': '查看物流'},
            {'key': 'shipments:manage', 'label': '管理物流'},
            {'key': 'region:view', 'label': '区域订单统计'},
            {'key': 'region:audit', 'label': '审核区域代理'},
        ],
    },
    {
        'label': '服务与收益',
        'permissions': [
            {'key': 'local-life:view', 'label': '查看本地生活'},
            {'key': 'local-life:create', 'label': '新增本地生活'},
            {'key': 'local-life:edit', 'label': '编辑本地生活'},
            {'key': 'local-life:verify', 'label': '本地生活核销'},
            {'key': 'commission:view', 'label': '返现管理'},
            {'key': 'withdraws:view', 'label': '查看提现'},
            {'key': 'withdraws:review', 'label': '审核提现'},
            {'key': 'withdraws:pay', 'label': '提现打款'},
            {'key': 'payments:view', 'label': '查看支付流水'},
            {'key': 'assets:view', 'label': '资产中心'},
            {'key': 'suppliers:view', 'label': '供应商管理'},
            {'key': 'suppliers:audit', 'label': '审核供应商资格'},
            {'key': 'earning-rules:view', 'label': '收益规则'},
            {'key': 'earning-rules:edit', 'label': '编辑收益规则'},
        ],
    },
    {
        'label': '系统',
        'permissions': [
            {'key': 'admins:view', 'label': '查看管理员'},
            {'key': 'admins:manage', 'label': '管理管理员'},
            {'key': 'roles:view', 'label': '查看角色'},
            {'key': 'roles:manage', 'label': '管理角色与权限'},
            {'key': 'permissions:manage', 'label': '兼容旧版用户权限管理'},
            {'key': 'profile:view', 'label': '个人中心'},
            {'key': 'profile:edit', 'label': '编辑个人资料'},
            {'key': 'profile:password', 'label': '修改密码'},
        ],
    },
]


DEFAULT_TEAM_ADMIN_PERMISSIONS = {
    'dashboard:view',
    'users:view',
    'users:manage-commerce',
    'teams:view',
    'teams:edit',
    'invites:view',
    'products:view',
    'products:create',
    'products:edit',
    'products:submit-review',
    'products:shelf',
    'orders:view',
    'orders:manage',
    'shipments:view',
    'shipments:manage',
    'region:view',
    'commission:view',
    'withdraws:view',
    'withdraws:review',
    'suppliers:view',
    'assets:view',
    'decoration:view',
    'decoration:edit',
    'local-life:view',
    'local-life:create',
    'local-life:edit',
    'local-life:verify',
    'profile:view',
    'profile:edit',
    'profile:password',
}


class AdminPermissionService:
    @staticmethod
    def all_permission_keys() -> set[str]:
        return {
            item['key']
            for group in PERMISSION_GROUPS
            for item in group['permissions']
        }

    @staticmethod
    def options() -> dict:
        return {'groups': PERMISSION_GROUPS}

    @staticmethod
    def _stored_keys(db: Session, user_id: int) -> set[str]:
        rows = db.query(AdminUserPermission.permission_key).filter(AdminUserPermission.user_id == user_id).all()
        return {row[0] for row in rows}

    @staticmethod
    def effective_permissions(db: Session, user: User) -> list[str]:
        if user.global_role == GlobalRole.SUPER_ADMIN:
            return ['*']
        if user.global_role != GlobalRole.TEAM_ADMIN:
            return []

        if user.admin_role_id:
            role = db.get(AdminRole, user.admin_role_id)
            if not role or role.status != 'ENABLED':
                return []
            rows = db.query(AdminRolePermission.permission_key).filter(
                AdminRolePermission.role_id == role.id,
            ).all()
            return sorted({row[0] for row in rows})

        stored = AdminPermissionService._stored_keys(db, user.id)
        if CONFIGURED_KEY in stored:
            return sorted(stored - {CONFIGURED_KEY})
        return sorted(DEFAULT_TEAM_ADMIN_PERMISSIONS)

    @staticmethod
    def has_permission(db: Session, user: User, permission_key: str | None) -> bool:
        if not permission_key:
            return False
        permissions = AdminPermissionService.effective_permissions(db, user)
        return '*' in permissions or permission_key in permissions

    @staticmethod
    def assert_permission(db: Session, user: User, permission_key: str | None) -> None:
        if not AdminPermissionService.has_permission(db, user, permission_key):
            raise ForbiddenError('No permission')

    @staticmethod
    def list_admins(db: Session) -> list[dict]:
        rows = (
            db.query(User)
            .filter(User.global_role.in_([GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN]))
            .order_by(User.global_role.asc(), User.id.asc())
            .all()
        )
        return [
            {
                'id': item.id,
                'phone': item.phone,
                'nickname': item.nickname,
                'global_role': item.global_role.value,
                'admin_role': {
                    'id': item.admin_role.id,
                    'code': item.admin_role.code,
                    'name': item.admin_role.name,
                    'data_scope': item.admin_role.data_scope,
                    'status': item.admin_role.status,
                } if item.admin_role else None,
                'status': item.status.value,
                'permissions': AdminPermissionService.effective_permissions(db, item),
            }
            for item in rows
        ]

    @staticmethod
    def get_admin_permissions(db: Session, user_id: int) -> dict:
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('Admin not found')
        if user.global_role not in {GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN}:
            raise ConflictError('Only admin accounts can be configured')
        return {
            'id': user.id,
            'phone': user.phone,
            'nickname': user.nickname,
            'global_role': user.global_role.value,
            'admin_role': {
                'id': user.admin_role.id,
                'code': user.admin_role.code,
                'name': user.admin_role.name,
                'data_scope': user.admin_role.data_scope,
                'status': user.admin_role.status,
            } if user.admin_role else None,
            'status': user.status.value,
            'permissions': AdminPermissionService.effective_permissions(db, user),
            'configured': CONFIGURED_KEY in AdminPermissionService._stored_keys(db, user.id),
        }

    @staticmethod
    def save_admin_permissions(db: Session, user_id: int, permission_keys: list[str]) -> dict:
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('Admin not found')
        if user.global_role == GlobalRole.SUPER_ADMIN:
            raise ConflictError('Super admin always has all permissions')
        if user.global_role != GlobalRole.TEAM_ADMIN:
            raise ConflictError('Only team admins can be configured')
        if user.admin_role_id:
            raise ConflictError('This administrator inherits permissions from its role')

        allowed = AdminPermissionService.all_permission_keys()
        cleaned = sorted({item for item in permission_keys if item in allowed})
        db.query(AdminUserPermission).filter(AdminUserPermission.user_id == user_id).delete()
        db.add(AdminUserPermission(user_id=user_id, permission_key=CONFIGURED_KEY))
        for key in cleaned:
            db.add(AdminUserPermission(user_id=user_id, permission_key=key))
        db.commit()
        return AdminPermissionService.get_admin_permissions(db, user_id)

    @staticmethod
    def permission_for_request(method: str, path: str) -> str | None:
        clean_path = path.replace('/api/v1/admin', '', 1)
        method = method.upper()
        if clean_path.startswith('/admins'):
            return 'admins:view' if method == 'GET' else 'admins:manage'
        if clean_path.startswith('/roles'):
            return 'roles:view' if method == 'GET' else 'roles:manage'
        if clean_path.startswith('/permissions'):
            return 'permissions:manage'
        if clean_path.startswith('/profile/password'):
            return 'profile:password'
        if clean_path.startswith('/profile'):
            return 'profile:view' if method == 'GET' else 'profile:edit'
        if clean_path.startswith('/dashboard'):
            return 'dashboard:view'
        if clean_path.startswith('/decorations'):
            return 'decoration:edit' if method in {'POST', 'PUT', 'PATCH', 'DELETE'} else 'decoration:view'
        if clean_path.startswith('/users'):
            if clean_path.endswith('/status'):
                return 'users:status'
            return 'users:view' if method == 'GET' else 'users:manage-commerce'
        if clean_path.startswith('/teams'):
            return 'teams:view' if method == 'GET' else 'teams:edit'
        if clean_path.startswith('/invites'):
            return 'invites:view'
        if clean_path.startswith('/categories'):
            return 'products:edit' if method != 'GET' else 'products:view'
        if clean_path.startswith('/products') or clean_path.startswith('/zones'):
            if clean_path.endswith('/submit-review'):
                return 'products:submit-review'
            if clean_path.endswith('/audit'):
                return 'products:audit'
            if clean_path.endswith('/status') or clean_path.startswith('/products/batch-status'):
                return 'products:shelf'
            if method == 'POST':
                return 'products:create'
            if method in {'PUT', 'PATCH', 'DELETE'}:
                return 'products:edit'
            return 'products:view'
        if clean_path.startswith('/orders'):
            return 'orders:manage' if method in {'POST', 'PUT', 'PATCH', 'DELETE'} else 'orders:view'
        if clean_path.startswith('/commerce/shipments'):
            return 'shipments:manage' if method in {'POST', 'PUT', 'PATCH', 'DELETE'} else 'shipments:view'
        if clean_path.startswith('/commerce/favorites') or clean_path.startswith('/commerce/footprints'):
            return 'users:manage-commerce' if method == 'DELETE' else 'users:view'
        if clean_path.startswith('/region-agents/audit'):
            return 'region:audit'
        if clean_path.startswith('/region-agents') or clean_path.startswith('/region'):
            return 'region:view'
        if clean_path.startswith('/local-life'):
            if method == 'POST':
                return 'local-life:create'
            if method in {'PUT', 'PATCH', 'DELETE'}:
                return 'local-life:edit'
            return 'local-life:view'
        if clean_path.startswith('/commission'):
            return 'commission:view'
        if clean_path.startswith('/withdraws'):
            if clean_path.endswith('/pay'):
                return 'withdraws:pay'
            if method in {'PUT', 'PATCH', 'POST'}:
                return 'withdraws:review'
            return 'withdraws:view'
        if clean_path.startswith('/earning-rules'):
            return 'earning-rules:edit' if method in {'POST', 'PUT', 'PATCH', 'DELETE'} else 'earning-rules:view'
        if clean_path.startswith('/product-qualifications') and clean_path.endswith('/audit'):
            return 'suppliers:audit'
        if clean_path.startswith('/suppliers') or clean_path.startswith('/product-qualification'):
            return 'suppliers:view'
        if clean_path.startswith('/payments'):
            return 'payments:view'
        if clean_path.startswith('/assets'):
            return 'assets:view'
        return None
