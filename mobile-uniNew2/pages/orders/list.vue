<template>
  <view class="orders-page">
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
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <rect x="9" y="3" width="6" height="4" rx="1" stroke="white" stroke-width="2"/>
            <path d="M9 12h6M9 16h6" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </view>
        <text class="page-title">我的订单</text>
        <view class="header-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor"/>
          </svg>
          实时
        </view>
      </view>
    </view>

    <!-- Hero Card -->
    <view class="hero-card">
      <view class="hero-content">
        <view class="hero-tag">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" stroke-width="2"/>
          </svg>
          ORDER CENTER
        </view>
        <text class="hero-title">订单中心</text>
        <text class="hero-subtitle">商品下单、购物车结算、支付完成都在这里查看</text>
      </view>

      <!-- Stats Row -->
      <view class="stats-row">
        <view class="stat-item">
          <text class="stat-value">{{ orders.length }}</text>
          <text class="stat-label">当前订单</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ pendingPayCount }}</text>
          <text class="stat-label">待支付</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ completedCount }}</text>
          <text class="stat-label">已完成</text>
        </view>
      </view>
    </view>

    <!-- Status Tabs -->
    <view class="status-tabs">
      <scroll-view class="tabs-scroll" scroll-x enhanced show-scrollbar="false">
        <view
          v-for="status in statuses"
          :key="status"
          class="status-tab"
          :class="{ active: activeStatus === status }"
          @click="changeStatus(status)"
        >
          {{ status }}
        </view>
      </scroll-view>
    </view>

    <!-- Content -->
    <view class="content-area">
      <!-- Loading State -->
      <StateView v-if="loading && !orders.length" title="订单加载中..." />

      <!-- Error State -->
      <StateView
        v-else-if="failed && !orders.length"
        title="订单加载失败"
        :show-retry="true"
        @retry="reload"
      />

      <!-- Empty State -->
      <StateView
        v-else-if="!orders.length"
        title="暂无该状态订单"
        description="切换筛选条件，或返回首页继续下单。"
      />

      <!-- Order List -->
      <view v-else class="order-list">
        <view
          v-for="order in orders"
          :key="order.no"
          class="order-card"
          @click="viewDetail(order.id)"
        >
          <!-- Order Header -->
          <view class="order-header">
            <view class="order-no-wrap">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" stroke-width="2"/>
              </svg>
              <text class="order-no">{{ order.no }}</text>
            </view>
            <view class="order-status" :class="order.badgeClass">
              {{ order.status }}
            </view>
          </view>

          <!-- Order Info -->
          <view class="order-info">
            <text class="order-title">{{ order.title }}</text>
            <view class="order-meta">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <text>{{ order.time }}</text>
              <text class="meta-dot">·</text>
              <text>{{ order.channel }}</text>
            </view>
            <view class="order-extra">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <rect x="1" y="4" width="22" height="16" rx="2" stroke="currentColor" stroke-width="2"/>
                <path d="M1 10h22" stroke="currentColor" stroke-width="2"/>
              </svg>
              {{ order.paymentCombo }}
            </view>
          </view>

          <!-- Order Footer -->
          <view class="order-footer">
            <view class="order-amount">
              <text class="amount-symbol">¥</text>
              <text class="amount-value">{{ order.amount }}</text>
              <text v-if="order.canPay" class="amount-due">待支付 ¥{{ order.cashDue }}</text>
            </view>
            <view class="order-actions">
              <view class="action-btn secondary" @click.stop="viewDetail(order.id)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke="currentColor" stroke-width="2"/>
                  <path d="Sonnet58 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" stroke="currentColor" stroke-width="2"/>
                </svg>
                详情
              </view>
              <view
                v-if="order.canPay"
                class="action-btn primary"
                @click.stop="payOrder(order)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <rect x="1" y="4" width="22" height="16" rx="2" stroke="currentColor" stroke-width="2"/>
                  <path d="M1 10h22" stroke="currentColor" stroke-width="2"/>
                </svg>
                去支付
              </view>
              <view
                v-if="order.canCancel"
                class="action-btn secondary"
                @click.stop="cancelOrder(order)"
              >
                取消订单
              </view>
              <view
                v-if="order.canConfirm"
                class="action-btn primary"
                @click.stop="confirmOrder(order)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                确认收货
              </view>
              <view
                v-if="order.canRefund"
                class="action-btn secondary"
                @click.stop="refundOrder(order)"
              >
                申请退款
              </view>
            </view>
          </view>
        </view>

        <!-- Load More -->
        <view class="load-more">
          <text>{{ loadMoreText }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad, onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { orderApi } from '@/api/modules';
import { pickListPayload, toOrderView } from '@/utils/adapters';
import { requestPayment as requestPlatformPayment } from '@/utils/payment';
import { trackEvent, trackPageView } from '@/utils/track';

const statuses = ['全部', '待支付', '待发货', '已发货', '已完成', '取消/退款'];
const statusParams = {
  待支付: 'pending_payment',
  待发货: 'pending_ship',
  已发货: 'shipped',
  已完成: 'completed',
  '取消/退款': 'refund'
};

const activeStatus = ref('全部');
const loading = ref(false);
const failed = ref(false);
const orders = ref([]);
const page = ref(1);
const pageSize = 10;
const hasMore = ref(true);

const pendingPayCount = computed(() => {
  return orders.value.filter((item) =>
    (item.status_text || item.status) === '待支付' || item.canPay
  ).length;
});

const completedCount = computed(() => {
  return orders.value.filter((item) =>
    (item.status_text || item.status) === '已完成'
  ).length;
});

const goBack = () => {
  uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/profile/index' }) });
};

const fetchOrders = async ({ reset = false } = {}) => {
  if (loading.value) return;
  if (!reset && !hasMore.value) return;
  loading.value = true;
  failed.value = false;

  const targetPage = reset ? 1 : page.value;
  try {
    const res = await orderApi.list({
      page: targetPage,
      page_size: pageSize,
      status: statusParams[activeStatus.value] || undefined
    });

    const allRows = pickListPayload(res);
    const mappedRows = allRows.map(toOrderView);
    orders.value = reset ? mappedRows : [...orders.value, ...mappedRows];
    hasMore.value = allRows.length >= pageSize;
    page.value = targetPage + 1;
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const reload = () => fetchOrders({ reset: true });

const changeStatus = (status) => {
  if (activeStatus.value === status) return;
  activeStatus.value = status;
  trackEvent('orders_change_status', { status });
  reload();
};

const loadMoreText = computed(() => {
  if (loading.value) return '加载更多中...';
  return hasMore.value ? '上拉加载更多' : '没有更多订单了';
});

const viewDetail = (id) => {
  trackEvent('orders_click_detail', { id, status: activeStatus.value });
  uni.navigateTo({ url: `/subpackages/order/detail?id=${id}` });
};

const payOrder = async (order) => {
  const payChannel = order.payChannel || order.payChannelOptions?.[0] || 'BALANCE';
  const result = await orderApi.pay(order.id, {
    pay_channel: payChannel,
    auto_complete: true
  });
  const payment = result?.payment;
  if (payment?.status !== 'PAID') {
    try {
      const platformResult = await requestPlatformPayment(payment);
      uni.showToast({
        title: platformResult?.mocked ? '支付单已创建' : '支付已提交',
        icon: platformResult?.mocked ? 'none' : 'success'
      });
    } catch (error) {
      const errMsg = String(error?.errMsg || error?.message || '');
      uni.showToast({
        title: errMsg.includes('cancel') ? '已取消支付' : '支付失败',
        icon: 'none'
      });
    }
  } else {
    uni.showToast({ title: '支付完成', icon: 'success' });
  }
  await reload();
};

const confirmOrder = async (order) => {
  await orderApi.confirm(order.id);
  uni.showToast({ title: '订单已完成', icon: 'success' });
  await reload();
};

function cancelOrder(order) {
  uni.showModal({
    title: '取消订单',
    content: '取消后将恢复库存并退回已抵扣资产，是否继续？',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.cancel(order.id);
      uni.showToast({ title: '订单已取消', icon: 'success' });
      await reload();
    }
  });
}

function refundOrder(order) {
  uni.showModal({
    title: '订单退款',
    content: '退款后将恢复库存并退回订单抵扣资产，是否继续？',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.refund(order.id);
      uni.showToast({ title: '订单已退款', icon: 'success' });
      await reload();
    }
  });
}

onLoad((options) => {
  if (options.status && statuses.includes(options.status)) {
    activeStatus.value = options.status;
  }
});

onShow(() => {
  trackPageView('orders_list');
  reload();
});

onPullDownRefresh(async () => {
  await reload();
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  fetchOrders();
});
</script>

<style scoped>
@import '@/styles/common.css';

.orders-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(env(safe-area-inset-bottom) + 120rpx);
}

