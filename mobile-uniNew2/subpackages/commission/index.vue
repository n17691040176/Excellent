<template>
  <view class="container commission-page">
    <view class="card summary-card">
      <view class="summary-tag">佣金中心</view>
      <view class="section-title mt-12">收益趋势与结算进度实时同步</view>
      <view class="muted">查看可提现金额、历史收益和结算状态，提现操作更直观</view>

      <view class="summary-main mt-20">
        <view>
          <view class="summary-label">可提现金额</view>
          <view class="num">¥{{ withdrawable }}</view>
        </view>
        <button class="btn btn-primary withdraw-btn" @click="withdraw">立即提现</button>
      </view>

      <view class="summary-strip mt-20">
        <view class="summary-chip">
          <view class="chip-value">{{ list.length }}</view>
          <view class="chip-label">收益记录</view>
        </view>
        <view class="summary-chip">
          <view class="chip-value">{{ settledCount }}</view>
          <view class="chip-label">已结算</view>
        </view>
        <view class="summary-chip">
          <view class="chip-value">{{ pendingCount }}</view>
          <view class="chip-label">待结算</view>
        </view>
      </view>
    </view>

    <StateView v-if="loading" title="加载中..." custom-class="mt-24" />
    <StateView v-else-if="failed" title="佣金记录加载失败" :show-retry="true" custom-class="mt-24" @retry="loadCommission" />
    <StateView v-else-if="!list.length" title="暂无佣金记录" description="产生收益后会同步展示结算进度" custom-class="mt-24" />

    <view v-else class="record-list mt-24">
      <view class="card record-card" v-for="item in list" :key="item.id">
        <view class="row-between record-top">
          <view>
            <view class="name">{{ item.name }}</view>
            <view class="muted mt-8">{{ item.time }}</view>
          </view>
          <view class="badge" :class="item.status === '已结算' ? 'badge-green' : 'badge-orange'">{{ item.status }}</view>
        </view>
        <view class="record-bottom mt-16">
          <view class="record-desc">{{ item.desc || '收益入账记录' }}</view>
          <view class="income">+¥{{ item.amount }}</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { commissionApi } from '@/api/modules';
import { pickListPayload, toCommissionFlows } from '@/utils/adapters';

const loading = ref(false);
const failed = ref(false);
const withdrawable = ref('0.00');
const list = ref([]);

const settledCount = computed(() => list.value.filter((item) => item.status === '已结算').length);
const pendingCount = computed(() => list.value.filter((item) => item.status !== '已结算').length);

const loadCommission = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const [summaryRes, flowsRes] = await Promise.allSettled([
      commissionApi.summary(),
      commissionApi.flows({ page: 1, page_size: 20 })
    ]);

    if (summaryRes.status === 'fulfilled') {
      withdrawable.value = summaryRes.value?.withdrawable_amount ?? summaryRes.value?.available_amount ?? '0.00';
    }
    if (flowsRes.status === 'fulfilled') {
      list.value = toCommissionFlows(pickListPayload(flowsRes.value));
    }
    if (summaryRes.status === 'rejected' && flowsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const withdraw = async () => {
  const amount = Number(withdrawable.value) || 0;
  if (amount <= 0) {
    uni.showToast({ title: '暂无可提现佣金', icon: 'none' });
    return;
  }
  try {
    await commissionApi.createWithdraw({
      withdraw_type: 'COMMISSION',
      amount
    });
    uni.showToast({ title: '提现申请已提交', icon: 'none' });
    loadCommission();
  } catch (error) {
    // 请求层统一提示
  }
};

onShow(() => {
  loadCommission();
});

onPullDownRefresh(async () => {
  await loadCommission();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';
.commission-page { padding-bottom: 36rpx; }
.summary-card {
  background:
    radial-gradient(circle at 95% 8%, rgba(255, 166, 82, 0.16), transparent 36%),
    linear-gradient(180deg, #fffdf9 0%, #fff5eb 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.18);
  position: relative;
  overflow: hidden;
}
.summary-card::after {
  content: '';
  position: absolute;
  right: -30rpx;
  top: -30rpx;
  width: 150rpx;
  height: 150rpx;
  border-radius: 50%;
  background: rgba(255, 122, 0, 0.08);
}
.summary-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.summary-main {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16rpx;
}
.summary-label { font-size: 22rpx; color: #8b7158; }
.num { margin-top: 6rpx; font-size: 48rpx; color: #ff6a00; font-weight: 900; }
.withdraw-btn { width: 200rpx; padding: 0; }
.summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
}
.summary-chip {
  padding: 14rpx 12rpx;
  border-radius: 18rpx;
  background: rgba(255, 255, 255, 0.72);
  border: 1rpx solid rgba(255, 154, 106, 0.12);
}
.chip-value { font-size: 30rpx; font-weight: 900; color: #4f321a; }
.chip-label { margin-top: 4rpx; font-size: 20rpx; color: #8b7158; }
.record-list { display: grid; gap: 14rpx; }
.record-card { border: 1rpx solid rgba(255, 154, 106, 0.16); border-radius: 24rpx; }
.record-top { align-items: flex-start; }
.name { font-size: 28rpx; color: #4f321a; font-weight: 800; }
.record-bottom { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; }
.record-desc { font-size: 22rpx; color: #8b7158; }
.income { color: #ff6a00; font-size: 30rpx; font-weight: 800; }
.state-card { text-align: center; }
.retry-btn { width: 180rpx; }
</style>
