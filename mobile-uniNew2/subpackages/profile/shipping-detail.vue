<template>
  <view class="container detail-page">
    <StateView v-if="loading" title="快递详情加载中..." />
    <StateView v-else-if="failed" title="快递详情加载失败" :show-retry="true" @retry="loadData" />

    <template v-else>
      <view class="card head-card">
        <view class="row-between">
          <view class="section-title">快递详情</view>
          <view class="badge" :class="detail.status === 'delivered' ? 'badge-green' : 'badge-blue'">{{ detail.status_text }}</view>
        </view>

        <view class="head-title">{{ detail.title }}</view>
        <view class="head-desc">{{ detail.status_hint }}</view>

        <view class="progress-track">
          <view class="progress-fill" :style="{ width: `${detail.progress_percent || 0}%` }"></view>
        </view>

        <view class="head-grid">
          <view class="head-cell">
            <view class="head-label">承运方式</view>
            <view class="head-value">{{ detail.delivery_mode_text || '--' }}</view>
          </view>
          <view class="head-cell">
            <view class="head-label">承运方</view>
            <view class="head-value">{{ detail.carrier_name || '--' }}</view>
          </view>
          <view class="head-cell">
            <view class="head-label">快递单号</view>
            <view class="head-value">{{ detail.tracking_no || '--' }}</view>
          </view>
          <view class="head-cell">
            <view class="head-label">订单编号</view>
            <view class="head-value">{{ detail.order_no || '--' }}</view>
          </view>
        </view>

        <view class="action-row">
          <button class="btn btn-ghost mini-btn" @click="copyTracking">复制单号</button>
          <button v-if="detail.carrier_phone" class="btn btn-ghost mini-btn" @click="callPhone">联系商家</button>
          <button
            v-if="detail.can_confirm"
            class="btn btn-primary mini-btn"
            :disabled="confirming"
            @click="confirmReceipt"
          >
            {{ confirming ? '确认中...' : '确认收货' }}
          </button>
        </view>
      </view>

      <view class="status-strip mt-20">
        <view class="strip-item">
          <view class="strip-title">下单时间</view>
          <view class="strip-desc">{{ formatTime(detail.created_at) }}</view>
        </view>
        <view class="strip-item">
          <view class="strip-title">最近更新</view>
          <view class="strip-desc">{{ formatTime(detail.updated_at) }}</view>
        </view>
        <view class="strip-item">
          <view class="strip-title">订单金额</view>
          <view class="strip-desc">¥{{ money(detail.amount) }}</view>
        </view>
      </view>

      <view class="card mt-24">
        <view class="section-title">物流轨迹</view>
        <view v-for="item in detail.timeline" :key="`${item.title}-${item.time}`" class="timeline">
          <view class="dot" :class="{ active: item.active }" />
          <view class="timeline-main">
            <view class="t-title">{{ item.title }}</view>
            <view class="t-time">{{ formatTime(item.time) }}</view>
          </view>
        </view>
      </view>

      <view class="card mt-20">
        <view class="section-title">包裹商品</view>
        <view v-for="item in detail.items" :key="item.id" class="goods-row">
          <view class="goods-title">{{ item.product_name }}</view>
          <view class="goods-meta">数量 x{{ item.quantity }}</view>
          <view class="goods-amount">¥{{ money(item.total_amount) }}</view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { commerceApi, orderApi } from '@/api/modules';

const orderId = ref('');
const loading = ref(false);
const failed = ref(false);
const confirming = ref(false);
const detail = ref({
  status: '',
  status_text: '',
  status_hint: '',
  title: '',
  carrier_name: '',
  carrier_phone: '',
  delivery_mode_text: '',
  tracking_no: '',
  order_no: '',
  progress_percent: 0,
  can_confirm: false,
  amount: 0,
  created_at: '',
  updated_at: '',
  timeline: [],
  items: []
});

function money(value) {
  return Number(value || 0).toFixed(2);
}

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

