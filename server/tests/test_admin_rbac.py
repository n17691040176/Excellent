from types import SimpleNamespace

from app.models.enums import GlobalRole
from app.services.admin_permission_service import AdminPermissionService
from app.services.admin_scope import AdminScopeService


def test_sensitive_admin_routes_use_distinct_permissions():
    cases = {
        ('PATCH', '/api/v1/admin/users/12/status'): 'users:status',
        ('PATCH', '/api/v1/admin/products/12/submit-review'): 'products:submit-review',
        ('PATCH', '/api/v1/admin/products/12/status'): 'products:shelf',
        ('PATCH', '/api/v1/admin/products/12/audit'): 'products:audit',
        ('POST', '/api/v1/admin/region-agents'): 'region:manage',
        ('PUT', '/api/v1/admin/region-agents/12'): 'region:manage',
        ('DELETE', '/api/v1/admin/region-agents/12'): 'region:manage',
        ('PATCH', '/api/v1/admin/withdraws/12/pay'): 'withdraws:pay',
        ('PATCH', '/api/v1/admin/product-qualifications/12/audit'): 'suppliers:audit',
        ('GET', '/api/v1/admin/payments'): 'payments:view',
        ('GET', '/api/v1/admin/admins'): 'admins:view',
        ('POST', '/api/v1/admin/admins'): 'admins:manage',
        ('GET', '/api/v1/admin/roles'): 'roles:view',
        ('PUT', '/api/v1/admin/roles/12'): 'roles:manage',
    }
    for (method, path), expected in cases.items():
        assert AdminPermissionService.permission_for_request(method, path) == expected


def test_packages_are_intentionally_outside_custom_role_authorization():
    assert AdminPermissionService.permission_for_request('GET', '/api/v1/admin/packages') is None
    assert AdminPermissionService.permission_for_request('POST', '/api/v1/admin/packages') is None


def test_unmapped_permission_fails_closed():
    assert AdminPermissionService.has_permission(None, SimpleNamespace(), None) is False


def test_dynamic_role_controls_data_scope():
    global_admin = SimpleNamespace(
        global_role=GlobalRole.TEAM_ADMIN,
        admin_role=SimpleNamespace(status='ENABLED', data_scope='ALL'),
    )
    team_admin = SimpleNamespace(
        global_role=GlobalRole.TEAM_ADMIN,
        admin_role=SimpleNamespace(status='ENABLED', data_scope='TEAM'),
    )
    root = SimpleNamespace(global_role=GlobalRole.SUPER_ADMIN, admin_role=None)

    assert AdminScopeService.has_global_scope(global_admin) is True
    assert AdminScopeService.has_global_scope(team_admin) is False
    assert AdminScopeService.has_global_scope(root) is True
