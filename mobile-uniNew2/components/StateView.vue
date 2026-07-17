<template>
  <view class="state-wrap" :class="customClass">
    <!-- Loading -->
    <svg v-if="type === 'loading'" class="state-icon loading" width="80" height="80" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="31.4 31.4" stroke-dashoffset="0"/>
    </svg>
    <!-- Empty -->
    <svg v-else-if="type === 'empty'" class="state-icon empty" width="100" height="100" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
      <path d="M8 15C8.5 16.5 9.5 18 12 18C14.5 18 15.5 16.5 16 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="9" cy="9" r="1.5" fill="currentColor"/>
      <circle cx="15" cy="9" r="1.5" fill="currentColor"/>
    </svg>
    <!-- Error -->
    <svg v-else-if="type === 'error'" class="state-icon error" width="80" height="80" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
      <path d="M12 8V12M12 16H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <!-- Default -->
    <svg v-else class="state-icon" width="80" height="80" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
      <path d="M12 16V12M12 8H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>

    <view class="state-title">{{ title }}</view>
    <view v-if="description" class="state-desc">{{ description }}</view>
    <view v-if="showRetry" class="retry-btn" @click="$emit('retry')">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M1 4V10H7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M3.51 15C4.15839 16.8404 5.38734 18.4202 7.01166 19.5014C8.63598 20.5826 10.5677 21.1066 12.5157 20.9945C14.4637 20.8824 16.3226 20.1397 17.8121 18.8798C19.3016 17.6198 20.3413 15.9089 20.7741 14.0064C21.2068 12.1039 21.0107 10.1157 20.2127 8.33153C19.4148 6.54734 18.0551 5.06235 16.3288 4.10187C14.6025 3.14139 12.6009 2.75431 10.6223 3.00104C8.64365 3.24778 6.79194 4.11503 5.34 5.47" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      {{ retryText }}
    </view>
  </view>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'loading' },
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80rpx 48rpx;
  text-align: center;
}

.state-icon {
  margin-bottom: 32rpx;
  color: var(--border);
}

.state-icon.loading {
  color: var(--primary);
  animation: spin 1s linear infinite;
}

.state-icon.empty {
  color: var(--border);
}

.state-icon.error {
  color: var(--error);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.state-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text);
  margin-bottom: 8rpx;
}

.state-desc {
  margin-top: 12rpx;
  color: var(--text-muted);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.retry-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  margin-top: 32rpx;
  padding: 16rpx 40rpx;
  background: var(--card);
  color: var(--primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  border: 1rpx solid var(--primary);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast) var(--ease-out);
}

.retry-btn:active {
  background: rgba(5, 150, 105, 0.05);
  transform: scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .state-icon.loading {
    animation: none;
  }

  .retry-btn {
    transition: none;
  }
}
</style>