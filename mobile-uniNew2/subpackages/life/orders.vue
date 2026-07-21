<template>
  <view class="life-orders-page">
    <!-- Header -->
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">生活订单</text>
      <view class="header-spacer" />
    </view>

    <!-- Loading -->
    <view v-if="loading && !list.length" class="loading-state">
      <view v-for="i in 3" :key="i" class="skeleton-item">
        <view class="skeleton skeleton-content" />
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed && !list.length" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">订单加载失败</text>
      <view class="retry-btn" @click="reload">点击重试</view>
    </view>

    <!-- Empty -->
    <view v-else-if="!list.length" class="empty-state">
      <text class="empty-icon">◇</text>
      <text class="empty-title">暂无生活订单</text>
      <text class="empty-desc">先去服务大厅看看热门服务</text>
      <view class="empty-btn" @click="goLife">去逛逛</view>
    </view>

    <!-- Orders List -->
    <view v-else class="orders-list">
      <view v-for="item in list" :key="item.no" class="order-card">
        <view class="order-header">
          <text class="order-no">{{ item.no }}</text>
          <view class="order-status" :class="item.badge">
            {{ item.status }}
          </view>
        </view>
        <text class="order-name">{{ item.name }}</text>
        <text class="order-time">预约时间：{{ item.time }}</text>
      </view>

      <view v-if="hasMore" class="load-more" @click="fetchList">
        {{ loading ? '加载中...' : '加载更多' }}
      </view>
      <view v-else class="load-more done">— 没有更多了 —</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app';
import { localLifeApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const page = ref(1);
const pageSize = 10;
const hasMore = ref(true);
const list = ref([]);

const toLifeOrderView = (item = {}, index = 0) => {
  const status = item.status_text || item.status || '待上门';
  return {
    no: item.order_no || item.no || `LIFE-${Date.now()}-${index}`,
    name: item.service_name || item.title || '未命名服务订单',
    time: item.appointment_time || item.time || item.created_at || '--',
    status,
    badge: status === '已完成' ? 'done' : status === '已取消' ? 'cancel' : 'pending'
  };
};

const fetchList = async ({ reset = false } = {}) => {
  if (loading.value) return;
  if (!reset && !hasMore.value) return;

  loading.value = true;
  failed.value = false;
  const targetPage = reset ? 1 : page.value;

  try {
    const res = await localLifeApi.orders({ page: targetPage, page_size: pageSize });
    const rows = pickListPayload(res).map(toLifeOrderView);
    list.value = reset ? rows : [...list.value, ...rows];
    hasMore.value = rows.length >= pageSize;
    page.value = targetPage + 1;
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const reload = () => fetchList({ reset: true });

function goBack() {
  uni.navigateBack();
}

function goLife() {
  uni.navigateTo({ url: '/subpackages/life/index' });
}

onShow(() => {
  trackPageView('life_orders');
  reload();
});

onPullDownRefresh(async () => {
  await reload();
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  fetchList();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.life-orders-page {
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

/* Orders List */
.orders-list {
  padding: 24rpx;
}

.order-card {
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  margin-bottom: 16rpx;
  box-shadow: var(--shadow-sm);
}

.order-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.order-no {
  font-size: 22rpx;
  color: var(--text-muted);
}

.order-status {
  padding: 6rpx 16rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.order-status.done {
  background: var(--primary-bg);
  color: var(--primary);
}

.order-status.pending {
  background: var(--secondary-bg);
  color: var(--secondary);
}

.order-status.cancel {
  background: var(--bg);
  color: var(--text-muted);
}

.order-name {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  display: block;
  margin-bottom: 8rpx;
}

.order-time {
  font-size: 22rpx;
  color: var(--text-muted);
}

.load-more {
  text-align: center;
  padding: 24rpx;
  font-size: 24rpx;
  color: var(--text-muted);
}

.load-more.done {
  color: var(--border);
}
</style>
