<template>
  <view class="container detail-page">
    <view v-if="loading" class="card state-card">加载中...</view>
    <view v-else-if="failed" class="card state-card">
      <view>订单详情加载失败</view>
      <button class="btn btn-ghost retry-btn mt-16" @click="loadDetail">重试</button>
    </view>
    <template v-else>
      <view class="card head-card">
        <view class="head-tag">订单中心</view>
        <view class="row-between mt-12">
          <view class="section-title no-margin">订单详情</view>
          <view class="badge" :class="badgeClass">{{ detail.status }}</view>
        </view>
        <view class="muted mt-8">订单号：{{ detail.no }}</view>
        <view class="price-row mt-16">
          <view>
            <view class="price-label">订单总额</view>
            <view class="price">¥{{ detail.amount }}</view>
          </view>
          <view class="pay-status-pill">{{ detail.payStatus }}</view>
        </view>

        <view class="service-strip mt-16">
          <view class="service-pill">{{ detail.channel }}</view>
          <view class="service-pill">{{ detail.paymentCombo }}</view>
        </view>
      </view>

      <view class="card mt-20 info-card">
        <view class="section-title">支付信息</view>
        <view class="info-row">
          <text>支付组合</text>
          <text>{{ detail.paymentCombo }}</text>
        </view>
        <view class="info-row">
          <text>商品总额</text>
          <text>¥{{ detail.totalAmount }}</text>
        </view>
        <view class="info-row">
          <text>资产抵扣</text>
          <text>-¥{{ detail.discountAmount }}</text>
        </view>
        <view class="info-row strong">
          <text>待支付金额</text>
          <text>¥{{ detail.cashDue }}</text>
        </view>
        <view v-if="detail.paymentMessage" class="payment-note">{{ detail.paymentMessage }}</view>
      </view>

      <view class="card mt-20" v-if="detail.items.length">
        <view class="section-title">订单商品</view>
        <view v-for="item in detail.items" :key="item.id" class="goods-row">
          <view class="goods-title">{{ item.product_name }}</view>
          <view class="goods-meta">数量 {{ item.quantity }} / 单价 ¥{{ item.unit_price }}</view>
          <view class="goods-meta">小计 ¥{{ item.total_amount }}</view>
        </view>
      </view>

      <view class="card mt-20" v-if="detail.steps.length">
        <view class="section-title">进度轨迹</view>
        <view class="timeline" v-for="item in detail.steps" :key="`${item.title}-${item.time}`">
          <view class="dot" :class="{ active: item.active }" />
          <view>
            <view class="t-title">{{ item.title }}</view>
            <view class="t-time">{{ item.time }}</view>
          </view>
        </view>
      </view>

      <view class="action-wrap mt-24">
        <button v-if="detail.canPay" class="btn btn-primary action-btn" @click="payOrder">{{ paying ? '支付中...' : '继续支付' }}</button>
        <button v-if="detail.canConfirm" class="btn btn-ghost action-btn" @click="confirmOrder">确认完成</button>
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
  payChannel: '',
  payChannelOptions: []
});

const badgeClass = computed(() => {
  if (detail.value.status === '已完成') return 'badge-green';
  if (detail.value.status === '已支付') return 'badge-blue';
  return 'badge-orange';
});

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
    payStatus: payStatus === 'PAID' ? '已支付' : '未支付',
    paymentCombo: res?.payment_combo || order?.payment_combo || findPaymentCombo(deductions, payableAmount, payStatus),
    paymentMessage: res?.payment_message || (payableAmount > 0 ? '微信支付、支付宝支付接口已预留，当前使用模拟完成支付。' : '订单已完成支付。'),
    channel: order?.channel_text || order?.channel || '商城订单',
    steps: normalizeSteps(order?.timeline || order?.steps || res?.timeline || res?.steps),
    items,
    payChannel: res?.default_pay_channel || order?.default_pay_channel || payChannelOptions[0] || '',
    payChannelOptions,
    canPay: Boolean(order?.can_pay ?? res?.can_pay ?? payStatus !== 'PAID'),
    canConfirm: Boolean(order?.can_confirm ?? res?.can_confirm ?? (payStatus === 'PAID' && orderStatus !== '已完成' && order?.order_type !== 'LOCAL_LIFE_ORDER'))
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

onLoad((query) => {
  id.value = query?.id || '';
  trackPageView('order_detail_view', { id: id.value });
  loadDetail();
});
</script>

<style scoped>
@import '@/styles/common.css';

.detail-page { padding-bottom: 36rpx; }
.head-card {
  background:
    radial-gradient(circle at 96% 8%, rgba(255, 166, 82, 0.18), transparent 38%),
    linear-gradient(180deg, #fffdf9 0%, #fff6ec 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.16);
  position: relative;
  overflow: hidden;
}
.head-card::after {
  content: '';
  position: absolute;
  right: -30rpx;
  top: -30rpx;
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background: rgba(255, 122, 0, 0.08);
}
.head-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.no-margin { margin-bottom: 0; }
.price-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16rpx;
}
.price-label { font-size: 22rpx; color: #8b7158; }
.price { font-size: 42rpx; color: #ff6a00; font-weight: 900; }
.pay-status-pill {
  padding: 10rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 122, 0, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 700;
}
.service-strip { display: flex; flex-wrap: wrap; gap: 10rpx; }
.service-pill { padding: 6rpx 12rpx; border-radius: 999rpx; background: #fbf3ea; color: #9f6736; font-size: 20rpx; }
.info-card { border: 1rpx solid rgba(255, 154, 106, 0.16); }
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 16rpx;
  font-size: 24rpx;
  color: #6b4a2f;
}
.info-row.strong { color: #ff6a00; font-weight: 800; }
.payment-note {
  margin-top: 18rpx;
  padding: 18rpx;
  border-radius: 18rpx;
  background: #fff6eb;
  color: #8b7158;
  font-size: 22rpx;
  line-height: 1.5;
}
.goods-row {
  margin-top: 16rpx;
  padding: 18rpx;
  border-radius: 18rpx;
  background: linear-gradient(180deg, #fffaf7, #fff2e8);
  border: 1rpx solid rgba(255, 154, 106, 0.12);
}
.goods-title { font-size: 26rpx; color: #4f321a; font-weight: 800; }
.goods-meta { margin-top: 8rpx; color: #8b7158; font-size: 22rpx; }
.timeline { display: flex; gap: 12rpx; margin-top: 16rpx; }
.dot { width: 16rpx; height: 16rpx; border-radius: 50%; background: #e6cfb6; margin-top: 10rpx; }
.dot.active { background: #ff6a00; }
.t-title { font-size: 26rpx; color: #4f321a; }
.t-time { margin-top: 4rpx; color: #8b7158; font-size: 22rpx; }
.action-wrap { display: flex; gap: 16rpx; }
.action-btn { flex: 1; }
.state-card { text-align: center; }
.retry-btn { width: 180rpx; }
</style>
