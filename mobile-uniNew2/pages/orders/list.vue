<template>
  <view class="orders-page">
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <view class="header-copy">
        <text class="page-title">我的订单</text>
        <text v-if="orders.length" class="page-count">当前 {{ orders.length }} 笔</text>
      </view>
      <view class="icon-button placeholder" />
    </view>

    <view class="tabs-wrap">
      <scroll-view class="tabs-scroll" scroll-x enhanced :show-scrollbar="false">
        <view class="tabs-track">
          <view
            v-for="status in statuses"
            :key="status"
            class="status-tab"
            :class="{ active: activeStatus === status }"
            @click="changeStatus(status)"
          >
            {{ status }}
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="content-area">
      <StateView v-if="loading && !orders.length" type="loading" title="正在加载订单" />
      <StateView
        v-else-if="failed && !orders.length"
        type="error"
        title="订单加载失败"
        description="请检查网络后重试"
        :show-retry="true"
        @retry="reload"
      />
      <StateView
        v-else-if="!orders.length"
        type="empty"
        title="暂无订单"
        description="该状态下还没有订单"
      />

      <view v-else class="order-list">
        <view
          v-for="order in orders"
          :key="order.no"
          class="order-card"
          @click="viewDetail(order.id)"
        >
          <view class="order-head">
            <text class="order-no">{{ order.no }}</text>
            <view class="order-status" :class="order.badgeClass">
              <view class="status-dot" />
              <text>{{ order.status }}</text>
            </view>
          </view>

          <text class="order-title">{{ order.title }}</text>
          <view class="order-meta">
            <text>{{ order.time }}</text>
            <text class="meta-separator">·</text>
            <text>{{ order.channel }}</text>
          </view>

          <view class="payment-line">
            <text class="payment-method">{{ order.paymentCombo }}</text>
            <view class="amount-wrap">
              <text class="amount-label">{{ order.canPay ? '待支付' : '订单金额' }}</text>
              <text class="amount-price">¥{{ order.canPay ? order.cashDue : order.amount }}</text>
            </view>
          </view>

          <view v-if="order.canPay || order.canCancel || order.canConfirm || order.canRefund" class="order-actions">
            <button
              v-if="order.canCancel"
              class="order-button secondary"
              @click.stop="cancelOrder(order)"
            >
              取消订单
            </button>
            <button
              v-if="order.canRefund"
              class="order-button secondary"
              @click.stop="refundOrder(order)"
            >
              申请退款
            </button>
            <button
              v-if="order.canConfirm"
              class="order-button primary"
              @click.stop="confirmOrder(order)"
            >
              确认收货
            </button>
            <button
              v-if="order.canPay"
              class="order-button primary"
              :disabled="busyOrderId === order.id"
              @click.stop="payOrder(order)"
            >
              {{ busyOrderId === order.id ? '处理中...' : '去支付' }}
            </button>
          </view>
        </view>

        <view class="load-more" @click="fetchOrders()">
          <view v-if="loading" class="loading-dot" />
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
const busyOrderId = ref(null);
const page = ref(1);
const pageSize = 10;
const hasMore = ref(true);
const paymentReturn = ref(null);
const paymentReturnHandled = ref(false);

const loadMoreText = computed(() => {
  if (loading.value) return '正在加载';
  return hasMore.value ? '加载更多' : '已经到底了';
});

function goBack() {
  const pages = getCurrentPages();
  if (pages.length <= 1) {
    uni.switchTab({ url: '/pages/profile/index' });
    return;
  }
  uni.navigateBack();
}

