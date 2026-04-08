import { createRouter, createWebHashHistory } from 'vue-router'

import { getToken } from '@/utils/auth'

const routes = [
  { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true, title: '登录注册' } },
  { path: '/', redirect: '/home' },
  { path: '/home', component: () => import('@/views/HomeView.vue'), meta: { title: '首页' } },
  { path: '/categories', component: () => import('@/views/CategoryView.vue'), meta: { title: '分类' } },
  { path: '/packages', component: () => import('@/views/PackageListView.vue'), meta: { title: '套餐中心' } },
  { path: '/packages/:id', component: () => import('@/views/PackageDetailView.vue'), meta: { title: '套餐详情' } },
  { path: '/products/:id', component: () => import('@/views/ProductDetailView.vue'), meta: { title: '商品详情' } },
  { path: '/life', component: () => import('@/views/LocalLifeView.vue'), meta: { title: '本地生活' } },
  { path: '/life/orders', component: () => import('@/views/LocalLifeOrdersView.vue'), meta: { title: '本地生活订单' } },
  { path: '/life/services/:id', component: () => import('@/views/LocalLifeServiceDetailView.vue'), meta: { title: '服务详情' } },
  { path: '/team', component: () => import('@/views/TeamView.vue'), meta: { title: '我的团队' } },
  { path: '/invite', component: () => import('@/views/InviteView.vue'), meta: { title: '邀请好友' } },
  { path: '/commission', component: () => import('@/views/CommissionView.vue'), meta: { title: '佣金中心' } },
  { path: '/assets', component: () => import('@/views/AssetCenterView.vue'), meta: { title: '资产中心' } },
  { path: '/addresses', component: () => import('@/views/AddressView.vue'), meta: { title: '地址管理' } },
  { path: '/orders', component: () => import('@/views/OrderView.vue'), meta: { title: '我的订单' } },
  { path: '/orders/:id', component: () => import('@/views/OrderDetailView.vue'), meta: { title: '订单详情' } },
  { path: '/settings', component: () => import('@/views/SettingsView.vue'), meta: { title: '账号设置' } },
  { path: '/profile', component: () => import('@/views/ProfileView.vue'), meta: { title: '个人中心' } }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta?.title ? `${to.meta.title} - Excellent Mall` : 'Excellent Mall'
  if (to.meta.public) {
    if (to.path === '/login' && getToken()) {
      next('/home')
      return
    }
    next()
    return
  }
  if (!getToken()) {
    next('/login')
    return
  }
  next()
})

export default router
