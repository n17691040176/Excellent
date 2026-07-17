<template>
  <view class="life-list-page">
    <!-- Header -->
    <view class="page-header">
      <text class="header-title">本地生活</text>
    </view>

    <!-- Hero Card -->
    <view class="hero-card">
      <view class="hero-icon">◇</view>
      <text class="hero-title">本地服务大厅</text>
      <text class="hero-desc">根据位置推荐高口碑服务商</text>
    </view>

    <!-- Services List -->
    <view class="services-list">
      <view v-for="item in list" :key="item.id" class="service-card" @click="goDetail(item.id)">
        <view class="service-header">
          <text class="service-title">{{ item.title }}</text>
          <view class="service-tag">{{ item.tag }}</view>
        </view>
        <text class="service-desc">{{ item.desc }}</text>
        <view class="service-footer">
          <text class="service-price">¥{{ item.price }}</text>
          <text class="service-link">查看详情 →</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { trackPageView } from '@/utils/track';

const list = ref([
  { id: 's1001', title: '全屋深度清洁', desc: '上门 3 小时，含专业工具。', price: 199, tag: '热门' },
  { id: 's1002', title: '空调拆洗保养', desc: '支持单台/多台组合服务。', price: 149, tag: '季节' }
]);

const goDetail = (id) => uni.navigateTo({ url: `/subpackages/life/service-detail?id=${id}` });

trackPageView('life_list');
</script>

<style scoped>
@import '@/styles/elegant.css';

.life-list-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 48rpx;
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx 24rpx;
  padding-top: calc(32rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border-light);
}

.header-title {
  font-size: 34rpx;
  font-weight: 700;
  color: var(--text);
}

/* Hero Card */
.hero-card {
  margin: 24rpx;
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
  font-size: 36rpx;
  font-weight: 700;
  color: white;
  margin-bottom: 8rpx;
}

.hero-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

/* Services List */
.services-list {
  padding: 0 24rpx;
}

.service-card {
  padding: 28rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
}

.service-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.service-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
}

.service-tag {
  padding: 6rpx 16rpx;
  background: var(--secondary-bg);
  color: var(--secondary);
  font-size: 20rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.service-desc {
  font-size: 24rpx;
  color: var(--text-muted);
  margin-bottom: 16rpx;
}

.service-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.service-price {
  font-size: 36rpx;
  font-weight: 800;
  color: var(--secondary);
}

.service-link {
  font-size: 24rpx;
  color: var(--secondary);
  font-weight: 600;
}
</style>
