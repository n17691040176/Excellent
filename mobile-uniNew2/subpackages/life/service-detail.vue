<template>
  <view class="service-detail-page">
    <!-- Header -->
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">服务详情</text>
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
      <text class="error-text">服务详情加载失败</text>
      <view class="retry-btn" @click="loadDetail">点击重试</view>
    </view>

    <!-- Content -->
    <template v-else>
      <!-- Hero Card -->
      <view class="hero-card">
        <view class="hero-icon">◇</view>
        <text class="hero-title">{{ detail.title }}</text>
        <text class="hero-desc">{{ detail.desc }}</text>
        <text class="hero-price">¥{{ detail.price }}</text>
      </view>

      <!-- Content Card -->
      <view class="content-card">
        <text class="section-title">服务内容</text>
        <view class="content-list">
          <view v-for="(item, index) in detail.content" :key="index" class="content-item">
            <text class="item-dot">◆</text>
            <text class="item-text">{{ item }}</text>
          </view>
        </view>
      </view>

      <!-- Action Bar -->
      <view class="action-bar">
        <view class="action-price">
          <text class="price-label">¥</text>
          <text class="price-value">{{ detail.price }}</text>
        </view>
        <view class="action-btn" @click="book">立即预约</view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { localLifeApi } from '@/api/modules';
import { trackEvent, trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const id = ref('');
const detail = ref({
  title: '',
  desc: '',
  price: 0,
  content: []
});

const normalize = (res) => ({
  title: res?.name || res?.title || '未命名服务',
  desc: res?.description || res?.desc || '暂无描述',
  price: res?.price ?? res?.sale_price ?? 0,
  content: res?.content || res?.items || ['暂无服务内容']
});

const loadDetail = async () => {
  if (!id.value) return;
  loading.value = true;
  failed.value = false;
  try {
    const res = await localLifeApi.serviceDetail(id.value);
    detail.value = normalize(res || {});
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const book = () => {
  trackEvent('life_service_detail_book', { id: id.value });
  uni.showToast({ title: '已发起预约', icon: 'none' });
};

function goBack() {
  uni.navigateBack();
}

onLoad((query) => {
  id.value = query?.id || '';
  trackPageView('life_service_detail_view', { id: id.value });
  loadDetail();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.service-detail-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 160rpx;
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
  height: 300rpx;
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

/* Hero Card */
.hero-card {
  margin: 120rpx 24rpx 24rpx;
  padding: 48rpx 32rpx;
  background: linear-gradient(135deg, #f97316, #ea580c);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 12rpx 40rpx rgba(249, 115, 22, 0.3);
}

.hero-icon {
  width: 80rpx;
  height: 80rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  color: white;
  margin-bottom: 20rpx;
}

.hero-title {
  font-size: 38rpx;
  font-weight: 700;
  color: white;
  margin-bottom: 8rpx;
  text-align: center;
}

.hero-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 24rpx;
  text-align: center;
}

.hero-price {
  font-size: 56rpx;
  font-weight: 800;
  color: white;
}

/* Content Card */
.content-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 24rpx;
}

.content-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.content-item {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
}

.item-dot {
  font-size: 16rpx;
  color: var(--secondary);
  margin-top: 4rpx;
}

.item-text {
  font-size: 26rpx;
  color: var(--text);
  line-height: 1.5;
}

/* Action Bar */
.action-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24rpx 32rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
  background: var(--card);
  border-top: 1rpx solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(20rpx);
  z-index: 100;
}

.action-price {
  display: flex;
  align-items: baseline;
  gap: 4rpx;
}

.price-label {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--secondary);
}

.price-value {
  font-size: 48rpx;
  font-weight: 800;
  color: var(--secondary);
}

.action-btn {
  padding: 20rpx 48rpx;
  background: linear-gradient(135deg, #f97316, #ea580c);
  color: white;
  font-size: 30rpx;
  font-weight: 700;
  border-radius: 44rpx;
}
</style>
