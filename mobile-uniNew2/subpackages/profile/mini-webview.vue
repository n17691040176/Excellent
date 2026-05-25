<template>
  <view class="webview-page">
    <web-view v-if="targetUrl" :src="targetUrl" />
    <view v-else class="empty-state">
      <view class="empty-title">共享充电宝入口未配置</view>
      <view class="empty-desc">请先在配置文件里填写小程序或 H5 地址。</view>
      <button class="btn btn-primary mt-24" @click="goFallback">查看充电宝资产</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { POWER_BANK_MINIAPP_CONFIG } from '@/config/power-bank-miniapp';

const targetUrl = ref('');

function goFallback() {
  uni.redirectTo({ url: POWER_BANK_MINIAPP_CONFIG.fallbackPath });
}

onLoad((query) => {
  targetUrl.value = decodeURIComponent(query?.url || '');
});
</script>

<style scoped>
@import '@/styles/common.css';

.webview-page {
  min-height: 100vh;
  background: #fff6eb;
}
.empty-state {
  padding: 120rpx 32rpx;
  text-align: center;
}
.empty-title {
  font-size: 34rpx;
  font-weight: 800;
  color: #4f321a;
}
.empty-desc {
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.5;
  color: #8b7158;
}
</style>