async function fetchOrders({ reset = false } = {}) {
  if (loading.value || (!reset && !hasMore.value)) return;
  loading.value = true;
  failed.value = false;
  const targetPage = reset ? 1 : page.value;
  try {
    const response = await orderApi.list({
      page: targetPage,
      page_size: pageSize,
      status: statusParams[activeStatus.value] || undefined
    });
    const rows = pickListPayload(response);
    const mapped = rows.map(toOrderView);
    orders.value = reset ? mapped : [...orders.value, ...mapped];
    hasMore.value = rows.length >= pageSize;
    page.value = targetPage + 1;
    if (reset) {
      await orderApi.markViewed(statusParams[activeStatus.value] || 'all');
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

const reload = () => fetchOrders({ reset: true });

function changeStatus(status) {
  if (activeStatus.value === status) return;
  activeStatus.value = status;
  orders.value = [];
  hasMore.value = true;
  trackEvent('orders_change_status', { status });
  reload();
}

function viewDetail(orderId) {
  trackEvent('orders_click_detail', { id: orderId, status: activeStatus.value });
  uni.navigateTo({ url: `/subpackages/order/detail?id=${orderId}` });
}

async function payOrder(order) {
  if (busyOrderId.value) return;
  busyOrderId.value = order.id;
  try {
    const payChannel = order.payChannel || order.payChannelOptions?.[0];
    if (!payChannel) {
      uni.showToast({ title: '当前订单暂无可用支付方式', icon: 'none' });
      return;
    }
    const result = await orderApi.pay(order.id, { pay_channel: payChannel, auto_complete: true });
    const payment = result?.payment;
    if (payment?.status === 'FAILED') {
      throw new Error(payment.message || '支付参数创建失败');
    }
    if (payment?.status === 'PAID') {
      uni.showToast({ title: '支付完成', icon: 'success' });
      await reload();
      return;
    }
    const platformResult = await requestPlatformPayment(payment);
    if (platformResult?.redirected) return;
    if (payment?.out_trade_no) {
      try {
        await orderApi.syncPayment(order.id, payment.out_trade_no, null, payChannel);
      } catch (error) {
        // The provider callback can arrive after the native payment succeeds;
        // the regular order reload remains the source of truth.
      }
    }
    await reload();
  } catch (error) {
    const message = String(error?.errMsg || error?.message || '');
    uni.showToast({ title: message.includes('cancel') ? '已取消支付' : '支付未完成', icon: 'none' });
  } finally {
    busyOrderId.value = null;
  }
}

async function confirmOrder(order) {
  await orderApi.confirm(order.id);
  uni.showToast({ title: '已确认收货', icon: 'success' });
  await reload();
}

function cancelOrder(order) {
  uni.showModal({
    title: '取消订单',
    content: '取消后库存和已抵扣资产将自动退回。',
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
    title: '申请退款',
    content: '退款后库存和已抵扣资产将自动退回。',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.refund(order.id);
      uni.showToast({ title: '退款已提交', icon: 'success' });
      await reload();
    }
  });
}

function queryValue(value) {
  if (Array.isArray(value)) return value[value.length - 1];
  return value;
}

function normalizePaymentChannel(value = '') {
  const normalized = String(value || '').trim().toUpperCase();
  if (['WXPAY', 'WECHAT', 'WECHATPAY', 'WEIXIN', 'WX'].includes(normalized)) return 'WECHAT';
  if (['ALIPAY', 'ALI_PAY', 'ALI'].includes(normalized)) return 'ALIPAY';
  return '';
}

onLoad((options) => {
  if (options?.status && statuses.includes(options.status)) activeStatus.value = options.status;
  const orderId = queryValue(options?.id || options?.order_id || '');
  const outTradeNo = queryValue(options?.out_trade_no || options?.outTradeNo || '');
  if (orderId && outTradeNo) {
    paymentReturn.value = {
      orderId,
      outTradeNo,
      payChannel: normalizePaymentChannel(queryValue(
        options?.provider || options?.payment_provider || options?.pay_provider || options?.pay_channel
      ))
    };
  }
});

async function syncReturnedPayment() {
  if (paymentReturnHandled.value || !paymentReturn.value) return;
  paymentReturnHandled.value = true;
  try {
    const result = await orderApi.syncPayment(
      paymentReturn.value.orderId,
      paymentReturn.value.outTradeNo,
      null,
      paymentReturn.value.payChannel
    );
    if (result?.payment_status === 'PAID') {
      uni.showToast({ title: '支付状态已更新', icon: 'success' });
    }
  } catch (error) {
    // The list still reloads below; a delayed provider callback is expected.
  }
}

onShow(async () => {
  trackPageView('orders_list');
  await syncReturnedPayment();
  await reload();
});

onPullDownRefresh(async () => {
  await reload();
  uni.stopPullDownRefresh();
});

onReachBottom(() => fetchOrders());
</script>

<style scoped>
@import '@/styles/common.css';

.orders-page {
  width: 100%;
  max-width: 100vw;
  min-height: 100vh;
  background: #F6F7F8;
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
  overflow-x: hidden;
  box-sizing: border-box;
}

.page-header {
  display: grid;
  grid-template-columns: 64rpx 1fr 64rpx;
  align-items: center;
  min-height: 96rpx;
  padding: env(safe-area-inset-top) 24rpx 0;
  background: #FFFFFF;
  border-bottom: 1rpx solid #ECEEF0;
  box-sizing: content-box;
}

.icon-button {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #27272A;
  font-size: 38rpx;
}

.icon-button.placeholder {
  visibility: hidden;
}

.header-copy {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 12rpx;
}

.page-title {
  color: #18181B;
  font-size: 32rpx;
  font-weight: 700;
}

.page-count {
  color: #8B8B93;
  font-size: 22rpx;
}

.tabs-wrap {
  position: sticky;
  top: 0;
  z-index: 30;
  padding: 16rpx 20rpx;
  background: rgba(255, 255, 255, 0.97);
  border-bottom: 1rpx solid #ECEEF0;
  overflow: hidden;
  box-sizing: border-box;
}

.tabs-scroll {
  display: block;
  width: 100%;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  box-sizing: border-box;
  scrollbar-width: none;
}

.tabs-scroll::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.tabs-track {
  display: inline-flex;
  gap: 8rpx;
  min-width: 100%;
}

.status-tab {
  height: 64rpx;
  padding: 0 24rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #606068;
  background: #F2F3F4;
  border-radius: 12rpx;
  font-size: 25rpx;
  font-weight: 600;
  box-sizing: border-box;
}

.status-tab.active {
  color: #FFFFFF;
  background: #07845D;
}

.content-area {
  width: 100%;
  padding: 20rpx;
  box-sizing: border-box;
}

.order-list {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.order-card {
  width: 100%;
  min-width: 0;
  padding: 24rpx;
  background: #FFFFFF;
  border: 1rpx solid #E5E7EB;
  border-radius: 16rpx;
  box-shadow: 0 2rpx 6rpx rgba(24, 24, 27, 0.04);
  box-sizing: border-box;
}

.order-card:active {
  background: #FAFAFA;
}

.order-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.order-no {
  min-width: 0;
  overflow: hidden;
  color: #85858D;
  font-size: 22rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-status {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8rpx;
  color: #9A4D12;
  font-size: 24rpx;
  font-weight: 700;
}

.status-dot {
  width: 12rpx;
  height: 12rpx;
  background: currentColor;
  border-radius: 50%;
}

.order-status.badge-success { color: #087052; }
.order-status.badge-info { color: #326AA5; }
.order-status.badge-warning { color: #B75B15; }

.order-title {
  display: -webkit-box;
  margin-top: 18rpx;
  overflow: hidden;
  color: #27272A;
  font-size: 29rpx;
  font-weight: 700;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.order-meta {
  display: flex;
  align-items: center;
  gap: 8rpx;
  margin-top: 10rpx;
  color: #85858D;
  font-size: 23rpx;
}

.meta-separator {
  color: #C4C4C8;
}

.payment-line {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20rpx;
  margin-top: 22rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid #ECEEF0;
}

.payment-method {
  min-width: 0;
  flex: 1;
  color: #047857;
  font-size: 23rpx;
}

.amount-wrap {
  flex-shrink: 0;
  display: flex;
  align-items: baseline;
  gap: 10rpx;
}

.amount-label {
  color: #71717A;
  font-size: 22rpx;
}

.amount-price {
  color: #D55312;
  font-size: 32rpx;
  font-weight: 800;
}

.order-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12rpx;
  margin-top: 20rpx;
}

.order-button {
  min-width: 144rpx;
  height: 68rpx;
  margin: 0;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  font-size: 25rpx;
  font-weight: 700;
  line-height: 1;
}

.order-button::after {
  border: 0;
}

.order-button.primary {
  color: #FFFFFF;
  background: #07845D;
}

.order-button.secondary {
  color: #52525B;
  background: #FFFFFF;
  border: 1rpx solid #D4D4D8;
}

.order-button[disabled] {
  opacity: 0.55;
}

.load-more {
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  color: #85858D;
  font-size: 23rpx;
}

.loading-dot {
  width: 20rpx;
  height: 20rpx;
  border: 3rpx solid #A1A1AA;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .loading-dot { animation: none; }
}
</style>
