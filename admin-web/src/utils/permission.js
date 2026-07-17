export const ROLE_LABELS = {
  SUPER_ADMIN: '超级管理员',
  TEAM_ADMIN: '团队管理员',
  USER: '普通用户'
}

export const PERMISSION_MATRIX = {
  SUPER_ADMIN: ['*'],
  TEAM_ADMIN: [
    'dashboard:view',
    'users:view',
    'users:manage-commerce',
    'teams:view',
    'teams:edit',
    'products:view',
    'products:create',
    'products:edit',
    'products:submit-review',
    'products:shelf',
    'orders:view',
    'orders:manage',
    'commission:view',
    'withdraws:view',
    'withdraws:review',
    'shipments:view',
    'shipments:manage',
    'region:view',
    'invites:view',
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
    'profile:password'
  ],
  USER: []
}

export function hasRole(userRole, allowRoles = []) {
  if (!allowRoles.length) return true
  return allowRoles.includes(userRole)
}

export function hasPermission(userRole, permission, userPermissions = null) {
  if (!permission) return true
  if (Array.isArray(userPermissions)) {
    return userPermissions.includes('*') || userPermissions.includes(permission)
  }
  const granted = PERMISSION_MATRIX[userRole] || []
  return granted.includes('*') || granted.includes(permission)
}
