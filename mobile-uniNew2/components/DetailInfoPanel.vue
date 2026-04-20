<template>
  <view class="detail-panel">
    <view class="detail-grid">
      <view v-for="item in items" :key="item.key || item.label" class="detail-cell">
        <view class="detail-label">{{ item.label }}</view>
        <view class="detail-value">{{ item.value || '--' }}</view>
      </view>
    </view>
    <view v-if="note" class="detail-note">{{ note }}</view>
    <slot />
  </view>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  },
  note: {
    type: String,
    default: ''
  }
});
</script>

<style scoped>
.detail-panel {
  margin-top: 12rpx;
  padding: 16rpx;
  border-radius: 18rpx;
  background: #fff8f1;
  border: 1rpx solid rgba(198, 161, 124, 0.14);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.detail-cell {
  min-width: 0;
}

.detail-label {
  font-size: 20rpx;
  color: #9a7e63;
}

.detail-value {
  margin-top: 6rpx;
  font-size: 22rpx;
  line-height: 1.45;
  color: #4f321a;
  word-break: break-all;
}

.detail-note {
  margin-top: 12rpx;
  font-size: 21rpx;
  line-height: 1.55;
  color: #8d745d;
}
</style>
