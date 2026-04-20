<template>
  <view class="filter-chips" :class="customClass">
    <view
      v-for="item in items"
      :key="item.value"
      class="chip interactive"
      :class="{ active: isActive(item.value) }"
      @click="select(item.value)"
    >
      <text>{{ item.label }}</text>
      <text v-if="item.count !== undefined" class="chip-count">{{ item.count }}</text>
    </view>
  </view>
</template>

<script setup>
const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: [String, Number],
    default: ''
  },
  customClass: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'change']);

function isActive(value) {
  return String(props.modelValue) === String(value);
}

function select(value) {
  if (isActive(value)) return;
  emit('update:modelValue', value);
  emit('change', value);
}
</script>

<style scoped>
.filter-chips {
  display: flex;
  gap: 12rpx;
  overflow-x: auto;
}

.chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 10rpx 20rpx;
  border-radius: 999rpx;
  background: #f6f1ea;
  color: #7f6954;
  font-size: 24rpx;
  border: 1rpx solid rgba(194, 156, 117, 0.18);
}

.chip.active {
  background: #bf8752;
  color: #ffffff;
  border-color: #bf8752;
}

.chip-count {
  opacity: 0.85;
  font-size: 20rpx;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
