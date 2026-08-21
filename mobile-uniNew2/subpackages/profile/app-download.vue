<template>
  <view class="download-page">
    <view class="page-header">
      <view class="header-inner">
        <AppBackButton @click="goBack" />
        <text class="page-title">应用下载</text>
        <view class="header-spacer" />
      </view>
    </view>

    <view class="content-shell">
      <view class="identity-section">
        <image
          class="app-avatar"
          src="/static/apps/aistove-icon.png"
          mode="aspectFit"
          aria-label="Ai物联网安全灶 APP头像"
        />
        <text class="app-name">Ai物联网安全灶</text>
        <text class="app-platform">Android 客户端</text>
      </view>

      <view class="download-section">
        <button
          class="download-button"
          hover-class="download-button-active"
          aria-label="下载 Ai物联网安全灶 Android 版"
          @click="downloadApp"
        >
          <svg class="download-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 3V15" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            <path d="M7 10L12 15L17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M5 21H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          <text>下载 Android 版</text>
        </button>
        <text class="platform-note">仅支持 Android 设备</text>
      </view>

      <view class="info-section">
        <text class="section-title">版本信息</text>
        <view v-for="item in appInfo" :key="item.label" class="info-row">
          <text class="info-label">{{ item.label }}</text>
          <text class="info-value">{{ item.value }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { trackEvent, trackPageView } from '@/utils/track';

const APP_DOWNLOAD_URL = 'https://api.aistove.cn/api/app/releases/latest/download';
const APP_RELEASE_INFO_URL = 'https://api.aistove.cn/api/app/releases/latest';
const DEFAULT_RELEASE = {
  versionName: '1.0.0',
  versionCode: 100,
  fileSize: 76347071
};

const releaseInfo = ref({ ...DEFAULT_RELEASE });
const appInfo = computed(() => [
  { label: '当前版本', value: formatVersion(releaseInfo.value.versionName) },
  { label: '安装包大小', value: formatFileSize(releaseInfo.value.fileSize) },
  { label: '适用平台', value: 'Android' }
]);

function formatVersion(versionName) {
  const version = String(versionName || '').trim();
  if (!version) return '未知';
  return /^v/i.test(version) ? version : `V${version}`;
}

function formatFileSize(fileSize) {
  const bytes = Number(fileSize);
  if (!Number.isFinite(bytes) || bytes <= 0) return '未知';
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function loadReleaseInfo() {
  return new Promise((resolve) => {
    uni.request({
      url: APP_RELEASE_INFO_URL,
      method: 'GET',
      timeout: 10000,
      success: (response) => {
        const payload = typeof response?.data === 'string'
          ? (() => {
              try {
                return JSON.parse(response.data);
              } catch {
                return null;
              }
            })()
          : response?.data;
        const release = payload?.release;
        if (!release?.versionName) {
          resolve(false);
          return;
        }
        releaseInfo.value = { ...DEFAULT_RELEASE, ...release };
        resolve(true);
      },
      fail: (error) => {
        console.warn('[aistove] release metadata unavailable; using fallback', error);
        resolve(false);
      }
    });
  });
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack();
    return;
  }
  uni.switchTab({ url: '/pages/profile/index' });
}

function getPlatform() {
  try {
    return String(uni.getSystemInfoSync?.().platform || '').toLowerCase();
  } catch {
    return '';
  }
}

function getUserAgent() {
  return String(globalThis.navigator?.userAgent || '');
}

function isIosDevice() {
  return getPlatform() === 'ios' || /iPhone|iPad|iPod/i.test(getUserAgent());
}

function copyDownloadUrl(content = '请在手机浏览器中粘贴并打开链接，下载 Ai物联网安全灶。') {
  uni.setClipboardData({
    data: APP_DOWNLOAD_URL,
    success: () => {
      uni.showModal({
        title: '下载链接已复制',
        content,
        showCancel: false
      });
    },
    fail: () => {
      uni.showToast({ title: '复制下载链接失败', icon: 'none' });
    }
  });
}

function downloadApp() {
  trackEvent('aistove_app_download_click', {
    version: releaseInfo.value.versionName || DEFAULT_RELEASE.versionName,
    versionCode: releaseInfo.value.versionCode || DEFAULT_RELEASE.versionCode,
    platform: 'android'
  });

  if (isIosDevice()) {
    uni.showModal({
      title: '暂不支持 iOS',
      content: 'Ai物联网安全灶当前仅提供 Android 版本。',
      showCancel: false
    });
    return;
  }

  if (globalThis.plus?.runtime?.openURL) {
    globalThis.plus.runtime.openURL(APP_DOWNLOAD_URL, () => copyDownloadUrl());
    return;
  }

  if (globalThis.location?.href) {
    if (/MicroMessenger/i.test(getUserAgent())) {
      copyDownloadUrl('请点击右上角，在手机浏览器中打开下载链接。');
      return;
    }
    globalThis.location.href = APP_DOWNLOAD_URL;
    return;
  }

  copyDownloadUrl();
}

onShow(() => {
  trackPageView('aistove_app_download');
  loadReleaseInfo();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.download-page {
  min-height: 100vh;
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
  background: var(--bg);
}

.page-header {
  padding: 20rpx 24rpx;
  padding-top: calc(20rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border-light);
}

.header-inner {
  width: 100%;
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  align-items: center;
}

.page-title {
  flex: 1;
  color: var(--text);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  text-align: center;
}

.header-spacer {
  width: 64rpx;
  height: 64rpx;
  flex: 0 0 64rpx;
}

.content-shell {
  width: 100%;
  max-width: 680px;
  margin: 0 auto;
}

.identity-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 72rpx 32rpx 48rpx;
  background: var(--card);
}

.app-avatar {
  width: 192rpx;
  height: 192rpx;
  flex: 0 0 192rpx;
  border-radius: 44rpx;
  box-shadow: 0 16rpx 36rpx rgba(249, 115, 22, 0.2);
}

.app-name {
  max-width: 100%;
  margin-top: 32rpx;
  color: var(--text);
  font-size: 40rpx;
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
  text-align: center;
  overflow-wrap: anywhere;
}

.app-platform {
  margin-top: 12rpx;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.download-section {
  padding: 0 32rpx 48rpx;
  background: var(--card);
  border-bottom: 1rpx solid var(--border-light);
}

.download-button {
  width: 100%;
  max-width: 600rpx;
  height: 96rpx;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  border: none;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--accent), var(--accent-dark));
  box-shadow: var(--shadow-accent);
  color: white;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  transition: transform var(--duration-fast) var(--ease-out), opacity var(--duration-fast) var(--ease-out);
}

.download-button-active {
  opacity: 0.9;
  transform: scale(0.98);
}

.download-icon {
  width: 40rpx;
  height: 40rpx;
  flex: 0 0 40rpx;
}

.platform-note {
  display: block;
  margin-top: 20rpx;
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-align: center;
}

.info-section {
  margin-top: 16rpx;
  padding: 32rpx;
  background: var(--card);
}

.section-title {
  display: block;
  margin-bottom: 12rpx;
  color: var(--text);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
}

.info-row {
  min-height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  border-bottom: 1rpx solid var(--border-light);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label,
.info-value {
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.info-label {
  color: var(--text-muted);
}

.info-value {
  color: var(--text);
  font-weight: var(--font-semibold);
  text-align: right;
}

@media (prefers-reduced-motion: reduce) {
  .download-button {
    transition: none;
  }
}
</style>
