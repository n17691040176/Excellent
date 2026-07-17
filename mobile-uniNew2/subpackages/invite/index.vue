<template>
  <view class="invite-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <view class="back-btn" @click="goBack">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="white" stroke-width="2"/>
            <path d="M12 8V16M8 12H16" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </view>
        <text class="page-title">邀请有礼</text>
        <view class="header-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor"/>
          </svg>
          实时
        </view>
      </view>
    </view>

    <!-- Invite Card -->
    <view class="invite-card">
      <view class="card-icon">◈</view>
      <text class="card-title">分享邀请码</text>
      <text class="card-subtitle">好友下单你得奖励</text>

      <view class="code-wrap">
        <text class="code-label">我的邀请码</text>
        <text class="code-value">{{ inviteCode }}</text>
      </view>

      <view class="action-row">
        <button class="action-btn primary" @click="share">立即分享</button>
        <button class="action-btn secondary" @click="copyCode">复制邀请码</button>
      </view>
    </view>

    <!-- Stats Card -->
    <view class="stats-card">
      <view class="card-header">
        <text class="section-title">邀请数据</text>
        <view class="update-badge">
          <text class="badge-icon">◆</text>
          <text class="badge-text">实时</text>
        </view>
      </view>

      <view v-if="loading" class="loading-stats">
        <view class="skeleton skeleton-stat" />
        <view class="skeleton skeleton-stat" />
      </view>

      <view v-else-if="failed" class="error-stats">
        <text class="error-text">数据加载失败</text>
        <view class="retry-text" @click="loadInvite">点击重试</view>
      </view>

      <view v-else class="stats-grid">
        <view class="stat-item">
          <text class="stat-value">{{ stats.total }}</text>
          <text class="stat-label">累计邀请</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ stats.valid }}</text>
          <text class="stat-label">有效转化</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { userApi } from '@/api/modules';
import { pickListPayload, toInviteStats } from '@/utils/adapters';
import { trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const inviteCode = ref('EX2026');
const stats = ref({ total: 0, valid: 0 });

const loadInvite = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const [codeRes, recordsRes] = await Promise.allSettled([
      userApi.inviteCode(),
      userApi.inviteRecords({ page: 1, page_size: 50 })
    ]);

    if (codeRes.status === 'fulfilled') {
      inviteCode.value = codeRes.value?.invite_code || codeRes.value?.code || inviteCode.value;
    }
    if (recordsRes.status === 'fulfilled') {
      stats.value = toInviteStats(pickListPayload(recordsRes.value));
    }

    if (codeRes.status === 'rejected' && recordsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const share = () => uni.showToast({ title: '已生成分享卡片', icon: 'none' });

const copyCode = async () => {
  await uni.setClipboardData({ data: inviteCode.value });
  uni.showToast({ title: '邀请码已复制', icon: 'none' });
};

function goBack() {
  uni.navigateBack();
}

onShow(() => {
  trackPageView('invite');
  loadInvite();
});

onPullDownRefresh(async () => {
  await loadInvite();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.invite-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 48rpx;
}

/* Header */
.page-header {
  padding: 24rpx 32rpx;
  padding-top: calc(24rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.logo-mark {
  width: 56rpx;
  height: 56rpx;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  color: var(--text);
  transition: opacity var(--duration-fast);
}

.back-btn:active {
  opacity: 0.6;
}

.page-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
  flex: 1;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 20rpx;
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
}

/* Invite Card */
.invite-card {
  margin: 24rpx;
  padding: 48rpx 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 12rpx 40rpx rgba(16, 185, 129, 0.25);
}

.card-icon {
  width: 96rpx;
  height: 96rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
  color: white;
  margin-bottom: 24rpx;
}

.card-title {
  font-size: 36rpx;
  font-weight: 700;
  color: white;
  margin-bottom: 8rpx;
}

.card-subtitle {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 40rpx;
}

.code-wrap {
  width: 100%;
  padding: 24rpx;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 32rpx;
}

.code-label {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.7);
}

.code-value {
  font-size: 40rpx;
  font-weight: 800;
  color: white;
  letter-spacing: 4rpx;
}

.action-row {
  display: flex;
  gap: 16rpx;
  width: 100%;
}

.action-btn {
  flex: 1;
  height: 88rpx;
  border-radius: 44rpx;
  font-size: 28rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
}

.action-btn.primary {
  background: white;
  color: var(--primary);
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2rpx solid rgba(255, 255, 255, 0.5);
}

/* Stats Card */
.stats-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
}

.update-badge {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  background: var(--primary-bg);
  border-radius: 20rpx;
}

.badge-icon {
  font-size: 16rpx;
  color: var(--primary);
}

.badge-text {
  font-size: 20rpx;
  color: var(--primary);
  font-weight: 600;
}

.stats-grid {
  display: flex;
  align-items: center;
  background: var(--bg);
  border-radius: var(--radius-lg);
  padding: 24rpx;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.stat-value {
  font-size: 40rpx;
  font-weight: 800;
  color: var(--text);
}

.stat-label {
  font-size: 22rpx;
  color: var(--text-muted);
}

.stat-divider {
  width: 1rpx;
  height: 60rpx;
  background: var(--border-light);
}

/* Loading */
.loading-stats {
  display: flex;
  gap: 16rpx;
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-stat {
  flex: 1;
  height: 100rpx;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error */
.error-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32rpx;
}

.error-text {
  font-size: 26rpx;
  color: var(--text-muted);
  margin-bottom: 16rpx;
}

.retry-text {
  font-size: 24rpx;
  color: var(--primary);
  font-weight: 600;
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background: var(--border-light);
  }
}
</style>
