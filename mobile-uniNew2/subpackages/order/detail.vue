<template>
  <view class="detail-page">
    <!-- Header -->
    <view class="page-header">
      <view class="back-btn" @click="goBack">←</view>
      <text class="header-title">订单详情</text>
      <view class="header-spacer" />
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view class="skeleton skeleton-header" />
      <view class="skeleton skeleton-line" />
      <view class="skeleton skeleton-line short" />
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">订单详情加载失败</text>
      <view class="retry-btn" @click="loadDetail">点击重试</view>
    </view>

    <template v-else>
      <!-- Status Header -->
      <view class="status-header">
        <view class="status-icon">{{ statusIcon }}</view>
        <view class="status-info">
          <text class="status-text">{{ detail.status }}</text>
          <text class="status-hint">{{ statusHint }}</text>
        </view>
      </view>

      <view v-if="detail.requiresShipping" class="info-card">
        <text class="section-title">收货与物流</text>
        <template v-if="detail.shippingAddress">
          <view class="info-row">
            <text class="info-label">收货人</text>
            <text class="info-value">{{ detail.shippingAddress.receiver_name }} {{ detail.shippingAddress.receiver_phone }}</text>
          </view>
          <view class="info-row">
            <text class="info-label">收货地址</text>
            <text class="info-value">{{ detail.shippingAddress.full_address }}</text>
          </view>
        </template>
        <view v-if="detail.shipment?.tracking_no" class="info-row">
          <text class="info-label">物流信息</text>
          <text class="info-value">{{ detail.shipment.carrier_name || '物流公司' }} {{ detail.shipment.tracking_no }}</text>
        </view>
        <text v-else-if="detail.status === '待发货'" class="payment-note">商家备货中，发货后将显示真实物流单号。</text>
      </view>

      <!-- Order Info Card -->
      <view class="info-card">
        <view class="card-header">
          <text class="card-tag">订单中心</text>
        </view>
        <view class="info-row">
          <text class="info-label">订单编号</text>
          <text class="info-value">{{ detail.no }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">支付组合</text>
          <text class="info-value">{{ detail.paymentCombo }}</text>
        </view>
        <view class="info-row highlight">
          <text class="info-label">订单总额</text>
          <text class="info-value price">¥{{ detail.amount }}</text>
        </view>
      </view>

      <!-- Payment Info Card -->
      <view class="info-card">
        <text class="section-title">支付信息</text>
        <view class="info-row">
          <text class="info-label">商品总额</text>
          <text class="info-value">¥{{ detail.totalAmount }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">资产抵扣</text>
          <text class="info-value">-¥{{ detail.discountAmount }}</text>
        </view>
        <view class="info-row strong">
          <text class="info-label">待支付金额</text>
          <text class="info-value price">¥{{ detail.cashDue }}</text>
        </view>
        <view v-if="detail.paymentMessage" class="payment-note">{{ detail.paymentMessage }}</view>
      </view>

      <!-- Items Card -->
      <view v-if="detail.items.length" class="items-card">
        <text class="section-title">订单商品</text>
        <view v-for="item in detail.items" :key="item.id" class="order-item">
          <view class="item-image">
            <view class="image-placeholder" />
          </view>
          <view class="item-info">
            <text class="item-title">{{ item.product_name }}</text>
            <text class="item-meta">数量 {{ item.quantity }} / 单价 ¥{{ item.unit_price }}</text>
            <text class="item-subtotal">小计 ¥{{ item.total_amount }}</text>
          </view>
        </view>
      </view>

      <!-- Timeline Card -->
      <view v-if="detail.steps.length" class="timeline-card">
        <text class="section-title">进度轨迹</text>
        <view class="timeline">
          <view
            v-for="(item, idx) in detail.steps"
            :key="`${item.title}-${item.time}`"
            class="timeline-item"
          >
            <view class="timeline-dot" :class="{ active: item.active, last: idx === detail.steps.length - 1 }" />
            <view class="timeline-content">
              <text class="timeline-title">{{ item.title }}</text>
              <text class="timeline-time">{{ item.time }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Actions -->
      <view class="action-section">
        <button v-if="detail.canPay" class="action-btn primary" @click="payOrder">
          {{ paying ? '支付中...' : '继续支付' }}
        </button>
        <button v-if="detail.canConfirm" class="action-btn secondary" @click="confirmOrder">
          确认收货
        </button>
        <button v-if="detail.canCancel" class="action-btn secondary" @click="cancelOrder">
          取消订单
        </button>
        <button v-if="detail.canRefund" class="action-btn secondary" @click="refundOrder">
          申请退款
        </button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { orderApi } from '@/api/modules';
import { requestPayment as requestPlatformPayment } from '@/utils/payment';
import { trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const paying = ref(false);
const id = ref('');

const detail = ref({
  status: '处理中',
  no: '--',
  amount: '0.00',
  totalAmount: '0.00',
  discountAmount: '0.00',
  cashDue: '0.00',
  payStatus: '未支付',
  paymentCombo: '--',
  paymentMessage: '',
  channel: '商城订单',
  steps: [],
  items: [],
  canPay: false,
  canConfirm: false,
  canCancel: false,
  canRefund: false,
  requiresShipping: false,
  shippingAddress: null,
  shipment: null,
  payChannel: '',
  payChannelOptions: []
});

const statusIcon = computed(() => {
  if (detail.value.payStatus === '已支付') return '◆';
  return '◇';
});

const statusHint = computed(() => ({
  '待支付': '请尽快完成支付',
  '待发货': '订单已支付，商家正在备货',
  '已发货': '商品已发出，请留意物流信息',
  '已完成': '订单已完成',
  '已取消': '订单已取消',
  '已退款': '订单已退款'
}[detail.value.status] || '订单状态已更新'));

function normalizeSteps(timeline) {
  if (Array.isArray(timeline) && timeline.length) {
    return timeline.map((item, idx) => ({
      title: item.title || item.name || `节点 ${idx + 1}`,
      time: item.time || item.created_at || '--',
      active: item.active ?? true
    }));
  }
  return [
    { title: '订单创建', time: '--', active: true },
    { title: '处理中', time: '--', active: false }
  ];
}

function findPaymentCombo(assetDeductions = [], payableAmount = 0, payStatus = '') {
  const types = new Set((assetDeductions || []).map((item) => item.asset_type));
  if (types.has('BALANCE') && types.has('POINTS')) return '余额 + 积分';
  if (types.has('VOUCHER') && types.has('POINTS')) return '消费金 + 积分';
  if (types.has('POINTS') && Number(payableAmount || 0) > 0) return '外部支付 + 积分';
  if (types.has('BALANCE')) return '余额支付';
  if (types.has('VOUCHER')) return '消费金支付';
  if (payStatus === 'PAID' && Number(payableAmount || 0) === 0) return '已完成支付';
  return '待支付';
}

function preferredPayChannel(options = [], cashDue = 0, fallback = '') {
  if (Number(cashDue || 0) > 0) {
    const externalChannel = options.find((item) => ['ALIPAY', 'WECHAT'].includes(item));
    if (externalChannel) return externalChannel;
  }
  return fallback || options[0] || '';
}

function normalize(res) {
  const order = res?.order || res || {};
  const items = Array.isArray(res?.items) ? res.items : [];
  const deductions = Array.isArray(res?.asset_deductions) ? res.asset_deductions : [];
  const payableAmount = Number(order?.payable_amount ?? order?.amount ?? 0);
  const totalAmount = Number(order?.total_amount ?? payableAmount);
  const discountAmount = Number(order?.discount_amount ?? 0);
  const payStatus = order?.pay_status || 'UNPAID';
  const orderStatus = order?.status_text || order?.order_status || order?.status || '处理中';
  const payChannelOptions = Array.isArray(res?.pay_channel_options)
    ? res.pay_channel_options
    : (Array.isArray(order?.pay_channel_options) ? order.pay_channel_options : []);

  return {
    status: orderStatus,
    no: order?.order_no || order?.no || '--',
    amount: totalAmount.toFixed(2),
    totalAmount: totalAmount.toFixed(2),
    discountAmount: discountAmount.toFixed(2),
    cashDue: payableAmount.toFixed(2),
    payStatus: payStatus === 'PAID' ? '已支付' : payStatus === 'REFUNDED' ? '已退款' : '未支付',
    paymentCombo: res?.payment_combo || order?.payment_combo || findPaymentCombo(deductions, payableAmount, payStatus),
    paymentMessage: res?.payment_message || (payableAmount > 0 ? '支付单已生成，请完成支付，订单状态以服务器异步通知为准。' : '订单已完成支付。'),
    channel: order?.channel_text || order?.channel || '商城订单',
    steps: normalizeSteps(order?.timeline || order?.steps || res?.timeline || res?.steps),
    items,
    payChannel: preferredPayChannel(payChannelOptions, payableAmount, res?.default_pay_channel || order?.default_pay_channel || ''),
    payChannelOptions,
    canPay: Boolean(order?.can_pay ?? res?.can_pay ?? payStatus !== 'PAID'),
    canConfirm: Boolean(order?.can_confirm ?? res?.can_confirm ?? false),
    canCancel: Boolean(order?.can_cancel ?? res?.can_cancel ?? false),
    canRefund: Boolean(order?.can_refund ?? res?.can_refund ?? false),
    requiresShipping: Boolean(order?.requires_shipping ?? res?.requires_shipping),
    shippingAddress: res?.shipping_address || order?.shipping_address || null,
    shipment: res?.shipment || order?.shipment || null
  };
}

const loadDetail = async () => {
  if (!id.value) return;
  loading.value = true;
  failed.value = false;
  try {
    const res = await orderApi.detail(id.value);
    detail.value = normalize(res || {});
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const goBack = () => uni.navigateBack();

async function payOrder() {
  paying.value = true;
  try {
    const payChannel = detail.value.payChannel || detail.value.payChannelOptions?.[0];
    if (!payChannel) {
      uni.showToast({ title: '当前订单暂无可用支付方式', icon: 'none' });
      return;
    }
    const result = await orderApi.pay(id.value, {
      pay_channel: payChannel,
      auto_complete: true
    });
    const payment = result?.payment;
    if (payment?.status === 'PAID') {
      uni.showToast({ title: '支付完成', icon: 'success' });
      await loadDetail();
      return;
    }
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
    await loadDetail();
  } finally {
    paying.value = false;
  }
}

async function confirmOrder() {
  await orderApi.confirm(id.value);
  uni.showToast({ title: '订单已完成', icon: 'success' });
  await loadDetail();
}

function cancelOrder() {
  uni.showModal({
    title: '取消订单',
    content: '取消后将恢复库存并退回已抵扣资产，是否继续？',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.cancel(id.value);
      uni.showToast({ title: '订单已取消', icon: 'success' });
      await loadDetail();
    }
  });
}

function refundOrder() {
  uni.showModal({
    title: '订单退款',
    content: '确认申请退款吗？退款后将恢复库存并退回资产。',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.refund(id.value);
      uni.showToast({ title: '订单已退款', icon: 'success' });
      await loadDetail();
    }
  });
}

onLoad((query) => {
  id.value = query?.id || '';
  trackPageView('order_detail_view', { id: id.value });
  loadDetail();
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

/* Status Header */
.status-header {
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 40rpx 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
}

.status-icon {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
  color: white;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.status-text {
  font-size: 36rpx;
  font-weight: 700;
  color: white;
}

.status-hint {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

/* Info Cards */
.info-card {
  margin: 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.card-header {
  margin-bottom: 24rpx;
}

.card-tag {
  display: inline-flex;
  padding: 8rpx 20rpx;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 24rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 24rpx;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid var(--border-light);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 26rpx;
  color: var(--text-muted);
}

.info-value {
  font-size: 26rpx;
  color: var(--text);
  font-weight: 500;
}

.info-value.price {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--secondary);
}

.info-row.highlight {
  background: var(--bg);
  margin: 16rpx -16rpx;
  padding: 20rpx 16rpx;
  border-radius: var(--radius-md);
  border: none;
}

.info-row.strong {
  background: var(--primary-bg);
  margin: 16rpx -16rpx;
  padding: 20rpx 16rpx;
  border-radius: var(--radius-md);
  border: none;
}

.payment-note {
  margin-top: 20rpx;
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-md);
  font-size: 22rpx;
  color: var(--text-muted);
  line-height: 1.6;
}

/* Items Card */
.items-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  margin-bottom: 24rpx;
}

.order-item {
  display: flex;
  gap: 20rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid var(--border-light);
}

.order-item:last-child {
  border-bottom: none;
}

.item-image {
  width: 120rpx;
  height: 120rpx;
  border-radius: var(--radius-md);
  overflow: hidden;
  flex-shrink: 0;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--primary-bg), var(--primary));
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.item-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
  line-height: 1.3;
}

.item-meta {
  font-size: 22rpx;
  color: var(--text-muted);
}

.item-subtotal {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--secondary);
}

/* Timeline Card */
.timeline-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  margin-bottom: 24rpx;
}

.timeline {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: 20rpx;
  position: relative;
}

.timeline-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
  background: var(--border);
  flex-shrink: 0;
  margin-top: 6rpx;
  z-index: 1;
}

.timeline-dot.active {
  background: var(--primary);
  box-shadow: 0 0 0 6rpx var(--primary-bg);
}

.timeline-dot.last {
  background: var(--border-light);
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 9rpx;
  top: 26rpx;
  width: 2rpx;
  height: calc(100% + 20rpx);
  background: var(--border-light);
}

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding-bottom: 32rpx;
}

.timeline-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
}

.timeline-item:not(:has(+ .timeline-item)) .timeline-title,
.timeline-dot:not(.active) + .timeline-content .timeline-title {
  color: var(--text-muted);
}

.timeline-time {
  font-size: 22rpx;
  color: var(--text-muted);
}

/* Loading State */
.loading-state {
  padding: 24rpx;
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-header {
  height: 160rpx;
  border-radius: var(--radius-xl);
}

.skeleton-line {
  height: 100rpx;
  margin-top: 24rpx;
  border-radius: var(--radius-xl);
}

.skeleton-line.short {
  width: 60%;
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

/* Action Section */
.action-section {
  display: flex;
  gap: 24rpx;
  padding: 32rpx 24rpx;
}

.action-btn {
  flex: 1;
  height: 96rpx;
  border-radius: 48rpx;
  font-size: 30rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
}

.action-btn.primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  box-shadow: 0 8rpx 24rpx rgba(16, 185, 129, 0.25);
}

.action-btn.secondary {
  background: var(--bg);
  color: var(--text);
  border: 2rpx solid var(--border);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background: var(--border-light);
  }

  .action-btn {
    transition: none;
  }

  .action-btn:active {
    transform: none;
  }
}
</style>
