<template>
  <view class="webview-page">
    <!-- Loading -->
    <view v-if="!checked" class="loading-state">
      <view class="loading-icon">◇</view>
      <text class="loading-text">加载中...</text>
    </view>

    <!-- Webview -->
    <web-view v-else-if="targetUrl" :src="targetUrl" />

    <!-- Empty State -->
    <view v-else class="empty-state">
      <view class="empty-icon">◇</view>
      <text class="empty-title">入口未配置</text>
      <text class="empty-desc">请先在配置文件里填写小程序或 H5 地址</text>
      <view class="empty-btn" @click="goFallback">查看充电宝资产</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { POWER_BANK_MINIAPP_CONFIG } from '@/config/power-bank-miniapp';

const checked = ref(false);
const targetUrl = ref('');

function goFallback() {
  uni.redirectTo({ url: POWER_BANK_MINIAPP_CONFIG.fallbackPath });
}

onLoad((query) => {
  targetUrl.value = decodeURIComponent(query?.url || '');
  checked.value = true;
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.webview-page {
  min-height: 100vh;
  background: var(--bg);
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 24rpx;
}

.loading-icon {
  font-size: 64rpx;
  color: var(--primary);
  animation: spin 2s linear infinite;
}

.loading-text {
  font-size: 26rpx;
  color: var(--text-muted);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 48rpx;
}

.empty-icon {
  font-size: 120rpx;
  color: var(--border);
  margin-bottom: 32rpx;
}

.empty-title {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12rpx;
}

.empty-desc {
  font-size: 26rpx;
  color: var(--text-muted);
  text-align: center;
  margin-bottom: 48rpx;
}

.empty-btn {
  padding: 20rpx 48rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 28rpx;
  font-weight: 600;
  border-radius: 40rpx;
}
</style>
