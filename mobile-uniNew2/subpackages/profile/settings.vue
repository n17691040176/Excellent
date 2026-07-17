<template>
  <view class="settings-page">
    <!-- Header -->
    <view class="page-header">
      <view class="back-btn" @click="goBack">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </view>
      <text class="header-title">账号设置</text>
      <view class="header-spacer" />
    </view>

    <!-- Account Section -->
    <view class="section-card">
      <text class="section-title">账户管理</text>
      <view class="menu-list">
        <view
          v-for="item in accountMenu"
          :key="item.action"
          class="menu-item"
          @click="handleMenu(item)"
        >
          <view class="menu-left">
            <view class="menu-icon" :style="{ background: item.bgColor }">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" v-html="item.svgPath" />
            </view>
            <text class="menu-title">{{ item.title }}</text>
          </view>
          <svg class="menu-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
      </view>
    </view>

    <!-- Environment Card -->
    <view class="section-card">
      <view class="section-header">
        <text class="section-title">环境配置</text>
        <view class="env-badge" :class="currentEnvBadge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="10"/>
          </svg>
          {{ currentEnvTag }}
        </view>
      </view>
      <view class="env-list">
        <view
          v-for="env in envOptions"
          :key="env.value"
          class="env-item"
          :class="{ active: currentEnv === env.value }"
          @click="applyEnv(env.value)"
        >
          <view class="env-info">
            <text class="env-name">{{ env.label }}</text>
            <text class="env-url">{{ env.apiUrl }}</text>
          </view>
          <view v-if="currentEnv === env.value" class="env-check">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </view>
        </view>
      </view>
    </view>

    <!-- Logout -->
    <view class="logout-section">
      <view class="logout-btn" @click="logout">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <polyline points="16 17 21 12 16 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="21" y1="12" x2="9" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        退出登录
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { clearAuth } from '@/utils/auth';
import {
  APP_ENV,
  clearApiBaseUrl,
  clearAppEnv,
  clearInviteWebBaseUrl,
  getAppEnv,
  setApiBaseUrl,
  setAppEnv,
  setInviteWebBaseUrl
} from '@/config';

const accountMenu = [
  {
    title: '个人资料',
    action: 'profile',
    bgColor: 'rgba(5, 150, 105, 0.1)',
    svgPath: '<path d="M20 21V19a2 2 0 00-2-2H6a2 2 0 00-2 2v2" stroke="#059669" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="7" r="4" stroke="#059669" stroke-width="2"/>'
  },
  {
    title: '账号安全',
    action: 'security',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    svgPath: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  },
  {
    title: '隐私设置',
    action: 'privacy',
    bgColor: 'rgba(139, 92, 246, 0.1)',
    svgPath: '<rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke="#8B5CF6" stroke-width="2"/><path d="M7 11V7a5 5 0 0110 0v4" stroke="#8B5CF6" stroke-width="2" stroke-linecap="round"/>'
  }
];

const envOptions = [
  {
    value: APP_ENV.LOCAL,
    label: '本地环境',
    tag: 'local',
    apiUrl: 'http://127.0.0.1:8000',
    badgeClass: 'badge-local'
  },
  {
    value: APP_ENV.DEV,
    label: '开发服务器',
    tag: 'dev',
    apiUrl: 'http://156.238.241.213:8000',
    badgeClass: 'badge-dev'
  },
  {
    value: APP_ENV.PROD,
    label: '部署服务器',
    tag: 'prod',
    apiUrl: '待配置',
    badgeClass: 'badge-prod'
  }
];

const currentEnv = ref(getAppEnv());
const currentEnvTag = computed(() => {
  const matched = envOptions.find((item) => item.value === currentEnv.value);
  return matched ? matched.tag : currentEnv.value;
});
const currentEnvBadge = computed(() => {
  const matched = envOptions.find((item) => item.value === currentEnv.value);
  return matched ? matched.badgeClass : 'badge-local';
});

