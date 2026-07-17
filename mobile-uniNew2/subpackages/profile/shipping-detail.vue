<template>
  <view class="detail-page">
    <!-- Header -->
    <view class="page-header">
      <view class="back-btn" @click="goBack">←</view>
      <text class="header-title">快递详情</text>
      <view class="header-spacer" />
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view class="skeleton skeleton-hero" />
      <view class="skeleton skeleton-content" />
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">快递详情加载失败</text>
      <view class="retry-btn" @click="loadData">点击重试</view>
    </view>

    <!-- Content -->
    <template v-else>
      <!-- Head Card -->
      <view class="head-card">
        <view class="head-header">
          <text class="section-title">快递详情</text>
          <view class="head-status" :class="detail.status">
            {{ detail.status_text }}
          </view>
        </view>
        <text class="head-title">{{ detail.title }}</text>
        <text class="head-hint">{{ detail.status_hint }}</text>
        <view class="progress-track">
          <view class="progress-fill" :style="{ width: `${detail.progress_percent || 0}%` }"></view>
        </view>
        <view class="info-grid">
          <view class="info-cell">
            <text class="info-label">承运方式</text>
            <text class="info-value">{{ detail.delivery_mode_text || '--' }}</text>
          </view>
          <view class="info-cell">
            <text class="info-label">承运方</text>
            <text class="info-value">{{ detail.carrier_name || '--' }}</text>
          </view>
          <view class="info-cell">
            <text class="info-label">快递单号</text>
            <text class="info-value">{{ detail.tracking_no || '--' }}</text>
          </view>
          <view class="info-cell">
            <text class="info-label">订单编号</text>
            <text class="info-value">{{ detail.order_no || '--' }}</text>
          </view>
        </view>
        <view class="action-row">
          <view class="action-btn" @click="copyTracking">复制单号</view>
          <view v-if="detail.carrier_phone" class="action-btn" @click="callPhone">联系商家</view>
          <view v-if="detail.can_confirm" class="action-btn primary" :class="{ disabled: confirming }" @click="confirmReceipt">
            {{ confirming ? '确认中...' : '确认收货' }}
          </view>
        </view>
      </view>

      <!-- Status Strip -->
      <view class="status-strip">
        <view class="strip-item">
          <text class="strip-label">下单时间</text>
          <text class="strip-value">{{ formatTime(detail.created_at) }}</text>
        </view>
        <view class="strip-item">
          <text class="strip-label">最近更新</text>
          <text class="strip-value">{{ formatTime(detail.updated_at) }}</text>
        </view>
        <view class="strip-item">
          <text class="strip-label">订单金额</text>
          <text class="strip-value amount">¥{{ money(detail.amount) }}</text>
        </view>
      </view>

      <!-- Timeline -->
      <view class="timeline-card">
        <text class="section-title">物流轨迹</text>
        <view class="timeline-list">
          <view v-for="(item, index) in detail.timeline" :key="`${item.title}-${item.time}`" class="timeline-item">
            <view class="timeline-dot" :class="{ active: item.active, first: index === 0 }" />
            <view class="timeline-content">
              <text class="timeline-title">{{ item.title }}</text>
              <text class="timeline-time">{{ formatTime(item.time) }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Items Card -->
      <view class="items-card">
        <text class="section-title">包裹商品</text>
        <view v-for="item in detail.items" :key="item.id" class="item-row">
          <text class="item-name">{{ item.product_name }}</text>
          <text class="item-meta">数量 x{{ item.quantity }}</text>
          <text class="item-amount">¥{{ money(item.total_amount) }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { commerceApi, orderApi } from '@/api/modules';
import { trackPageView } from '@/utils/track';

const orderId = ref('');
const loading = ref(false);
const failed = ref(false);
const confirming = ref(false);
const detail = ref({
  status: '',
  status_text: '',
  status_hint: '',
  title: '',
  carrier_name: '',
  carrier_phone: '',
  delivery_mode_text: '',
  tracking_no: '',
  order_no: '',
  progress_percent: 0,
  can_confirm: false,
  amount: 0,
  created_at: '',
  updated_at: '',
  timeline: [],
  items: []
});

function money(value) {
  return Number(value || 0).toFixed(2);
}

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

async function loadData() {
  if (!orderId.value) return;
  loading.value = true;
  failed.value = false;
  try {
    detail.value = await commerceApi.shipmentDetail(orderId.value);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function copyTracking() {
  if (!detail.value.tracking_no) return;
  uni.setClipboardData({
    data: detail.value.tracking_no,
    success: () => uni.showToast({ title: '已复制单号', icon: 'none' })
  });
}

function callPhone() {
  if (!detail.value.carrier_phone) return;
  uni.makePhoneCall({ phoneNumber: String(detail.value.carrier_phone) });
}

function confirmReceipt() {
  if (!detail.value.can_confirm || confirming.value) return;
  uni.showModal({
    title: '确认收货',
    content: '确认已经收到这笔订单的包裹吗？',
    success: async ({ confirm }) => {
      if (!confirm) return;
      confirming.value = true;
      try {
        await orderApi.confirm(orderId.value);
        uni.showToast({ title: '已确认收货', icon: 'none' });
        await loadData();
      } finally {
        confirming.value = false;
      }
    }
  });
}

function goBack() {
  uni.navigateBack();
}

onLoad((query) => {
  orderId.value = query?.order_id || '';
  trackPageView('shipping_detail');
  loadData();
});

onShow(() => {
  if (orderId.value) {
    loadData();
  }
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.detail-page {
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
  border-bottom: 1rpx solid var(--border-light);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
}

.back-btn, .header-spacer {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  color: var(--text);
}

.header-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text);
}

/* Loading */
.loading-state {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  margin-top: 120rpx;
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-xl);
}

.skeleton-hero {
  height: 320rpx;
}

.skeleton-content {
  height: 200rpx;
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
  padding: 200rpx 32rpx 48rpx;
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

/* Head Card */
.head-card {
  margin: 120rpx 24rpx 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.head-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
}

.head-status {
  padding: 8rpx 20rpx;
  font-size: 24rpx;
  font-weight: 600;
  border-radius: 20rpx;
}

.head-status.shipping {
  background: var(--primary-bg);
  color: var(--primary);
}

.head-status.delivered {
  background: var(--success-bg);
  color: var(--success);
}

.head-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  display: block;
  margin-bottom: 8rpx;
}

.head-hint {
  font-size: 24rpx;
  color: var(--text-muted);
  display: block;
  margin-bottom: 20rpx;
}

.progress-track {
  height: 12rpx;
  border-radius: 999rpx;
  overflow: hidden;
  background: var(--border-light);
  margin-bottom: 24rpx;
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.info-cell {
  padding: 16rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
}

.info-label {
  font-size: 20rpx;
  color: var(--text-muted);
  display: block;
  margin-bottom: 6rpx;
}

.info-value {
  font-size: 24rpx;
  color: var(--text);
  display: block;
  word-break: break-all;
}

.action-row {
  display: flex;
  gap: 12rpx;
}

.action-btn {
  flex: 1;
  padding: 18rpx;
  font-size: 24rpx;
  font-weight: 600;
  text-align: center;
  border-radius: var(--radius-lg);
  background: var(--bg);
  color: var(--text-muted);
  border: 1rpx solid var(--border-light);
}

.action-btn.primary {
  background: var(--primary);
  color: white;
  border-color: transparent;
}

.action-btn.disabled {
  opacity: 0.6;
}

/* Status Strip */
.status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
  margin: 0 24rpx 24rpx;
}

.strip-item {
  padding: 20rpx 16rpx;
  background: var(--card);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.strip-label {
  font-size: 20rpx;
  color: var(--text-muted);
}

.strip-value {
  font-size: 22rpx;
  color: var(--text);
  font-weight: 600;
}

.strip-value.amount {
  color: var(--secondary);
  font-size: 24rpx;
}

/* Timeline Card */
.timeline-card {
  margin: 0 24rpx 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.timeline-list {
  margin-top: 24rpx;
}

.timeline-item {
  display: flex;
  gap: 16rpx;
  padding-bottom: 24rpx;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: var(--border);
  flex-shrink: 0;
  margin-top: 8rpx;
}

.timeline-dot.active {
  background: var(--primary);
}

.timeline-dot.first {
  background: var(--primary);
  box-shadow: 0 0 0 4rpx var(--primary-bg);
}

.timeline-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.timeline-title {
  font-size: 26rpx;
  color: var(--text);
  line-height: 1.4;
}

.timeline-time {
  font-size: 20rpx;
  color: var(--text-muted);
}

/* Items Card */
.items-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.item-row {
  display: flex;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid var(--border-light);
}

.item-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.item-name {
  flex: 1;
  font-size: 26rpx;
  color: var(--text);
  font-weight: 600;
  min-width: 0;
}

.item-meta {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-right: 24rpx;
}

.item-amount {
  font-size: 26rpx;
  font-weight: 700;
  color: var(--secondary);
}
</style>
