<template>
  <view class="container feature-page">
    <view class="card hero-card">
      <view class="hero-tag">快递服务</view>
      <view class="section-title mt-12">统一查看运输进度、单号和签收状态</view>
      <view class="muted">已支付且需要发货的订单，会在这里展示运输进度</view>
    </view>

    <StateView v-if="loading" title="快递加载中..." custom-class="mt-24" />
    <StateView v-else-if="failed" title="快递加载失败" :show-retry="true" custom-class="mt-24" @retry="loadData" />
    <StateView
      v-else-if="!items.length"
      title="暂无快递包裹"
      description="已支付且需要发货的订单，会在这里展示运输进度。"
      custom-class="mt-24"
    />

    <template v-else>
      <view class="card summary-card mt-24">
        <view class="row-between">
          <view>
            <view class="section-title summary-title">快递服务</view>
            <view class="summary-subtitle">统一查看运输进度、单号和签收状态</view>
          </view>
          <view class="badge badge-blue">实时同步</view>
        </view>

        <view class="summary-grid mt-20">
          <view class="summary-item">
            <view class="summary-num">{{ items.length }}</view>
            <view class="summary-label">全部包裹</view>
          </view>
          <view class="summary-item">
            <view class="summary-num">{{ shippingCount }}</view>
            <view class="summary-label">运输中</view>
          </view>
          <view class="summary-item">
            <view class="summary-num">{{ deliveredCount }}</view>
            <view class="summary-label">已签收</view>
          </view>
        </view>
      </view>

      <view class="status-wrap mt-20">
        <view
          v-for="tab in tabs"
          :key="tab.value"
          class="status-chip interactive"
          :class="{ active: activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </view>
      </view>

      <StateView
        v-if="!filteredItems.length"
        title="当前筛选下暂无包裹"
        description="可以切换筛选条件，查看其他运输状态。"
        custom-class="mt-20"
      />

      <view v-else class="card-list mt-20">
        <view v-for="item in filteredItems" :key="item.order_id" class="card ship-card interactive" @click="goDetail(item.order_id)">
          <view class="row-between">
            <view class="ship-company">{{ item.carrier_name }}</view>
            <view class="badge" :class="item.status === 'delivered' ? 'badge-green' : 'badge-blue'">{{ item.status_text }}</view>
          </view>

          <view class="ship-title">{{ item.title }}</view>
          <view class="ship-hint">{{ item.status_hint }}</view>

          <view class="progress-track">
            <view class="progress-fill" :style="{ width: `${item.progress_percent || 0}%` }"></view>
          </view>

          <view class="ship-message">{{ item.latest_message }}</view>

          <view class="meta-grid">
            <view class="ship-meta">单号 {{ item.tracking_no }}</view>
            <view class="ship-meta">{{ item.delivery_mode_text }}</view>
            <view class="ship-meta">更新时间 {{ formatTime(item.updated_at) }}</view>
          </view>

          <view class="ship-actions">
            <button class="btn btn-ghost mini-btn" @click.stop="copyTracking(item.tracking_no)">复制单号</button>
            <button v-if="item.carrier_phone" class="btn btn-ghost mini-btn" @click.stop="callPhone(item.carrier_phone)">联系商家</button>
            <button class="btn btn-primary mini-btn" @click.stop="goDetail(item.order_id)">查看详情</button>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const tabs = [
  { label: '全部', value: 'all' },
  { label: '运输中', value: 'shipping' },
  { label: '已签收', value: 'delivered' }
];

const loading = ref(false);
const failed = ref(false);
const items = ref([]);
const activeTab = ref('all');

const shippingCount = computed(() => items.value.filter((item) => item.status === 'shipping').length);
const deliveredCount = computed(() => items.value.filter((item) => item.status === 'delivered').length);

const filteredItems = computed(() => {
  if (activeTab.value === 'all') return items.value;
  return items.value.filter((item) => item.status === activeTab.value);
});

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const res = await commerceApi.shipments();
    items.value = pickListPayload(res);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

function copyTracking(trackingNo) {
  if (!trackingNo) return;
  uni.setClipboardData({
    data: trackingNo,
    success: () => uni.showToast({ title: '已复制单号', icon: 'none' })
  });
}

function callPhone(phone) {
  if (!phone) return;
  uni.makePhoneCall({ phoneNumber: String(phone) });
}

function goDetail(orderId) {
  uni.navigateTo({ url: `/subpackages/profile/shipping-detail?order_id=${orderId}` });
}

onShow(loadData);
</script>

<style scoped>
@import '@/styles/common.css';

.feature-page { padding-bottom: 36rpx; }
.hero-card {
  background:
    radial-gradient(circle at 96% 8%, rgba(94, 151, 255, 0.14), transparent 42%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.16);
}
.hero-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.summary-card {
  background:
    radial-gradient(circle at 96% 8%, rgba(94, 151, 255, 0.14), transparent 42%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
}
.summary-title {
  margin-bottom: 0;
}
.summary-subtitle {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #8b7158;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
}
.summary-item {
  padding: 16rpx;
  border-radius: 18rpx;
  background: #fcf6ef;
  border: 1rpx solid rgba(198, 161, 124, 0.14);
}
.summary-num {
  font-size: 34rpx;
  font-weight: 800;
  color: #4f321a;
}
.summary-label {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #8b7158;
}
.status-wrap {
  display: flex;
  gap: 12rpx;
  overflow-x: auto;
}
.status-chip {
  flex-shrink: 0;
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  background: #f6f1ea;
  color: #7f6954;
  font-size: 24rpx;
  border: 1rpx solid rgba(194, 156, 117, 0.18);
}
.status-chip.active {
  background: linear-gradient(135deg, #ff7a00, #ff5f3d);
  color: #ffffff;
  border-color: transparent;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.ship-card {
  border-radius: 24rpx;
  border: 1rpx solid rgba(255, 154, 106, 0.16);
}
.ship-company {
  font-size: 24rpx;
  color: #8b7158;
}
.ship-title {
  margin-top: 14rpx;
  font-size: 30rpx;
  font-weight: 700;
  color: #4f321a;
  line-height: 1.35;
}
.ship-hint {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #7d6753;
  line-height: 1.5;
}
.progress-track {
  margin-top: 16rpx;
  height: 10rpx;
  border-radius: 999rpx;
  overflow: hidden;
  background: #f1e4d6;
}
.progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #ff7a00, #ff5f3d);
}
.ship-message {
  margin-top: 14rpx;
  font-size: 23rpx;
  line-height: 1.5;
  color: #7d6753;
}
.meta-grid {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  margin-top: 14rpx;
}
.ship-meta {
  font-size: 21rpx;
  color: #9f8a77;
}
.ship-actions {
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
.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.98); opacity: 0.92; }
</style>