const envRuntimeConfig = {
  [APP_ENV.LOCAL]: {
    apiUrl: 'http://127.0.0.1:8000',
    inviteUrl: 'http://127.0.0.1:5174'
  },
  [APP_ENV.DEV]: {
    apiUrl: 'http://156.238.241.213:8000',
    inviteUrl: 'http://156.238.241.213:5174'
  },
  [APP_ENV.PROD]: {
    apiUrl: '',
    inviteUrl: ''
  }
};

function goBack() {
  uni.navigateBack();
}

function handleMenu(item) {
  uni.showToast({ title: `${item.title}即将开放`, icon: 'none' });
}

function applyEnv(env) {
  if (env === currentEnv.value) {
    uni.showToast({ title: `已是${envOptions.find(e => e.value === env).label}`, icon: 'none' });
    return;
  }

  if (env === APP_ENV.PROD) {
    clearAppEnv();
    clearApiBaseUrl();
    clearInviteWebBaseUrl();
  } else {
    setAppEnv(env);
    const runtimeConfig = envRuntimeConfig[env];
    setApiBaseUrl(runtimeConfig?.apiUrl || '');
    setInviteWebBaseUrl(runtimeConfig?.inviteUrl || '');
  }

  currentEnv.value = getAppEnv();
  uni.showToast({ title: `已切换到${envOptions.find(e => e.value === env).label}`, icon: 'none' });
  setTimeout(() => {
    const pages = getCurrentPages();
    const currentPage = pages[pages.length - 1];
    if (!currentPage) {
      uni.reLaunch({ url: '/pages/profile/index' });
      return;
    }
    const route = `/${currentPage.route}`;
    uni.reLaunch({ url: route });
  }, 300);
}

function logout() {
  uni.showModal({
    title: '退出登录',
    content: '确定要退出当前账号吗？',
    success: ({ confirm }) => {
      if (confirm) {
        clearAuth();
        uni.reLaunch({ url: '/pages/login/index' });
      }
    }
  });
}
</script>

<style scoped>
@import '@/styles/common.css';

.settings-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 48rpx;
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  padding-top: calc(24rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-fixed);
}

.back-btn, .header-spacer {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text);
  transition: all var(--duration-fast) var(--ease-out);
}

.back-btn:active {
  opacity: 0.6;
}

.header-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
}

/* Section Card */
.section-card {
  margin: 24rpx;
  margin-top: calc(24rpx + 112rpx);
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
  margin-bottom: 24rpx;
}

.section-header .section-title {
  margin-bottom: 0;
}

/* Menu List */
.menu-list {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--border);
  transition: all var(--duration-fast) var(--ease-out);
}

.menu-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.menu-item:active {
  opacity: 0.7;
}

.menu-left {
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.menu-icon {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
}

.menu-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text);
}

.menu-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* Env Badge */
.env-badge {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  border-radius: var(--radius-full);
  font-size: 20rpx;
  font-weight: var(--font-bold);
  text-transform: uppercase;
}

.badge-local {
  background: rgba(5, 150, 105, 0.1);
  color: var(--primary);
}

.badge-dev {
  background: rgba(59, 130, 246, 0.1);
  color: #3B82F6;
}

.badge-prod {
  background: rgba(139, 92, 246, 0.1);
  color: #8B5CF6;
}

/* Env List */
.env-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.env-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  border: 2rpx solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
}

.env-item:active {
  opacity: 0.8;
}

.env-item.active {
  border-color: var(--primary);
  background: rgba(5, 150, 105, 0.05);
}

.env-info {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.env-name {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text);
}

.env-url {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.env-check {
  width: 40rpx;
  height: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary);
  color: white;
  border-radius: 50%;
}

/* Logout */
.logout-section {
  margin: 48rpx 24rpx 0;
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: 28rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--danger);
  transition: all var(--duration-fast) var(--ease-out);
}

.logout-btn:active {
  background: rgba(239, 68, 68, 0.05);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .back-btn,
  .menu-item,
  .env-item,
  .logout-btn {
    transition: none;
  }
}
</style>
