<template>
  <view class="state-wrap card" :class="customClass">
    <view class="state-title">{{ title }}</view>
    <view v-if="description" class="state-desc">{{ description }}</view>
    <button v-if="showRetry" class="btn btn-ghost retry-btn mt-16" @click="$emit('retry')">{{ retryText }}</button>
  </view>
</template>

<script setup>
defineProps({
  title: { type: String, default: '加载中...' },
  description: { type: String, default: '' },
  showRetry: { type: Boolean, default: false },
  retryText: { type: String, default: '重试' },
  customClass: { type: String, default: '' }
});

defineEmits(['retry']);
</script>

<style scoped>
@import '@/styles/common.css';

.state-wrap {
  text-align: center;
  border: 1rpx solid rgba(198, 161, 124, 0.18);
  box-shadow: 0 12rpx 28rpx rgba(141, 100, 60, 0.08);
}

.state-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #4f321a;
}

.state-desc {
  margin-top: 8rpx;
  color: #8b7158;
  font-size: 23rpx;
  line-height: 1.5;
}

.retry-btn {
  width: 180rpx;
  margin-left: auto;
  margin-right: auto;
}
</style>
