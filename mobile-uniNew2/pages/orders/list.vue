<template>
  <view class="container orders-page">
    <view class="card board order-hero">
      <view class="row-between">
        <view>
          <view class="board-tag">ORDER CENTER</view>
          <view class="board-title">订单中心</view>
          <view class="board-subtitle">商品下单、购物车结算、支付完成都在这里查看</view>
        </view>
        <view class="badge badge-blue">实时</view>
      </view>

      <view class="board-stats mt-20">
        <view class="stat-card" v-for="item in stats" :key="item.label">
          <view class="stat-num">{{ item.value }}</view>
          <view class="stat-label">{{ item.label }}</view>
        </view>
      </view>
    </view>

    <view class="status-wrap mt-20">
      <view
        v-for="status in statuses"
        :key="status"
        class="status-chip interactive"
        :class="{ active: activeStatus === status }"
        @click="changeStatus(status)"
      >
        {{ status }}
      </view>
    </view>

    <view class="mt-20">
      <StateView v-if="loading && !orders.length" title="订单加载中..." />
      <StateView v-else-if="failed && !orders.length" title="订单加载失败" :show-retry="true" @retry="reload" />

      <template v-else>
        <view v-for="order in orders" :key="order.no" class="card order-card">
          <view class="order-top row-between">
            <view class="order-no">{{ order.no }}</view>
            <text class="badge" :class="order.badgeClass">{{ order.status }}</text>
          </view>

          <view class="order-title">{{ order.title }}</view>
          <view class="order-meta">{{ order.time }} / {{ order.channel }}</view>
          <view class="order-extra">{{ order.paymentCombo }}</view>

          <view class="order-bottom">
            <view>
              <view class="order-price">¥{{ order.amount }}</view>
              <view v-if="order.canPay" class="order-due">待支付 ¥{{ order.cashDue }}</view>
            </view>
            <view class="row gap-12 order-actions">
              <button class="btn btn-ghost mini-btn" @click="viewDetail(order.id)">详情</button>
              <button v-if="order.canPay" class="btn btn-primary mini-btn" @click="payOrder(order)">去支付</button>
              <button v-else-if="order.canConfirm" class="btn btn-primary mini-btn" @click="confirmOrder(order)">确认完成</button>
            </view>
          </view>
        </view>

        <StateView
          v-if="!orders.length"
          title="暂无该状态订单"
          description="切换筛选条件，或返回首页继续下单。"
        />

        <view v-if="orders.length" class="load-more muted">{{ loadMoreText }}</view>
      </template>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { orderApi } from '@/api/modules';
import { pickListPayload, toOrderView } from '@/utils/adapters';
import { requestPayment as requestPlatformPayment } from '@/utils/payment';
import { trackEvent, trackPageView } from '@/utils/track';

const statuses = ['全部', '待支付', '已支付', '已完成'];
const statusMap = {
  全部: '',
  待支付: 'pending_payment',
  已支付: 'pending_service',
  已完成: 'completed'
};

const activeStatus = ref('全部');
const loading = ref(false);
const failed = ref(false);
const orders = ref([]);
const page = ref(1);
const pageSize = 10;
const hasMore = ref(true);

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
      status: statusMap[activeStatus.value]
    });

    const rows = pickListPayload(res).map(toOrderView);
    orders.value = reset ? rows : [...orders.value, ...rows];
    hasMore.value = rows.length >= pageSize;
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

const stats = computed(() => {
  const list = orders.value;
  return [
    { label: '当前订单', value: list.length },
    { label: '待支付', value: list.filter((item) => item.canPay).length },
    { label: '已完成', value: list.filter((item) => item.status === '已完成').length }
  ];
});

const loadMoreText = computed(() => {
  if (loading.value) return '加载更多中...';
  return hasMore.value ? '上拉加载更多' : '没有更多订单了';
});

const viewDetail = (id) => {
  trackEvent('orders_click_detail', { id, status: activeStatus.value });
  uni.navigateTo({ url: `/subpackages/order/detail?id=${id}` });
};

const payOrder = async (order) => {
  const payChannel = order.payChannel || order.payChannelOptions?.[0] || 'WECHAT';
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

.orders-page { padding-bottom: 36rpx; }
.order-hero {
  background:
    radial-gradient(circle at 95% 6%, rgba(255, 184, 125, 0.2), transparent 34%),
    linear-gradient(180deg, #fffdfb 0%, #fff4ea 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.18);
}
.board-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.board-title { margin-top: 10rpx; font-size: 36rpx; font-weight: 900; color: #4d3420; letter-spacing: 0.6rpx; }
.board-subtitle { margin-top: 8rpx; font-size: 24rpx; color: #7f6954; }
.board-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12rpx; }
.stat-card { border-radius: 18rpx; padding: 14rpx; background: rgba(255, 255, 255, 0.9); border: 1rpx solid rgba(255,154,106,.16); }
.stat-num { font-size: 34rpx; color: #ff6a00; font-weight: 900; letter-spacing: 0.3rpx; }
.stat-label { margin-top: 4rpx; font-size: 22rpx; color: #8c735c; }
.status-wrap { display: flex; gap: 12rpx; overflow-x: auto; }
.status-chip { flex-shrink: 0; padding: 10rpx 20rpx; border-radius: 999rpx; background: #fff7f0; color: #7f6954; font-size: 24rpx; border: 1rpx solid rgba(194,156,117,.18); }
.status-chip.active { background: linear-gradient(135deg, #ff7a00, #ff5f3d); color: #ffffff; border-color: transparent; }
.order-card { margin-bottom: 16rpx; border: 1rpx solid rgba(255,154,106,.18); box-shadow: 0 12rpx 28rpx rgba(141, 101, 62, 0.08); border-radius: 24rpx; }
.order-top { align-items: flex-start; }
.order-no { font-size: 23rpx; color: #8d755d; }
.order-title { margin-top: 12rpx; font-size: 30rpx; font-weight: 800; color: #503522; letter-spacing: 0.4rpx; }
.order-meta { margin-top: 8rpx; font-size: 23rpx; color: #7d6753; }
.order-extra { margin-top: 8rpx; font-size: 22rpx; color: #a06d3d; }
.order-bottom { margin-top: 16rpx; display: flex; align-items: flex-end; justify-content: space-between; gap: 12rpx; }
.order-price { font-size: 36rpx; color: #ff6a00; font-weight: 900; letter-spacing: 0.5rpx; }
.order-due { margin-top: 6rpx; font-size: 22rpx; color: #8b7158; }
.order-actions { flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }
.mini-btn { min-width: 132rpx; height: 60rpx; line-height: 60rpx; padding: 0 18rpx; font-size: 23rpx; }
.load-more { text-align: center; padding: 12rpx 0 18rpx; }
.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.98); opacity: 0.92; }
</style>
