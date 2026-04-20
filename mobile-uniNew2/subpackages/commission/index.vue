<template>
  <view class="container commission-page">
    <view class="card summary-card">
      <view class="section-title">佣金中心</view>
      <view class="muted">收益趋势与结算进度实时同步</view>
      <view class="row-between mt-20">
        <view>
          <view class="num">¥{{ withdrawable }}</view>
          <view class="muted">可提现</view>
        </view>
        <button class="btn btn-primary withdraw-btn" @click="withdraw">立即提现</button>
      </view>
    </view>

    <StateView v-if="loading" title="加载中..." custom-class="mt-24" />
    <StateView v-else-if="failed" title="佣金记录加载失败" :show-retry="true" custom-class="mt-24" @retry="loadCommission" />
    <StateView v-else-if="!list.length" title="暂无佣金记录" description="产生收益后会同步展示结算进度" custom-class="mt-24" />

    <view class="card mt-24" v-else v-for="item in list" :key="item.id">
      <view class="row-between">
        <view class="name">{{ item.name }}</view>
        <view class="badge" :class="item.status === '已结算' ? 'badge-green' : 'badge-orange'">{{ item.status }}</view>
      </view>
      <view class="row-between mt-16">
        <view class="muted">{{ item.time }}</view>
        <view class="income">+¥{{ item.amount }}</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { commissionApi } from '@/api/modules';
import { pickListPayload, toCommissionFlows } from '@/utils/adapters';

const loading = ref(false);
const failed = ref(false);
const withdrawable = ref('0.00');
const list = ref([]);

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
    radial-gradient(circle at 95% 8%, rgba(255, 166, 82, 0.2), transparent 40%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
  border: 1rpx solid rgba(198, 161, 124, 0.18);
}
.num { font-size: 44rpx; color: #b85d11; font-weight: 800; }
.withdraw-btn { width: 200rpx; padding: 0; }
.name { font-size: 28rpx; color: #4f321a; }
.income { color: #c96a14; font-size: 30rpx; font-weight: 700; }
.state-card { text-align: center; }
.retry-btn { width: 180rpx; }
</style>
