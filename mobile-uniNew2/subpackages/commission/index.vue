<template>
  <view class="commission-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <AppBackButton @click="goBack" />
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="white" stroke-width="2"/>
            <path d="M12 6v12M6 12h12" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </view>
        <text class="page-title">佣金中心</text>
        <view class="header-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor"/>
          </svg>
          实时
        </view>
      </view>
    </view>

    <!-- Summary Card -->
    <view class="summary-card">
      <view class="card-icon">◆</view>
      <text class="card-subtitle">收益趋势与结算进度实时同步</text>

      <view class="balance-wrap">
        <text class="balance-label">可提现金额</text>
        <text class="balance-value">¥{{ withdrawable }}</text>
      </view>

      <button class="withdraw-btn" @click="withdraw">立即提现</button>

      <view class="stats-strip">
        <view class="stat-item">
          <text class="stat-value">{{ list.length }}</text>
          <text class="stat-label">收益记录</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ settledCount }}</text>
          <text class="stat-label">已结算</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ pendingCount }}</text>
          <text class="stat-label">待结算</text>
        </view>
      </view>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view v-for="i in 3" :key="i" class="skeleton-item">
        <view class="skeleton skeleton-content" />
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">佣金记录加载失败</text>
      <view class="retry-btn" @click="loadCommission">点击重试</view>
    </view>

    <!-- Empty -->
    <view v-else-if="!list.length" class="empty-state">
      <text class="empty-icon">◇</text>
      <text class="empty-title">暂无佣金记录</text>
      <text class="empty-desc">产生收益后会同步展示结算进度</text>
    </view>

    <!-- Records -->
    <view v-else class="records-list">
      <text class="section-title">收益记录</text>
      <view v-for="item in list" :key="item.id" class="record-card">
        <view class="record-header">
          <view class="record-info">
            <text class="record-name">{{ item.name }}</text>
            <text class="record-time">{{ item.time }}</text>
          </view>
          <view class="record-status" :class="item.status === '已结算' ? 'settled' : 'pending'">
            {{ item.status }}
          </view>
        </view>
        <view class="record-footer">
          <text class="record-desc">{{ item.desc || '收益入账记录' }}</text>
          <text class="record-amount">+¥{{ item.amount }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { commissionApi } from '@/api/modules';
import { pickListPayload, toCommissionFlows } from '@/utils/adapters';
import { trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const withdrawable = ref('0.00');
const list = ref([]);

const settledCount = computed(() => list.value.filter((item) => item.status === '已结算').length);
const pendingCount = computed(() => list.value.filter((item) => item.status !== '已结算').length);

const loadCommission = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const [summaryRes, flowsRes] = await Promise.allSettled([
      commissionApi.summary(),
      commissionApi.flows({ page: 1, page_size: 20 })
    ]);

    if (summaryRes.status === 'fulfilled') {
      withdrawable.value = summaryRes.value?.withdrawable_amount ?? summaryRes.value?.available_amount ?? '0.00';
    }
    if (flowsRes.status === 'fulfilled') {
      list.value = toCommissionFlows(pickListPayload(flowsRes.value));
    }
    if (summaryRes.status === 'rejected' && flowsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const withdraw = () => {
  uni.navigateTo({ url: '/subpackages/commission/withdraw' });
};

function goBack() {
  uni.navigateBack();
}

onShow(() => {
  trackPageView('commission');
  loadCommission();
});

onPullDownRefresh(async () => {
  await loadCommission();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.commission-page {
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

/* Summary Card */
.summary-card {
  margin: 24rpx;
  padding: 40rpx 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 12rpx 40rpx rgba(16, 185, 129, 0.25);
}

.card-icon {
  width: 80rpx;
  height: 80rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  color: white;
  margin-bottom: 16rpx;
}

.card-subtitle {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 32rpx;
}

.balance-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  margin-bottom: 24rpx;
}

.balance-label {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}

.balance-value {
  font-size: 56rpx;
  font-weight: 800;
  color: white;
}

.withdraw-btn {
  width: 100%;
  height: 88rpx;
  background: white;
  border-radius: 44rpx;
  color: var(--primary);
  font-size: 30rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  margin-bottom: 32rpx;
}

.stats-strip {
  display: flex;
  align-items: center;
  width: 100%;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  padding: 20rpx;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
}

.stat-value {
  font-size: 32rpx;
  font-weight: 800;
  color: white;
}

.stat-label {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.8);
}

.stat-divider {
  width: 1rpx;
  height: 48rpx;
  background: rgba(255, 255, 255, 0.2);
}

/* Loading */
.loading-state {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-item {
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

.skeleton-content {
  height: 120rpx;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error */
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

/* Empty */
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

/* Records */
.records-list {
  padding: 0 24rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 20rpx;
}

.record-card {
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
}

.record-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.record-info {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.record-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
}

.record-time {
  font-size: 22rpx;
  color: var(--text-muted);
}

.record-status {
  padding: 6rpx 16rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 20rpx;
}

.record-status.settled {
  background: var(--primary-bg);
  color: var(--primary);
}

.record-status.pending {
  background: var(--secondary-bg);
  color: var(--secondary);
}

.record-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.record-desc {
  font-size: 22rpx;
  color: var(--text-muted);
}

.record-amount {
  font-size: 32rpx;
  font-weight: 800;
  color: var(--secondary);
}
</style>
