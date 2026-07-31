import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

import MainLayout from '@/layout/MainLayout.vue'
import { useUserStore } from '@/stores/user'
import { getToken } from '@/utils/auth'
import { hasPermission, hasRole } from '@/utils/permission'

const ADMIN_PREFIX = '/admin'

function isAdminPrefixed(path) {
  return path === ADMIN_PREFIX || path.startsWith(`${ADMIN_PREFIX}/`)
}

function withAdminPrefix(path) {
  if (isAdminPrefixed(path)) return path
  return `${ADMIN_PREFIX}${path === '/' ? '' : path}`
}

function adminAlias(path) {
  return path === '/dashboard' ? [ADMIN_PREFIX, withAdminPrefix(path)] : withAdminPrefix(path)
}

function adminRoute(route) {
  return {
    ...route,
    alias: route.alias ? [route.alias, adminAlias(route.path)].flat() : adminAlias(route.path)
  }
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    alias: '/admin/login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: '/dashboard', component: () => import('@/views/dashboard/DashboardView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '首页概览', permission: 'dashboard:view' } },
      { path: '/users', component: () => import('@/views/users/UserListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '用户管理', permission: 'users:view' } },
      { path: '/teams', component: () => import('@/views/teams/TeamListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '团队管理', permission: 'teams:view' } },
      { path: '/products', component: () => import('@/views/products/ProductListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '商品管理', permission: 'products:view' } },
      { path: '/categories', component: () => import('@/views/categories/CategoryManageView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '商品分类管理', permission: 'products:view' } },
      { path: '/orders', component: () => import('@/views/orders/OrderListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '订单管理', permission: 'orders:view' } },
      { path: '/region-stats', component: () => import('@/views/region/RegionStatsView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '区域订单奖励', permission: 'region:view' } },
      { path: '/commission', component: () => import('@/views/commission/CommissionView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '佣金明细', permission: 'commission:view' } },
      { path: '/withdraws', component: () => import('@/views/withdraws/WithdrawListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '提现管理', permission: 'withdraws:view' } },
      { path: '/decorations/home', component: () => import('@/views/decorations/DecorationHomeView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '页面装修', permission: 'decoration:view' } },
      { path: '/local-life', component: () => import('@/views/local-life/LocalLifeView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '本地生活', permission: 'local-life:view' } },
      { path: '/invites', component: () => import('@/views/invites/InviteManageView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '邀请裂变', permission: 'invites:view' } },
      { path: '/shipments', component: () => import('@/views/shipments/ShipmentManageView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '快递物流', permission: 'shipments:view' } },
      { path: '/system/earning-rules', component: () => import('@/views/system/EarningRuleView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '收益规则', permission: 'earning-rules:view' } },
      { path: '/system/admins', component: () => import('@/views/system/AccountManageView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '管理员管理', permission: 'admins:view' } },
      { path: '/system/roles', component: () => import('@/views/system/RoleManageView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '角色管理', permission: 'roles:view' } },
      { path: '/system/permissions', redirect: '/system/roles', meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '角色管理', permission: 'roles:view' } },
      { path: '/profile', component: () => import('@/views/profile/ProfileView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '个人中心', permission: 'profile:view' } }
    ].map(adminRoute)
  },
  { path: '/403', alias: '/admin/403', component: () => import('@/views/exception/ForbiddenView.vue'), meta: { public: true } },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/exception/NotFoundView.vue'), meta: { public: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const token = getToken()
  const userStore = useUserStore()
  const isUsingAdminPrefix = isAdminPrefixed(from.path) || isAdminPrefixed(window.location.pathname)

  if ((to.path === '/admin' || to.path === '/admin/') && token) {
    next('/admin/dashboard')
    return
  }

  if (isUsingAdminPrefix && !isAdminPrefixed(to.path) && to.path !== '/') {
    next(withAdminPrefix(to.fullPath))
    return
  }

  if (to.meta.public) {
    if (to.path === '/login' && token) {
      next('/dashboard')
      return
    }
    next()
    return
  }

  if (!token) {
    next('/login')
    return
  }

  if (!userStore.userInfo) {
    try {
      await userStore.fetchMe()
    } catch (error) {
      userStore.logout()
      next('/login')
      return
    }
  }

  if (!userStore.isAdmin) {
    ElMessage.error('普通用户无后台访问权限')
    next('/403')
    return
  }

  if (!hasRole(userStore.role, to.meta.roles || [])) {
    next('/403')
    return
  }

  if (!hasPermission(userStore.role, to.meta.permission, userStore.permissions)) {
    next('/403')
    return
  }

  next()
})

export default router
