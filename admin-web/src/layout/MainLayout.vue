<template>
  <div class="admin-shell">
    <!-- 侧边栏 -->
    <aside class="admin-sidebar">
      <!-- Logo 区域 -->
      <div class="sidebar-brand">
        <div class="brand-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="2" y="2" width="24" height="24" rx="6" fill="url(#logoGradient)"/>
            <path d="M8 14h12M14 8v12" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
            <defs>
              <linearGradient id="logoGradient" x1="2" y1="2" x2="26" y2="26" gradientUnits="userSpaceOnUse">
                <stop stop-color="#D4A853"/>
                <stop offset="1" stop-color="#B8923F"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">Excellent</span>
          <span class="brand-tagline">运营中枢</span>
        </div>
      </div>

      <!-- 角色信息卡片 -->
      <div class="sidebar-role-card">
        <div class="role-card-header">
          <span class="role-badge">{{ roleLabel }}</span>
          <span class="role-dot"></span>
        </div>
        <div class="role-user">{{ userStore.userInfo?.nickname || '未登录' }}</div>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div
          v-for="section in visibleMenuSections"
          :key="section.title"
          class="menu-section"
        >
          <div class="menu-section-title">{{ section.title }}</div>
          <el-menu
            :default-active="activeMenu"
            class="sidebar-menu"
            router
            background-color="transparent"
            text-color="rgba(255,255,255,0.65)"
            active-text-color="#FFFFFF"
            :ellipsis="false"
          >
            <el-menu-item
              v-for="item in section.items"
              :key="item.path"
              :index="routePath(item.path)"
            >
              <el-icon>
                <component :is="getIcon(item.icon)" />
              </el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </el-menu>
        </div>
      </nav>

      <!-- 底部装饰 -->
      <div class="sidebar-footer">
        <div class="footer-decoration"></div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="admin-main">
      <!-- 顶部栏 -->
      <header class="admin-header">
        <div class="header-breadcrumb">
          <span class="breadcrumb-page">{{ route.meta.title || '管理后台' }}</span>
        </div>
        <div class="header-actions">
          <el-button text @click="router.push(routePath('/profile'))">
            <el-icon><User /></el-icon>
            个人中心
          </el-button>
          <el-button type="primary" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
      </header>

      <!-- 页面内容 -->
      <section class="admin-content">
        <router-view />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as icons from '@element-plus/icons-vue'
import { User, SwitchButton } from '@element-plus/icons-vue'

import { menuSections } from '@/router/menu'
import { useUserStore } from '@/stores/user'
import { hasPermission } from '@/utils/permission'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isAdminPrefixed = computed(() => route.path === '/admin' || route.path.startsWith('/admin/'))
const activeMenu = computed(() => {
  const path = route.path.replace(/^\/admin(?=\/|$)/, '') || '/dashboard'
  return routePath(path)
})
const visibleMenuSections = computed(() =>
  menuSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => item.roles.includes(userStore.role) && hasPermission(userStore.role, item.permission, userStore.permissions))
    }))
    .filter((section) => section.items.length)
)
const roleLabel = computed(() => userStore.userInfo?.admin_role?.name || ({
  SUPER_ADMIN: '超级管理员',
  TEAM_ADMIN: '团队管理员'
}[userStore.role] || '普通用户'))

function getIcon(name) {
  return icons[name] || icons.Menu
}

function routePath(path) {
  return isAdminPrefixed.value ? `/admin${path}` : path
}

function handleLogout() {
  userStore.logout()
  router.replace(routePath('/login'))
}
</script>

<style scoped>
@import '@/styles/variables.css';

/* ===== 主布局 ===== */
.admin-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100vh;
  background: var(--bg-base);
}

/* ===== 侧边栏 ===== */
.admin-sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px 16px;
  background: var(--bg-sidebar);
  overflow: hidden;
}

/* Logo 区域 */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  margin-bottom: 16px;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.08);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: #FFFFFF;
  letter-spacing: 0.02em;
}

.brand-tagline {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.1em;
}

/* 角色卡片 */
.sidebar-role-card {
  padding: 14px 16px;
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
}

.role-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--accent);
  background: rgba(212, 168, 83, 0.15);
  border-radius: var(--radius-full);
}

.role-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success-500);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

.role-user {
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.85);
}

/* 导航菜单 */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
}

.menu-section {
  margin-bottom: 14px;
}

.menu-section-title {
  padding: 0 14px 8px;
  font-size: 11px;
  font-weight: var(--font-semibold);
  color: rgba(255, 255, 255, 0.38);
}

.sidebar-menu :deep(.el-menu-item) {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 46px;
  margin-bottom: 4px;
  padding: 0 14px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--duration-fast) var(--ease-out);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #FFFFFF;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(212, 168, 83, 0.25), rgba(212, 168, 83, 0.12));
  color: #FFFFFF;
  font-weight: var(--font-semibold);
}

.sidebar-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--accent);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.sidebar-menu :deep(.el-icon) {
  width: 20px;
  height: 20px;
  margin-right: 2px;
  font-size: 18px;
}

/* 底部装饰 */
.sidebar-footer {
  padding-top: 16px;
}

.footer-decoration {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}

/* ===== 主内容区 ===== */
.admin-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
}

/* 顶部栏 */
.admin-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 16px 28px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-light);
  backdrop-filter: blur(8px);
}

.breadcrumb-page {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-actions .el-button {
  gap: 6px;
}

/* 页面内容 */
.admin-content {
  flex: 1;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* ===== 响应式 ===== */
@media (max-width: 1100px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }

  .admin-sidebar {
    position: relative;
    height: auto;
    padding: 16px;
  }

  .sidebar-nav {
    display: none;
  }

  .admin-content {
    padding: 16px;
  }
}
</style>
