<template>
  <div class="admin-shell page-shell">
    <aside class="admin-sidebar">
      <div class="brand-block">
        <div class="brand-mark">EX</div>
        <div>
          <div class="brand-title">Excellent Admin</div>
          <div class="brand-subtitle">运营后台中枢</div>
        </div>
      </div>

      <div class="brand-ribbon panel-card">
        <div class="ribbon-label">当前角色</div>
        <div class="ribbon-value">{{ roleLabel }}</div>
        <div class="ribbon-meta">{{ userStore.userInfo?.nickname || '未登录' }}</div>
      </div>

      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="activeMenu"
          class="admin-menu"
          router
          background-color="transparent"
          text-color="#f7efe8"
          active-text-color="#ffffff"
        >
          <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path">
            <el-icon><component :is="icons[item.icon] || icons.Menu" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </aside>

    <main class="admin-main">
      <header class="admin-header panel-card">
        <div>
          <div class="header-title">{{ route.meta.title || '管理后台' }}</div>
          <div class="header-subtitle">轻奢视觉风格 · 高效运营工作台</div>
        </div>
        <div class="header-actions">
          <el-button text @click="router.push('/profile')">个人中心</el-button>
          <el-button type="primary" @click="handleLogout">退出登录</el-button>
        </div>
      </header>

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

import { menuItems } from '@/router/menu'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const visibleMenus = computed(() => menuItems.filter((item) => item.roles.includes(userStore.role)))
const roleLabel = computed(() => ({
  SUPER_ADMIN: '超级管理员',
  TEAM_ADMIN: '团队管理员'
}[userStore.role] || '普通用户'))

function handleLogout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.admin-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
}

.admin-sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100vh;
  padding: 24px 18px;
  background:
    radial-gradient(circle at 20% 0%, rgba(226, 185, 128, 0.24), transparent 35%),
    linear-gradient(180deg, #3b2c24, #5a4132 62%, #6e4f3a 100%);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #fff;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 18px;
  font-weight: 800;
  letter-spacing: 0.08em;
  background: linear-gradient(135deg, #e2b980, #f8dfbc);
  color: #5a3a24;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.16);
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(255, 245, 236, 0.74);
}

.brand-ribbon {
  padding: 16px;
  color: #fff7ef;
  background: linear-gradient(135deg, rgba(226, 185, 128, 0.32), rgba(198, 132, 79, 0.38));
  border-color: rgba(255, 255, 255, 0.2);
}

.ribbon-label {
  font-size: 12px;
  opacity: 0.78;
}

.ribbon-value {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 700;
}

.ribbon-meta {
  margin-top: 4px;
  font-size: 13px;
  opacity: 0.84;
}

.menu-scroll {
  flex: 1;
}

.admin-menu {
  border-right: none;
}

.admin-menu :deep(.el-menu-item) {
  margin-bottom: 8px;
  height: 48px;
  border-radius: 14px;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 245, 236, 0.12);
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(198, 132, 79, 0.76), rgba(226, 185, 128, 0.62));
}

.admin-main {
  min-width: 0;
  padding: 24px;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
}

.header-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--brand-deep);
}

.header-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(58, 45, 36, 0.62);
}

.header-actions {
  display: flex;
  gap: 10px;
}

.admin-content {
  margin-top: 22px;
}

@media (max-width: 1100px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }

  .admin-sidebar {
    position: relative;
    height: auto;
  }
}
</style>
