<template>
  <view class="container invite-page">
    <view class="card poster">
      <view class="section-title">邀请好友</view>
      <view class="muted">分享专属邀请码，跟进注册与转化结果</view>
      <view class="invite-code mt-20">邀请码：{{ inviteCode }}</view>
      <button class="btn btn-primary mt-24" @click="share">立即分享</button>
    </view>

    <view class="card mt-24">
      <view class="section-title">邀请数据</view>
      <StateView v-if="loading" title="加载中..." custom-class="mt-16" />
      <StateView v-else-if="failed" title="邀请数据加载失败" :show-retry="true" custom-class="mt-16" @retry="loadInvite" />
      <view v-else class="grid-2 mt-20">
        <view class="item">
          <view class="num">{{ stats.total }}</view>
          <view class="label">累计邀请</view>
        </view>
        <view class="item">
          <view class="num">{{ stats.valid }}</view>
          <view class="label">有效转化</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { userApi } from '@/api/modules';
import { pickListPayload, toInviteStats } from '@/utils/adapters';

const loading = ref(false);
const failed = ref(false);
const inviteCode = ref('EX2026');
const stats = ref({ total: 0, valid: 0 });

const loadInvite = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const [codeRes, recordsRes] = await Promise.allSettled([
      userApi.inviteCode(),
      userApi.inviteRecords({ page: 1, page_size: 50 })
    ]);

    if (codeRes.status === 'fulfilled') {
      inviteCode.value = codeRes.value?.invite_code || codeRes.value?.code || inviteCode.value;
    }
    if (recordsRes.status === 'fulfilled') {
      stats.value = toInviteStats(pickListPayload(recordsRes.value));
    }

    if (codeRes.status === 'rejected' && recordsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const share = () => uni.showToast({ title: '已生成分享卡片', icon: 'none' });

onShow(() => {
  loadInvite();
});

onPullDownRefresh(async () => {
  await loadInvite();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';
.invite-page { padding-bottom: 36rpx; }
.poster { background: radial-gradient(circle at 95% 10%, rgba(30,143,100,.2), transparent 40%), #fff; }
.invite-code { font-size: 30rpx; font-weight: 700; color: #1f4032; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; }
.item { border-radius: 16rpx; background: #eff6f2; padding: 14rpx; }
.num { font-size: 34rpx; color: #1d5c42; font-weight: 800; }
.label { margin-top: 4rpx; font-size: 22rpx; color: #6c8378; }
.state-wrap { text-align: center; }
.retry-btn { width: 180rpx; }
</style>