async function loadData() {
  if (!orderId.value) return;
  loading.value = true;
  failed.value = false;
  try {
    detail.value = await commerceApi.shipmentDetail(orderId.value);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function copyTracking() {
  if (!detail.value.tracking_no) return;
  uni.setClipboardData({
    data: detail.value.tracking_no,
    success: () => uni.showToast({ title: '已复制单号', icon: 'none' })
  });
}

function callPhone() {
  if (!detail.value.carrier_phone) return;
  uni.makePhoneCall({ phoneNumber: String(detail.value.carrier_phone) });
}

function confirmReceipt() {
  if (!detail.value.can_confirm || confirming.value) return;
  uni.showModal({
    title: '确认收货',
    content: '确认已经收到这笔订单的包裹吗？确认后将更新为已签收。',
    success: async ({ confirm }) => {
      if (!confirm) return;
      confirming.value = true;
      try {
        await orderApi.confirm(orderId.value);
        uni.showToast({ title: '已确认收货', icon: 'none' });
        await loadData();
      } finally {
        confirming.value = false;
      }
    }
  });
}

onLoad((query) => {
  orderId.value = query?.order_id || '';
  loadData();
});

onShow(() => {
  if (orderId.value) {
    loadData();
  }
});
</script>

<style scoped>
@import '@/styles/common.css';

.detail-page { padding-bottom: 36rpx; }

.head-card {
  background:
    radial-gradient(circle at 96% 8%, rgba(94, 151, 255, 0.16), transparent 42%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
}

.head-title {
  margin-top: 8rpx;
  font-size: 30rpx;
  color: #4f321a;
  font-weight: 700;
  line-height: 1.35;
}

.head-desc {
  margin-top: 12rpx;
  font-size: 22rpx;
  color: #8b7158;
  line-height: 1.5;
}

.progress-track {
  margin-top: 18rpx;
  height: 10rpx;
  border-radius: 999rpx;
  overflow: hidden;
  background: #f1e4d6;
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #4c93ff, #6ab4ff);
}

.head-grid {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.head-cell {
  padding: 16rpx;
  border-radius: 18rpx;
  background: #fcf6ef;
}

.head-label {
  font-size: 20rpx;
  color: #9b8169;
}

.head-value {
  margin-top: 8rpx;
  font-size: 24rpx;
  line-height: 1.4;
  color: #4f321a;
  word-break: break-all;
}

.action-row {
  margin-top: 18rpx;
  display: flex;
  gap: 12rpx;
}

.mini-btn {
  flex: 1;
  min-width: 0;
  height: 60rpx;
  line-height: 60rpx;
  padding: 0;
  font-size: 23rpx;
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10rpx;
}

.strip-item {
  border-radius: 14rpx;
  padding: 12rpx;
  background: linear-gradient(145deg, #fffdf9, #fbf2e7);
  border: 1rpx solid rgba(198, 161, 124, 0.16);
}

.strip-title {
  font-size: 22rpx;
  font-weight: 700;
  color: #6b4422;
}

.strip-desc {
  margin-top: 6rpx;
  font-size: 20rpx;
  color: #8b7158;
  line-height: 1.4;
}

.timeline {
  display: flex;
  gap: 12rpx;
  margin-top: 18rpx;
}

.timeline-main {
  flex: 1;
  min-width: 0;
}

.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: #e6cfb6;
  margin-top: 10rpx;
}

.dot.active { background: #2d73f5; }

.t-title {
  font-size: 26rpx;
  color: #4f321a;
}

.t-time {
  margin-top: 4rpx;
  color: #8b7158;
  font-size: 22rpx;
}

.goods-row {
  padding: 18rpx 0;
  border-bottom: 1rpx solid #efe4d7;
}

.goods-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.goods-title {
  font-size: 26rpx;
  color: #4f321a;
  font-weight: 700;
}

.goods-meta {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #8b7158;
}

.goods-amount {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #c96a14;
  font-weight: 700;
}
</style>
