<template>
  <view class="footprints-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <AppBackButton @click="goBack" />
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="white" stroke-width="2"/>
            <path d="M12 6V12L16 14" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </view>
        <text class="page-title">我的足迹</text>
        <view class="header-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor"/>
          </svg>
          实时
        </view>
      </view>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view v-for="i in 3" :key="i" class="skeleton-item">
        <view class="skeleton skeleton-image" />
        <view class="skeleton-info">
          <view class="skeleton skeleton-title" />
          <view class="skeleton skeleton-price" />
        </view>
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">足迹加载失败</text>
      <view class="retry-btn" @click="loadData">点击重试</view>
    </view>

    <!-- Empty -->
    <view v-else-if="!items.length" class="empty-state">
      <text class="empty-icon">◇</text>
      <text class="empty-title">最近还没有浏览记录</text>
      <text class="empty-desc">打开商品详情后，会自动记录你的浏览足迹</text>
      <view class="empty-btn" @click="goShopping">去逛逛</view>
    </view>

    <!-- List -->
    <view v-else class="footprints-list">
      <view
        v-for="item in items"
        :key="item.product_id"
        class="footprint-item"
      >
        <view class="item-image" @click="goDetail(item.product_id)">
          <image v-if="item.image" class="image" :src="item.image" mode="aspectFill" />
          <view v-else class="image-placeholder" />
          <view class="view-badge">{{ item.view_count || 1 }}次</view>
        </view>
        <view class="item-content">
          <text class="item-title" @click="goDetail(item.product_id)">{{ item.title }}</text>
          <text class="item-desc">{{ item.desc || '最近浏览商品' }}</text>
          <text class="item-time">最近浏览 {{ formatTime(item.last_viewed_at) }}</text>
          <view class="item-footer">
            <text class="item-price">¥{{ money(item.price || item.sale_price) }}</text>
            <view class="item-actions">
              <view class="action-btn remove" @click="removeItem(item.product_id)">删除</view>
              <view class="action-btn view" @click="goDetail(item.product_id)">继续看</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { trackEvent, trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const items = ref([]);

function money(value) {
  return Number(value || 0).toFixed(2);
}

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const res = await commerceApi.footprints({ page: 1, page_size: 50 });
    items.value = pickListPayload(res);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

async function removeItem(productId) {
  await commerceApi.removeFootprint(productId);
  items.value = items.value.filter((item) => item.product_id !== productId);
  trackEvent('footprints_remove', { product_id: productId });
  uni.showToast({ title: '已删除', icon: 'none' });
}

function goDetail(productId) {
  trackEvent('footprints_view', { product_id: productId });
  uni.navigateTo({ url: `/subpackages/package/detail?id=${productId}` });
}

function goBack() {
  uni.navigateBack();
}

function goShopping() {
  uni.switchTab({ url: '/pages/packages/list' });
}

onShow(() => {
  trackPageView('footprints');
  loadData();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.footprints-page {
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

/* Loading State */
.loading-state {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.skeleton-item {
  display: flex;
  gap: 24rpx;
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

.skeleton-image {
  width: 180rpx;
  height: 180rpx;
  flex-shrink: 0;
  border-radius: var(--radius-md);
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-title {
  height: 40rpx;
  width: 80%;
}

.skeleton-price {
  height: 36rpx;
  width: 40%;
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
  margin-bottom: 48rpx;
}

.empty-btn {
  padding: 16rpx 48rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 28rpx;
  font-weight: 600;
  border-radius: 40rpx;
}

/* Footprints List */
.footprints-list {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.footprint-item {
  display: flex;
  gap: 24rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.item-image {
  position: relative;
  width: 180rpx;
  height: 180rpx;
  border-radius: var(--radius-lg);
  overflow: hidden;
  flex-shrink: 0;
}

.image {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--primary-bg), var(--primary));
}

.view-badge {
  position: absolute;
  left: 12rpx;
  top: 12rpx;
  padding: 6rpx 12rpx;
  background: rgba(16, 185, 129, 0.9);
  color: white;
  font-size: 18rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.item-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8rpx;
}

.item-desc {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-bottom: 8rpx;
}

.item-time {
  font-size: 20rpx;
  color: var(--text-muted);
  margin-bottom: auto;
}

.item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16rpx;
}

.item-price {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--secondary);
}

.item-actions {
  display: flex;
  gap: 12rpx;
}

.action-btn {
  padding: 10rpx 20rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 20rpx;
}

.action-btn.remove {
  background: var(--bg);
  color: var(--text-muted);
  border: 1rpx solid var(--border);
}

.action-btn.view {
  background: var(--primary);
  color: white;
}
</style>