/* ===== Header ===== */
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

/* ===== Hero Card ===== */
.hero-card {
  margin: 24rpx;
  padding: 32rpx;
  background: linear-gradient(135deg, rgba(5, 150, 105, 0.08), rgba(16, 185, 129, 0.04));
  border: 1rpx solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-xl);
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 16rpx;
  background: rgba(5, 150, 105, 0.1);
  color: var(--primary);
  font-size: 20rpx;
  font-weight: var(--font-bold);
  border-radius: var(--radius-full);
  margin-bottom: 16rpx;
}

.hero-title {
  display: block;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
  margin-bottom: 8rpx;
}

.hero-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.stats-row {
  display: flex;
  align-items: center;
  margin-top: 32rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-lg);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--primary);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 4rpx;
}

.stat-divider {
  width: 1rpx;
  height: 48rpx;
  background: var(--border);
}

/* ===== Status Tabs ===== */
.status-tabs {
  padding: 0 24rpx 24rpx;
  background: var(--card);
}

.tabs-scroll {
  white-space: nowrap;
}

.status-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 16rpx 28rpx;
  margin-right: 16rpx;
  background: var(--bg);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast) var(--ease-out);
}

.status-tab:last-child {
  margin-right: 0;
}

.status-tab.active {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-weight: var(--font-semibold);
}

