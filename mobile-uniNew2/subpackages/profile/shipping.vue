<template>
  <view class="shipping-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <AppBackButton @click="goBack" />
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="3" width="15" height="13" rx="2" stroke="white" stroke-width="2"/>
            <path d="M16 8H20L23 11V21C23 21.5523 22.5523 22 22 22H2C1.44772 22 1 21.5523 1 21V11L4 8H8" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </view>
        <text class="page-title">快递服务</text>
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
      <view class="summary-header">
        <view class="summary-info">
          <text class="summary-title">快递服务</text>
          <text class="summary-subtitle">统一查看运输进度</text>
        </view>
        <view class="summary-badge">实时</view>
      </view>
      <view class="stats-grid">
        <view class="stat-item">
          <text class="stat-value">{{ items.length }}</text>
          <text class="stat-label">全部包裹</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ shippingCount }}</text>
          <text class="stat-label">运输中</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ deliveredCount }}</text>
          <text class="stat-label">已签收</text>
        </view>
      </view>
    </view>

    <!-- Status Tabs -->
    <view class="tabs-wrap">
      <view
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-item"
        :class="{ active: activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </view>
    </view>

    <!-- Loading -->
    <view v-if="loading && !items.length" class="loading-state">
      <view v-for="i in 3" :key="i" class="skeleton-item">
        <view class="skeleton skeleton-content" />
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed && !items.length" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">快递加载失败</text>
      <view class="retry-btn" @click="loadData">点击重试</view>
    </view>

    <!-- Empty -->
    <view v-else-if="!filteredItems.length" class="empty-state">
      <text class="empty-icon">◇</text>
      <text class="empty-title">暂无快递包裹</text>
      <text class="empty-desc">已支付且需要发货的订单</text>
    </view>

    <!-- Shipments List -->
    <view v-else class="shipments-list">
      <view v-for="item in filteredItems" :key="item.order_id" class="ship-card" @click="goDetail(item.order_id)">
        <view class="ship-header">
          <text class="ship-company">{{ item.carrier_name }}</text>
          <view class="ship-status" :class="item.status">
            {{ item.status_text }}
          </view>
        </view>
        <text class="ship-title">{{ item.title }}</text>
        <text class="ship-hint">{{ item.status_hint }}</text>
        <view class="progress-track">
          <view class="progress-fill" :style="{ width: `${item.progress_percent || 0}%` }"></view>
        </view>
        <text class="ship-message">{{ item.latest_message }}</text>
        <view class="ship-meta">
          <text>单号 {{ item.tracking_no }}</text>
          <text>{{ item.delivery_mode_text }}</text>
          <text>更新 {{ formatTime(item.updated_at) }}</text>
        </view>
        <view class="ship-actions">
          <view class="action-btn" @click.stop="copyTracking(item.tracking_no)">复制</view>
          <view v-if="item.carrier_phone" class="action-btn" @click.stop="callPhone(item.carrier_phone)">联系</view>
          <view class="action-btn primary">查看详情</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { trackPageView } from '@/utils/track';

const tabs = [
  { label: '全部', value: 'all' },
  { label: '运输中', value: 'shipping' },
  { label: '已签收', value: 'delivered' }
];

const loading = ref(false);
const failed = ref(false);
const items = ref([]);
const activeTab = ref('all');

const shippingCount = computed(() => items.value.filter((item) => item.status === 'shipping').length);
const deliveredCount = computed(() => items.value.filter((item) => item.status === 'delivered').length);

const filteredItems = computed(() => {
  if (activeTab.value === 'all') return items.value;
  return items.value.filter((item) => item.status === activeTab.value);
});

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const res = await commerceApi.shipments();
    items.value = pickListPayload(res);
    await commerceApi.markViewed('shipping');
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function copyTracking(trackingNo) {
  if (!trackingNo) return;
  uni.setClipboardData({
    data: trackingNo,
    success: () => uni.showToast({ title: '已复制单号', icon: 'none' })
  });
}

function callPhone(phone) {
  if (!phone) return;
  uni.makePhoneCall({ phoneNumber: String(phone) });
}

function goBack() {
  uni.navigateBack();
}

function goDetail(orderId) {
  uni.navigateTo({ url: `/subpackages/profile/shipping-detail?order_id=${orderId}` });
}

onShow(() => {
  trackPageView('shipping');
  loadData();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.shipping-page {
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
  padding: 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: var(--radius-xl);
  box-shadow: 0 12rpx 32rpx rgba(16, 185, 129, 0.25);
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.summary-title {
  font-size: 30rpx;
  font-weight: 700;
  color: white;
  display: block;
}

.summary-subtitle {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.8);
  display: block;
  margin-top: 4rpx;
}

.summary-badge {
  padding: 8rpx 16rpx;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 20rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.stats-grid {
  display: flex;
  align-items: center;
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
  font-size: 36rpx;
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

/* Tabs */
.tabs-wrap {
  display: flex;
  gap: 16rpx;
  padding: 0 24rpx;
  margin-bottom: 24rpx;
}

.tab-item {
  padding: 12rpx 24rpx;
  background: var(--card);
  color: var(--text-muted);
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 24rpx;
  border: 1rpx solid var(--border-light);
}

.tab-item.active {
  background: var(--primary);
  color: white;
  border-color: transparent;
}

/* Loading */
.loading-state {
  padding: 0 24rpx;
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
  height: 240rpx;
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

/* Shipments List */
.shipments-list {
  padding: 0 24rpx;
}

.ship-card {
  padding: 28rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
}

.ship-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.ship-company {
  font-size: 22rpx;
  color: var(--text-muted);
}

.ship-status {
  padding: 6rpx 16rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.ship-status.shipping {
  background: var(--primary-bg);
  color: var(--primary);
}

.ship-status.delivered {
  background: var(--success-bg);
  color: var(--success);
}

.ship-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  display: block;
  margin-bottom: 8rpx;
}

.ship-hint {
  font-size: 22rpx;
  color: var(--text-muted);
  display: block;
  margin-bottom: 16rpx;
}

.progress-track {
  height: 10rpx;
  border-radius: 999rpx;
  overflow: hidden;
  background: var(--border-light);
  margin-bottom: 16rpx;
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
}

.ship-message {
  font-size: 22rpx;
  color: var(--text-muted);
  display: block;
  margin-bottom: 16rpx;
}

.ship-meta {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  margin-bottom: 16rpx;
}

.ship-meta text {
  font-size: 20rpx;
  color: var(--text-muted);
}

.ship-actions {
  display: flex;
  gap: 12rpx;
}

.action-btn {
  flex: 1;
  padding: 16rpx;
  font-size: 22rpx;
  font-weight: 600;
  text-align: center;
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--text-muted);
  border: 1rpx solid var(--border-light);
}

.action-btn.primary {
  background: var(--primary);
  color: white;
  border-color: transparent;
}
</style>
