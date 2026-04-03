import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

import MainLayout from '@/layout/MainLayout.vue'
import { useUserStore } from '@/stores/user'
import { getToken } from '@/utils/auth'
import { hasRole } from '@/utils/permission'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: '/dashboard', component: () => import('@/views/dashboard/DashboardView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '首页概览' } },
      { path: '/users', component: () => import('@/views/users/UserListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '用户管理' } },
      { path: '/teams', component: () => import('@/views/teams/TeamListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '团队管理' } },
      { path: '/packages', component: () => import('@/views/packages/PackageListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '套餐管理' } },
      { path: '/commission', component: () => import('@/views/commission/CommissionView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '返现管理' } },
      { path: '/withdraws', component: () => import('@/views/withdraws/WithdrawListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '提现管理' } },
      { path: '/suppliers', component: () => import('@/views/suppliers/SupplierListView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '招商中心' } },
      { path: '/assets', component: () => import('@/views/assets/AssetCenterView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '资产中心' } },
      { path: '/local-life', component: () => import('@/views/local-life/LocalLifeView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '本地生活' } },
      { path: '/system/roles', component: () => import('@/views/system/RoleManageView.vue'), meta: { roles: ['SUPER_ADMIN'], title: '权限管理' } },
      { path: '/system/accounts', component: () => import('@/views/system/AccountManageView.vue'), meta: { roles: ['SUPER_ADMIN'], title: '账号管理' } },
      { path: '/profile', component: () => import('@/views/profile/ProfileView.vue'), meta: { roles: ['SUPER_ADMIN', 'TEAM_ADMIN'], title: '个人中心' } }
    ]
  },
  { path: '/403', component: () => import('@/views/exception/ForbiddenView.vue'), meta: { public: true } },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/exception/NotFoundView.vue'), meta: { public: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const token = getToken()
  const userStore = useUserStore()

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

  next()
})

export default router
