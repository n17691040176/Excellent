<template>
  <view class="team-page">
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
            <circle cx="9" cy="7" r="4" stroke="white" stroke-width="2"/>
            <path d="M3 21V19C3 16.79 4.79 15 7 15H11C13.21 15 15 16.79 15 19V21" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <circle cx="17" cy="7" r="3" stroke="white" stroke-width="2"/>
            <path d="M21 21V19C21 17.34 19.66 16 18 16" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </view>
        <text class="page-title">我的团队</text>
        <view class="header-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor"/>
          </svg>
          实时
        </view>
      </view>
    </view>

    <!-- Stats Card -->
    <view class="stats-card">
      <view class="stats-header">
        <text class="stats-icon">◈</text>
        <text class="stats-title">团队数据</text>
      </view>
      <view class="stats-grid">
        <view class="stat-item">
          <text class="stat-value">{{ summary.total }}</text>
          <text class="stat-label">团队成员</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ summary.level1 }}</text>
          <text class="stat-label">一级邀请</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ summary.level2 }}</text>
          <text class="stat-label">二级邀请</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ validCount }}</text>
          <text class="stat-label">有效成员</text>
        </view>
      </view>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view v-for="i in 3" :key="i" class="skeleton-item">
        <view class="skeleton skeleton-avatar" />
        <view class="skeleton-info">
          <view class="skeleton skeleton-name" />
          <view class="skeleton skeleton-phone" />
        </view>
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">团队数据加载失败</text>
      <view class="retry-btn" @click="loadData">点击重试</view>
    </view>

    <!-- Empty -->
    <view v-else-if="!members.length" class="empty-state">
      <text class="empty-icon">◇</text>
      <text class="empty-title">暂无团队成员</text>
      <text class="empty-desc">邀请好友注册后，这里会展示团队成员</text>
    </view>

    <!-- Members List -->
    <view v-else class="members-list">
      <view v-for="m in members" :key="m.id" class="member-card">
        <view class="member-avatar">
          <text class="avatar-text">{{ m.name.charAt(0) }}</text>
        </view>
        <view class="member-info">
          <text class="member-name">{{ m.name }}</text>
          <text class="member-phone">{{ m.phone }}</text>
          <text class="member-time">{{ m.joinedAt }}</text>
        </view>
        <view class="member-badge" :class="m.level === '一级' ? 'level1' : 'level2'">
          {{ m.level }}
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { userApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const summary = ref({
  total: 0,
  level1: 0,
  level2: 0
});
const members = ref([]);

const validCount = computed(() => members.value.filter((item) => item.status === 'valid').length);

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

function maskPhone(value) {
  const raw = String(value || '');
  if (raw.length < 7) return raw || '--';
  return `${raw.slice(0, 3)}****${raw.slice(-4)}`;
}

function toMemberView(item = {}, index = 0) {
  const levelNumber = Number(item.level || 1);
  return {
    id: item.id || `member-${index}`,
    name: item.nickname || `成员 ${index + 1}`,
    phone: maskPhone(item.phone),
    level: levelNumber === 2 ? '二级' : '一级',
    status: item.status || 'valid',
    joinedAt: formatTime(item.created_at || item.joined_at)
  };
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const [summaryRes, recordsRes] = await Promise.allSettled([
      userApi.teamSummary(),
      userApi.inviteRecords({ page: 1, page_size: 50 })
    ]);

    if (summaryRes.status === 'fulfilled') {
      summary.value = {
        total: Number(summaryRes.value?.member_count ?? summaryRes.value?.total_members ?? 0),
        level1: 0,
        level2: 0
      };
    }

    if (recordsRes.status === 'fulfilled') {
      const rows = pickListPayload(recordsRes.value);
      members.value = rows.map(toMemberView);
      summary.value = {
        ...summary.value,
        level1: rows.filter((item) => Number(item.level) === 1).length,
        level2: rows.filter((item) => Number(item.level) === 2).length
      };
    }

    if (summaryRes.status === 'rejected' && recordsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function goBack() {
  uni.navigateBack();
}

onShow(() => {
  trackPageView('team');
  loadData();
});

onPullDownRefresh(async () => {
  await loadData();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.team-page {
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

/* Stats Card */
.stats-card {
  margin: 24rpx;
  padding: 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: var(--radius-xl);
  box-shadow: 0 12rpx 32rpx rgba(16, 185, 129, 0.25);
}

.stats-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 32rpx;
}

.stats-icon {
  font-size: 32rpx;
  color: white;
}

.stats-title {
  font-size: 28rpx;
  font-weight: 600;
  color: white;
}

.stats-grid {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  padding: 24rpx 16rpx;
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
  color: white;
}

.stat-label {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.8);
}

.stat-divider {
  width: 1rpx;
  height: 60rpx;
  background: rgba(255, 255, 255, 0.2);
}

/* Loading State */
.loading-state {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-item {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.skeleton-name {
  height: 32rpx;
  width: 50%;
}

.skeleton-phone {
  height: 24rpx;
  width: 70%;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 32rpx;
}

.error-icon {
  font-size: 80rpx;
  color: var(--error);
  margin-bottom: 24rpx;
}

.error-text {
  font-size: 28rpx;
  color: var(--text-muted);
  margin-bottom: 32rpx;
}

.retry-btn {
  padding: 16rpx 40rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 40rpx;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 32rpx;
}

.empty-icon {
  font-size: 120rpx;
  color: var(--border);
  margin-bottom: 32rpx;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8rpx;
}

.empty-desc {
  font-size: 26rpx;
  color: var(--text-muted);
}

/* Members List */
.members-list {
  padding: 0 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.member-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.member-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-text {
  font-size: 32rpx;
  font-weight: 700;
  color: white;
}

.member-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  min-width: 0;
}

.member-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
}

.member-phone {
  font-size: 22rpx;
  color: var(--text-muted);
}

.member-time {
  font-size: 20rpx;
  color: var(--text-muted);
}

.member-badge {
  padding: 8rpx 20rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 20rpx;
  flex-shrink: 0;
}

.member-badge.level1 {
  background: var(--primary-bg);
  color: var(--primary);
}

.member-badge.level2 {
  background: var(--secondary-bg);
  color: var(--secondary);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background: var(--border-light);
  }

  .team-card,
  .member-card {
    transition: none;
  }

  .team-card:active,
  .member-card:active {
    transform: none;
  }
}
</style>
