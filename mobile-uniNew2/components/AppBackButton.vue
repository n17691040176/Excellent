<template>
  <view
    class="app-back-button"
    role="button"
    aria-label="返回"
    hover-class="app-back-button-active"
    @click="$emit('click')"
  >
    <svg class="app-back-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M15 18L9 12L15 6"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </view>
</template>

<script setup>
defineEmits(['click']);
</script>

<style scoped>
.app-back-button {
  width: 64rpx;
  height: 64rpx;
  flex: 0 0 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text, #27272A);
  -webkit-tap-highlight-color: transparent;
}

.app-back-button-active {
  opacity: 0.56;
}

.app-back-icon {
  width: 44rpx;
  height: 44rpx;
}
</style>