/* ===== Content ===== */
.content-area {
  padding: 24rpx;
}

/* ===== Order List ===== */
.order-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.order-card {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 24rpx;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.order-card:active {
  transform: scale(0.99);
  box-shadow: var(--shadow-xs);
}

/* Order Header */
.order-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.order-no-wrap {
  display: flex;
  align-items: center;
  gap: 8rpx;
  color: var(--text-muted);
}

.order-no {
  font-size: var(--text-xs);
}

.order-status {
  padding: 6rpx 16rpx;
  font-size: 20rpx;
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
}

.order-status.badge-success,
.order-status.completed {
  background: rgba(5, 150, 105, 0.1);
  color: var(--primary);
}

.order-status.badge-warning,
.order-status.pending {
  background: rgba(217, 119, 6, 0.1);
  color: var(--accent);
}

.order-status.badge-info,
.order-status.shipped {
  background: rgba(59, 130, 246, 0.1);
  color: #3B82F6;
}

/* Order Info */
.order-info {
  padding-bottom: 20rpx;
  border-bottom: 1rpx solid var(--border);
}

.order-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text);
  line-height: 1.5;
  margin-bottom: 12rpx;
}

.order-meta {
  display: flex;
  align-items: center;
  gap: 6rpx;
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 8rpx;
}

.meta-dot {
  margin: 0 4rpx;
}

.order-extra {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: var(--text-xs);
  color: var(--primary);
}

/* Order Footer */
.order-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 20rpx;
}

.order-amount {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4rpx;
}

.amount-symbol {
  font-size: var(--text-sm);
  color: var(--primary);
  font-weight: var(--font-semibold);
}

.amount-value {
  font-size: var(--text-lg);
  color: var(--primary);
  font-weight: var(--font-bold);
}

.amount-due {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-left: 8rpx;
}

.order-actions {
  display: flex;
  gap: 12rpx;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 12rpx 24rpx;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast) var(--ease-out);
}

.action-btn:active {
  transform: scale(0.95);
}

.action-btn.secondary {
  background: var(--bg);
  color: var(--text-secondary);
  border: 1rpx solid var(--border);
}

.action-btn.primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
}

/* ===== Load More ===== */
.load-more {
  text-align: center;
  padding: 48rpx 0;
}

.load-more text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .status-tab,
  .order-card,
  .action-btn {
    transition: none;
  }

  .order-card:active {
    transform: none;
  }
}
</style>
