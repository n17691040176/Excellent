<template>
  <view class="container invite-page">
    <view class="card poster">
      <view class="poster-tag">邀请有礼</view>
      <view class="section-title mt-12">分享邀请码，好友下单你得奖励</view>
      <view class="muted">专属邀请码全程跟踪，注册和转化数据实时可看</view>

      <view class="invite-code-wrap mt-20">
        <view class="invite-code-label">我的邀请码</view>
        <view class="invite-code">{{ inviteCode }}</view>
      </view>

      <view class="poster-actions mt-24">
        <button class="btn btn-primary" @click="share">立即分享</button>
        <button class="btn btn-ghost" @click="copyCode">复制邀请码</button>
      </view>
    </view>

    <view class="card mt-24 data-card">
      <view class="row-between">
        <view class="section-title no-margin">邀请数据</view>
        <view class="data-chip">实时更新</view>
      </view>
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
const copyCode = async () => {
  await uni.setClipboardData({ data: inviteCode.value });
  uni.showToast({ title: '邀请码已复制', icon: 'none' });
};

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
.poster {
  background: linear-gradient(135deg, #fff6ec 0%, #ffe2c9 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.16);
  overflow: hidden;
  position: relative;
}
.poster::after {
  content: '';
  position: absolute;
  right: -36rpx;
  top: -36rpx;
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  background: rgba(255, 122, 0, 0.08);
}
.poster-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.invite-code-wrap {
  padding: 18rpx;
  border-radius: 22rpx;
  background: rgba(255, 255, 255, 0.7);
  border: 1rpx solid rgba(255, 154, 106, 0.12);
}
.invite-code-label { font-size: 20rpx; color: #8b7158; }
.invite-code { margin-top: 8rpx; font-size: 32rpx; font-weight: 900; color: #ff6a00; letter-spacing: 1.4rpx; }
.poster-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; }
.data-card { border: 1rpx solid rgba(255, 154, 106, 0.16); }
.data-chip {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 122, 0, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 700;
}
.no-margin { margin-bottom: 0; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; }
.item { border-radius: 18rpx; background: linear-gradient(180deg, #fffaf7, #fff1e7); padding: 14rpx; border: 1rpx solid rgba(255, 154, 106, 0.14); }
.num { font-size: 34rpx; color: #ff6a00; font-weight: 900; }
.label { margin-top: 4rpx; font-size: 22rpx; color: #6c8378; }
.state-wrap { text-align: center; }
.retry-btn { width: 180rpx; }
</style>
