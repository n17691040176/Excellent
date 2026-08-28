<template>
  <view class="detail-page" :class="{ 'has-actions': hasActions }">
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">订单详情</text>
      <view class="icon-button placeholder" />
    </view>

    <view v-if="loading" class="loading-state">
      <view class="skeleton status-skeleton" />
      <view class="skeleton content-skeleton" />
      <view class="skeleton content-skeleton short" />
    </view>

    <view v-else-if="failed" class="error-state">
      <text class="error-mark">!</text>
      <text class="error-title">无法加载订单</text>
      <text class="error-description">{{ errorMessage }}</text>
      <button class="retry-button" @click="loadDetail()">重新加载</button>
    </view>

    <template v-else>
      <view class="status-panel" :class="statusTone">
        <view class="status-symbol">{{ statusIcon }}</view>
        <view class="status-copy">
          <text class="status-title">{{ detail.status }}</text>
          <text class="status-description">{{ statusHint }}</text>
        </view>
      </view>

      <view v-if="returnedFromPayment" class="payment-result" :class="paymentResultTone">
        <view v-if="syncing" class="sync-spinner" />
        <text class="payment-result-text">{{ paymentResultMessage }}</text>
      </view>

      <view class="content-stack">
        <view v-if="detail.requiresShipping" class="section-card address-section">
          <view class="section-heading">
            <text class="section-title">收货信息</text>
            <text v-if="detail.shipment?.tracking_no" class="section-link">查看物流</text>
          </view>
          <template v-if="detail.shippingAddress">
            <view class="contact-line">
              <text class="contact-name">{{ detail.shippingAddress.receiver_name }}</text>
              <text class="contact-phone">{{ detail.shippingAddress.receiver_phone }}</text>
            </view>
            <text class="address-text">{{ detail.shippingAddress.full_address }}</text>
          </template>
          <text v-else class="empty-line">暂未记录收货地址</text>
          <view v-if="detail.shipment?.tracking_no" class="logistics-line">
            <text>{{ detail.shipment.carrier_name || '物流公司' }}</text>
            <text>{{ detail.shipment.tracking_no }}</text>
          </view>
        </view>

        <view v-if="detail.items.length" class="section-card">
          <view class="section-heading">
            <text class="section-title">商品</text>
            <text class="section-meta">共 {{ itemQuantity }} 件</text>
          </view>
          <view v-for="item in detail.items" :key="item.id" class="goods-row">
            <image v-if="item.image" class="goods-image" :src="item.image" mode="aspectFill" />
            <view v-else class="goods-image goods-placeholder">{{ item.product_name?.slice(0, 1) || '商' }}</view>
            <view class="goods-info">
              <text class="goods-title">{{ item.product_name }}</text>
              <text v-if="item.sku_name" class="goods-spec">{{ item.sku_name }}</text>
              <text class="goods-quantity">¥{{ money(item.unit_price) }} × {{ item.quantity }}</text>
            </view>
            <text class="goods-subtotal">¥{{ money(item.total_amount) }}</text>
          </view>
        </view>

        <view class="section-card amount-section">
          <text class="section-title">金额明细</text>
          <view class="amount-row">
            <text>商品总额</text>
            <text>¥{{ detail.totalAmount }}</text>
          </view>
          <view v-if="Number(detail.discountAmount) > 0" class="amount-row discount">
            <text>资产抵扣</text>
            <text>-¥{{ detail.discountAmount }}</text>
          </view>
          <view class="amount-row total">
            <text>{{ detail.canPay ? '待支付' : '实付金额' }}</text>
            <text class="total-price">¥{{ detail.canPay ? detail.cashDue : detail.paidAmount }}</text>
          </view>
          <view class="payment-method">
            <text>支付方式</text>
            <text>{{ detail.paymentCombo }}</text>
          </view>
        </view>

        <view class="section-card order-section">
          <text class="section-title">订单信息</text>
          <view class="info-row copyable" @click="copyOrderNo">
            <text>订单编号</text>
            <view class="info-value-wrap">
              <text class="info-value order-no">{{ detail.no }}</text>
              <text class="copy-text">复制</text>
            </view>
          </view>
          <view class="info-row">
            <text>订单类型</text>
            <text class="info-value">{{ detail.channel }}</text>
          </view>
          <view class="info-row">
            <text>创建时间</text>
            <text class="info-value">{{ detail.createdAt }}</text>
          </view>
          <view v-if="detail.paidAt !== '--'" class="info-row">
            <text>支付时间</text>
            <text class="info-value">{{ detail.paidAt }}</text>
          </view>
        </view>

        <view v-if="detail.steps.length" class="section-card timeline-section">
          <text class="section-title">订单进度</text>
          <view class="timeline">
            <view v-for="(step, index) in detail.steps" :key="`${step.title}-${index}`" class="timeline-row">
              <view class="timeline-rail">
                <view class="timeline-dot" :class="{ active: step.active }" />
                <view v-if="index < detail.steps.length - 1" class="timeline-line" />
              </view>
              <view class="timeline-copy">
                <text class="timeline-title" :class="{ active: step.active }">{{ step.title }}</text>
                <text class="timeline-time">{{ step.time }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view v-if="hasActions" class="action-bar">
        <button v-if="detail.canCancel" class="action-button secondary" @click="cancelOrder">取消订单</button>
        <button v-if="detail.canRefund" class="action-button secondary" @click="refundOrder">申请退款</button>
        <button v-if="detail.canConfirm" class="action-button primary" @click="confirmOrder">确认收货</button>
        <button v-if="detail.canPay" class="action-button primary" :disabled="paying" @click="payOrder">
          {{ paying ? '处理中...' : '继续支付' }}
        </button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { orderApi } from '@/api/modules';
import { formatDateTime, formatMoney } from '@/utils/format';
import { requestPayment as requestPlatformPayment } from '@/utils/payment';
import { trackPageView } from '@/utils/track';

const loading = ref(true);
const failed = ref(false);
const paying = ref(false);
const syncing = ref(false);
const id = ref('');
const outTradeNo = ref('');
const paymentProvider = ref('');
const alipayReturnParams = ref(null);
const errorMessage = ref('订单不存在或网络暂时不可用');
const paymentResultMessage = ref('正在确认支付结果...');
const paymentResultTone = ref('pending');

const detail = ref({
  status: '处理中',
  no: '--',
  totalAmount: '0.00',
  discountAmount: '0.00',
  cashDue: '0.00',
  paidAmount: '0.00',
  payStatusCode: 'UNPAID',
  paymentCombo: '--',
  channel: '商城订单',
  createdAt: '--',
  paidAt: '--',
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

const returnedFromPayment = computed(() => Boolean(outTradeNo.value || alipayReturnParams.value));
const hasActions = computed(() => (
  detail.value.canPay || detail.value.canConfirm || detail.value.canCancel || detail.value.canRefund
));
const itemQuantity = computed(() => detail.value.items.reduce((total, item) => total + Number(item.quantity || 0), 0));

const statusTone = computed(() => {
  if (detail.value.status === '待支付') return 'warning';
  if (detail.value.status === '已发货') return 'info';
  if (['已取消', '已退款'].includes(detail.value.status)) return 'muted';
  return 'success';
});

const statusIcon = computed(() => ({
  待支付: '¥',
  待发货: '✓',
  已发货: '→',
  已完成: '✓',
  已取消: '×',
  已退款: '↩'
}[detail.value.status] || '·'));

const statusHint = computed(() => ({
  待支付: '请在订单关闭前完成支付',
  待发货: '支付成功，商家正在备货',
  已发货: '商品已发出，请留意物流更新',
  已完成: '订单已完成',
  已取消: '订单已取消',
  已退款: '款项已原路退回'
}[detail.value.status] || '订单状态已更新'));

function money(value) {
  return formatMoney(value, { withThousands: false });
}

function normalizeSteps(timeline = []) {
  if (!Array.isArray(timeline)) return [];
  return timeline.map((item, index) => ({
    title: item.title || item.name || `进度 ${index + 1}`,
    time: formatDateTime(item.time || item.created_at),
    active: item.active ?? true
  }));
}

function queryValue(value) {
  if (Array.isArray(value)) return value[value.length - 1];
  return value;
}

function normalizePaymentProvider(value = '') {
  const normalized = String(value || '').trim().toLowerCase();
  if (['wxpay', 'wechat', 'wechatpay', 'weixin', 'wx', '微信'].includes(normalized)) return 'wxpay';
  if (['alipay', 'ali_pay', 'ali', '支付宝'].includes(normalized)) return 'alipay';
  return normalized;
}

function paymentProviderLabel(value = '') {
  const provider = normalizePaymentProvider(value);
  if (provider === 'wxpay') return '微信';
  if (provider === 'alipay') return '支付宝';
  return '在线';
}

function normalizePayChannel(value = '') {
  const normalized = String(value || '').trim().toUpperCase();
  if (['WXPAY', 'WECHAT', 'WECHATPAY', 'WEIXIN', 'WX'].includes(normalized)) return 'WECHAT';
  if (['ALIPAY', 'ALI_PAY', 'ALI'].includes(normalized)) return 'ALIPAY';
  if (normalized === 'BALANCE') return 'BALANCE';
  return value || '';
}

function payChannelLabel(value = '') {
  const channel = normalizePayChannel(value);
  if (channel === 'WECHAT') return '微信';
  if (channel === 'ALIPAY') return '支付宝';
  if (channel === 'BALANCE') return '余额';
  if (channel === 'VOUCHER') return '消费金';
  return '在线支付';
}

function paymentChannelValues(options = []) {
  return (Array.isArray(options) ? options : [])
    .map((item) => {
      if (typeof item === 'string') return { value: item, available: true };
      return {
        value: item?.value || item?.channel || item?.pay_channel || '',
        available: item?.available !== false
      };
    })
    .filter((item) => item.value && item.available)
    .map((item) => normalizePayChannel(item.value));
}

function findPaymentCombo(assetDeductions = [], payableAmount = 0, payStatus = '', payChannel = '') {
  const types = new Set((assetDeductions || []).map((item) => item.asset_type));
  if (types.has('BALANCE') && types.has('POINTS')) return '余额 + 积分';
  if (types.has('VOUCHER') && types.has('POINTS')) return '消费金 + 积分';
  if (types.has('POINTS') && Number(payableAmount || 0) > 0) return `${payChannelLabel(payChannel)} + 积分`;
  if (types.has('BALANCE')) return '余额支付';
  if (types.has('VOUCHER')) return '消费金支付';
  if (payStatus === 'PAID') return payChannelLabel(payChannel);
  return '待支付';
}

function paymentLabel(status, providedLabel, assetDeductions, payableAmount, payStatus, payChannel) {
  if (status === '已退款') return '已退款';
  if (status === '已取消') return '订单已取消';
  return providedLabel || findPaymentCombo(assetDeductions, payableAmount, payStatus, payChannel);
}

function preferredPayChannel(options = [], cashDue = 0, fallback = '') {
  const values = paymentChannelValues(options);
  if (Number(cashDue || 0) > 0) {
    const externalChannel = values.find((item) => ['ALIPAY', 'WECHAT'].includes(item));
    if (externalChannel) return externalChannel;
  }
  return normalizePayChannel(fallback) || values[0] || '';
}

function normalize(res = {}) {
  const order = res?.order || res || {};
  // Payment-status responses wrap the full serialized order in `order`,
  // while the detail endpoint returns its item arrays at the top level.
  // Accept both shapes so a provider return does not blank the detail view.
  const items = Array.isArray(res?.items)
    ? res.items
    : (Array.isArray(order?.items) ? order.items : []);
  const deductions = Array.isArray(res?.asset_deductions)
    ? res.asset_deductions
    : (Array.isArray(order?.asset_deductions) ? order.asset_deductions : []);
  const payableAmount = Number(order?.payable_amount ?? order?.cash_due ?? 0);
  const totalAmount = Number(order?.total_amount ?? order?.amount ?? 0);
  const discountAmount = Number(order?.discount_amount ?? 0);
  const payStatus = order?.pay_status || 'UNPAID';
  const status = order?.status_text || order?.order_status || order?.status || '处理中';
  const paidAmount = Number(order?.paid_amount ?? (payStatus === 'PAID' ? totalAmount : 0));
  const payChannelOptions = Array.isArray(res?.pay_channel_options)
    ? res.pay_channel_options
    : (Array.isArray(order?.pay_channel_options) ? order.pay_channel_options : []);
  const payChannel = normalizePayChannel(
    order?.pay_channel
      || order?.payChannel
      || res?.pay_channel
      || res?.payChannel
      || res?.default_pay_channel
      || order?.default_pay_channel
      || ''
  ) || preferredPayChannel(payChannelOptions, payableAmount);

  return {
    status,
    no: order?.order_no || order?.no || '--',
    totalAmount: money(totalAmount),
    discountAmount: money(discountAmount),
    cashDue: money(payableAmount),
    paidAmount: money(paidAmount),
    payStatusCode: payStatus,
    paymentCombo: paymentLabel(
      status,
      res?.payment_combo || order?.payment_combo,
      deductions,
      payableAmount,
      payStatus,
      payChannel
    ),
    channel: order?.channel_text || order?.channel || '商城订单',
    createdAt: formatDateTime(order?.created_at),
    paidAt: formatDateTime(order?.paid_at),
    steps: normalizeSteps(order?.timeline || order?.steps || res?.timeline || res?.steps),
    items,
    payChannel,
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

async function loadDetail({ silent = false } = {}) {
  if (!id.value) {
    failed.value = true;
    errorMessage.value = '缺少订单编号，请返回订单列表重试';
    loading.value = false;
    return false;
  }
  if (!silent) loading.value = true;
  failed.value = false;
  try {
    detail.value = normalize(await orderApi.detail(id.value));
    if (!paymentProvider.value && detail.value.payChannel) {
      paymentProvider.value = normalizePaymentProvider(detail.value.payChannel);
    }
    return true;
  } catch (error) {
    failed.value = true;
    errorMessage.value = error?.message || '订单不存在或网络暂时不可用';
    return false;
  } finally {
    if (!silent) loading.value = false;
  }
}

function wait(duration) {
  return new Promise((resolve) => setTimeout(resolve, duration));
}

async function syncReturnedPayment() {
  if (!id.value || !outTradeNo.value) return false;
  syncing.value = true;
  paymentResultTone.value = 'pending';
  const returnParams = paymentProvider.value === 'alipay' ? alipayReturnParams.value : null;
  const syncChannel = paymentProvider.value === 'wxpay'
    ? 'WECHAT'
    : paymentProvider.value === 'alipay' ? 'ALIPAY' : '';
  const providerLabel = paymentProviderLabel(paymentProvider.value);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const result = await orderApi.syncPayment(id.value, outTradeNo.value, returnParams, syncChannel);
      if (result?.order || result?.status || result?.order_status) {
        detail.value = normalize(result);
      }
      if (result?.payment_status === 'PAID' || detail.value.payStatusCode === 'PAID') {
        paymentResultMessage.value = '支付成功，订单状态已更新';
        paymentResultTone.value = 'success';
        syncing.value = false;
        return true;
      }
      const providerStatus = String(result?.provider_status || '').toUpperCase();
      if (['TRADE_CLOSED', 'CLOSED', 'PAYERROR', 'FAIL', 'FAILED'].includes(providerStatus)) {
        paymentResultMessage.value = '该笔支付已关闭，可重新发起支付';
        paymentResultTone.value = 'warning';
        syncing.value = false;
        return true;
      }
      if (['WAIT_BUYER_PAY', 'NOTPAY', 'USERPAYING', 'PENDING'].includes(providerStatus)) {
        paymentResultMessage.value = `${providerLabel}支付结果暂未确认，请稍后刷新订单`;
        paymentResultTone.value = 'warning';
      }
    } catch (error) {
      if (attempt === 2) {
        paymentResultMessage.value = `${providerLabel}支付结果暂未同步，请稍后刷新订单`;
        paymentResultTone.value = 'warning';
      }
    }
    if (attempt < 2) await wait(1200);
  }
  syncing.value = false;
  // Always let initialize() load the order after a failed sync. Otherwise the
  // page stays on its placeholder state (amount/order number shown as --).
  return false;
}

async function initialize() {
  loading.value = true;
  const synced = await syncReturnedPayment();
  if (!synced) {
    const loaded = await loadDetail({ silent: true });
    if (loaded && detail.value.canPay) {
      try {
        const result = await orderApi.syncPayment(id.value, '', null, detail.value.payChannel);
        if (result?.provider_status !== 'NO_TRANSACTION' && (result?.order || result?.status || result?.order_status)) {
          detail.value = normalize(result);
        }
        if (result?.payment_status === 'PAID') {
          uni.showToast({ title: '支付状态已更新', icon: 'success' });
        }
      } catch (error) {
        // The order remains usable even when the provider status check is temporarily unavailable.
      }
    }
  }
  loading.value = false;
}

function goBack() {
  if (returnedFromPayment.value) {
    uni.reLaunch({ url: '/pages/orders/list' });
    return;
  }
  uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/orders/list' }) });
}

function copyOrderNo() {
  if (!detail.value.no || detail.value.no === '--') return;
  uni.setClipboardData({ data: detail.value.no });
}

async function payOrder() {
  if (paying.value) return;
  paying.value = true;
  try {
    const payChannel = detail.value.payChannel || detail.value.payChannelOptions?.[0];
    if (!payChannel) {
      uni.showToast({ title: '当前订单暂无可用支付方式', icon: 'none' });
      return;
    }
    const result = await orderApi.pay(id.value, { pay_channel: payChannel, auto_complete: true });
    const payment = result?.payment;
    if (payment?.status === 'FAILED') {
      throw new Error(payment.message || '支付参数创建失败');
    }
    if (payment?.status === 'PAID') {
      uni.showToast({ title: '支付完成', icon: 'success' });
      await loadDetail({ silent: true });
      return;
    }
    paymentProvider.value = normalizePaymentProvider(payment?.provider || payChannel);
    const platformResult = await requestPlatformPayment(payment);
    if (platformResult?.redirected) return;
    if (payment?.out_trade_no) {
      outTradeNo.value = payment.out_trade_no;
      await syncReturnedPayment();
    } else {
      await loadDetail({ silent: true });
    }
  } catch (error) {
    const message = String(error?.errMsg || error?.message || '');
    uni.showToast({ title: message.includes('cancel') ? '已取消支付' : '支付未完成', icon: 'none' });
  } finally {
    paying.value = false;
  }
}

async function confirmOrder() {
  await orderApi.confirm(id.value);
  uni.showToast({ title: '已确认收货', icon: 'success' });
  await loadDetail({ silent: true });
}

function cancelOrder() {
  uni.showModal({
    title: '取消订单',
    content: '取消后库存和已抵扣资产将自动退回。',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.cancel(id.value);
      uni.showToast({ title: '订单已取消', icon: 'success' });
      await loadDetail({ silent: true });
    }
  });
}

function refundOrder() {
  uni.showModal({
    title: '申请退款',
    content: '退款后库存和已抵扣资产将自动退回。',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await orderApi.refund(id.value);
      uni.showToast({ title: '退款已提交', icon: 'success' });
      await loadDetail({ silent: true });
    }
  });
}

const ALIPAY_RETURN_FIELDS = [
  'charset',
  'out_trade_no',
  'method',
  'total_amount',
  'trade_status',
  'sign',
  'trade_no',
  'auth_app_id',
  'version',
  'app_id',
  'sign_type',
  'seller_id',
  'timestamp'
];

function extractAlipayReturnParams(query = {}, provider = '') {
  if (provider && provider !== 'alipay') return null;
  const params = {};
  ALIPAY_RETURN_FIELDS.forEach((field) => {
    const value = queryValue(query[field]);
    if (value !== undefined && value !== null && value !== '') params[field] = String(value);
  });
  return params.sign && params.out_trade_no ? params : null;
}

onLoad((query) => {
  id.value = queryValue(query?.id || query?.order_id || '');
  const queryProvider = normalizePaymentProvider(queryValue(
    query?.provider || query?.payment_provider || query?.pay_provider || query?.pay_channel
  ));
  alipayReturnParams.value = extractAlipayReturnParams(query, queryProvider);
  paymentProvider.value = queryProvider || (alipayReturnParams.value ? 'alipay' : '');
  outTradeNo.value = queryValue(
    alipayReturnParams.value?.out_trade_no || query?.out_trade_no || query?.outTradeNo || ''
  );
  trackPageView('order_detail_view', {
    id: id.value,
    payment_return: Boolean(outTradeNo.value),
    payment_provider: paymentProvider.value || undefined
  });
  initialize();
});
</script>

<style scoped>
@import '@/styles/common.css';

.detail-page {
  min-height: 100vh;
  background: #F6F7F8;
  padding-bottom: calc(40rpx + env(safe-area-inset-bottom));
}

.detail-page.has-actions {
  padding-bottom: calc(144rpx + env(safe-area-inset-bottom));
}

.page-header {
  display: grid;
  grid-template-columns: 64rpx 1fr 64rpx;
  align-items: center;
  min-height: 88rpx;
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

.header-title {
  text-align: center;
  color: #18181B;
  font-size: 32rpx;
  font-weight: 700;
}

.status-panel {
  display: flex;
  align-items: center;
  gap: 24rpx;
  min-height: 176rpx;
  padding: 32rpx 40rpx;
  color: #FFFFFF;
  box-sizing: border-box;
}

.status-panel.success { background: #07845D; }
.status-panel.warning { background: #C26116; }
.status-panel.info { background: #2563A8; }
.status-panel.muted { background: #60646C; }

.status-symbol {
  width: 76rpx;
  height: 76rpx;
  flex: 0 0 76rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid rgba(255, 255, 255, 0.65);
  border-radius: 50%;
  font-size: 38rpx;
  font-weight: 700;
}

.status-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.status-title {
  font-size: 38rpx;
  font-weight: 700;
}

.status-description {
  color: rgba(255, 255, 255, 0.86);
  font-size: 25rpx;
}

.payment-result {
  display: flex;
  align-items: center;
  gap: 16rpx;
  min-height: 72rpx;
  padding: 16rpx 28rpx;
  border-bottom: 1rpx solid transparent;
  box-sizing: border-box;
}

.payment-result.pending { color: #1D4E89; background: #EAF3FF; border-color: #D5E7FC; }
.payment-result.success { color: #076045; background: #E8F8F1; border-color: #CBECDD; }
.payment-result.warning { color: #8A4310; background: #FFF3E8; border-color: #F3DDC9; }

.payment-result-text {
  font-size: 25rpx;
  font-weight: 600;
}

.sync-spinner {
  width: 24rpx;
  height: 24rpx;
  flex: 0 0 24rpx;
  border: 3rpx solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.content-stack {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  padding: 20rpx;
}

.section-card {
  padding: 28rpx;
  background: #FFFFFF;
  border: 1rpx solid #E8EAED;
  border-radius: 16rpx;
  box-sizing: border-box;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 24rpx;
}

.section-title {
  display: block;
  color: #18181B;
  font-size: 29rpx;
  font-weight: 700;
}

.section-meta,
.section-link {
  color: #71717A;
  font-size: 23rpx;
}

.section-link {
  color: #047857;
}

.contact-line {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}

.contact-name {
  color: #18181B;
  font-size: 28rpx;
  font-weight: 700;
}

.contact-phone,
.address-text,
.empty-line {
  color: #71717A;
  font-size: 25rpx;
}

.address-text,
.empty-line {
  display: block;
  margin-top: 12rpx;
  line-height: 1.55;
}

.logistics-line {
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
  margin-top: 22rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid #ECEEF0;
  color: #3F3F46;
  font-size: 24rpx;
}

.goods-row {
  display: grid;
  grid-template-columns: 104rpx minmax(0, 1fr) auto;
  gap: 18rpx;
  align-items: center;
  padding: 20rpx 0;
  border-top: 1rpx solid #ECEEF0;
}

.section-heading + .goods-row {
  padding-top: 0;
  border-top: 0;
}

.goods-row:last-child {
  padding-bottom: 0;
}

.goods-image {
  width: 104rpx;
  height: 104rpx;
  border-radius: 12rpx;
  background: #F0F2F3;
}

.goods-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  font-size: 32rpx;
  font-weight: 700;
}

.goods-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.goods-title {
  color: #27272A;
  font-size: 27rpx;
  font-weight: 600;
  line-height: 1.4;
}

.goods-spec,
.goods-quantity {
  color: #85858D;
  font-size: 23rpx;
}

.goods-subtotal {
  align-self: start;
  color: #27272A;
  font-size: 26rpx;
  font-weight: 700;
}

.amount-section > .section-title,
.order-section > .section-title,
.timeline-section > .section-title {
  margin-bottom: 20rpx;
}

.amount-row,
.payment-method,
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  min-height: 64rpx;
  color: #71717A;
  font-size: 25rpx;
}

.amount-row > text:last-child,
.payment-method > text:last-child {
  color: #27272A;
}

.amount-row.discount > text:last-child {
  color: #047857;
}

.amount-row.total {
  min-height: 80rpx;
  margin-top: 10rpx;
  padding-top: 14rpx;
  border-top: 1rpx solid #E5E7EB;
  color: #18181B;
  font-weight: 700;
}

.total-price {
  color: #D55312 !important;
  font-size: 34rpx;
  font-weight: 800;
}

.payment-method {
  margin-top: 6rpx;
  padding-top: 14rpx;
  border-top: 1rpx solid #F0F1F2;
}

.info-row {
  border-top: 1rpx solid #F0F1F2;
}

.order-section > .section-title + .info-row {
  border-top: 0;
}

.info-value-wrap {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12rpx;
}

.info-value {
  max-width: 70%;
  color: #3F3F46;
  text-align: right;
  word-break: break-all;
}

.order-no {
  max-width: 440rpx;
  font-size: 23rpx;
}

.copy-text {
  flex-shrink: 0;
  color: #047857;
  font-size: 22rpx;
}

.timeline-row {
  display: grid;
  grid-template-columns: 24rpx minmax(0, 1fr);
  gap: 18rpx;
  min-height: 88rpx;
}

.timeline-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.timeline-dot {
  width: 16rpx;
  height: 16rpx;
  flex: 0 0 16rpx;
  margin-top: 8rpx;
  background: #D4D4D8;
  border-radius: 50%;
}

.timeline-dot.active {
  background: #07845D;
  box-shadow: 0 0 0 5rpx #E3F4ED;
}

.timeline-line {
  width: 2rpx;
  flex: 1;
  margin-top: 8rpx;
  background: #E4E4E7;
}

.timeline-copy {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding-bottom: 24rpx;
}

.timeline-title {
  color: #71717A;
  font-size: 26rpx;
  font-weight: 600;
}

.timeline-title.active {
  color: #27272A;
}

.timeline-time {
  color: #8B8B93;
  font-size: 22rpx;
}

.action-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: flex;
  justify-content: flex-end;
  gap: 16rpx;
  min-height: 108rpx;
  padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.96);
  border-top: 1rpx solid #E5E7EB;
  box-sizing: content-box;
}

.action-button {
  min-width: 176rpx;
  height: 76rpx;
  margin: 0;
  padding: 0 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  font-size: 27rpx;
  font-weight: 700;
  line-height: 1;
}

.action-button::after,
.retry-button::after {
  border: 0;
}

.action-button.primary {
  color: #FFFFFF;
  background: #07845D;
}

.action-button.secondary {
  color: #3F3F46;
  background: #FFFFFF;
  border: 1rpx solid #D4D4D8;
}

.action-button[disabled] {
  opacity: 0.55;
}

.loading-state {
  padding: 24rpx;
}

.skeleton {
  background: #E9EBED;
  border-radius: 16rpx;
  animation: pulse 1.4s ease-in-out infinite;
}

.status-skeleton { height: 176rpx; }
.content-skeleton { height: 240rpx; margin-top: 20rpx; }
.content-skeleton.short { height: 160rpx; }

.error-state {
  min-height: 70vh;
  padding: 48rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.error-mark {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #A33A34;
  background: #FBE9E7;
  border-radius: 50%;
  font-size: 38rpx;
  font-weight: 800;
}

.error-title {
  margin-top: 24rpx;
  color: #27272A;
  font-size: 30rpx;
  font-weight: 700;
}

.error-description {
  margin-top: 10rpx;
  color: #71717A;
  font-size: 25rpx;
}

.retry-button {
  height: 72rpx;
  margin-top: 28rpx;
  padding: 0 32rpx;
  color: #FFFFFF;
  background: #07845D;
  border-radius: 12rpx;
  font-size: 26rpx;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 0.65; }
  50% { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .sync-spinner,
  .skeleton {
    animation: none;
  }
}
</style>
