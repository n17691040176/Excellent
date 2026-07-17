<template>
  <span class="status-tag" :class="tagClass">
    <span v-if="dot" class="status-tag__dot"></span>
    <slot>{{ displayLabel }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'default'
  },
  status: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  dot: {
    type: Boolean,
    default: true
  },
  outline: {
    type: Boolean,
    default: false
  }
})

// Status mappings by category
const STATUS_MAP = {
  // Order statuses
  order: {
    PENDING: { type: 'warning', label: '待支付' },
    PAID: { type: 'info', label: '已支付' },
    PROCESSING: { type: 'primary', label: '处理中' },
    COMPLETED: { type: 'success', label: '已完成' },
    CANCELLED: { type: 'neutral', label: '已取消' },
    REFUNDED: { type: 'danger', label: '已退款' }
  },
  // Package statuses
  package: {
    DRAFT: { type: 'neutral', label: '草稿' },
    ON_SHELF: { type: 'success', label: '已上架' },
    OFF_SHELF: { type: 'warning', label: '已下架' },
    APPROVED: { type: 'success', label: '已通过' }
  },
  // Supplier statuses
  supplier: {
    PENDING: { type: 'warning', label: '待审核' },
    APPROVED: { type: 'success', label: '已通过' },
    REJECTED: { type: 'danger', label: '已驳回' },
    ACTIVE: { type: 'success', label: '已启用' },
    INACTIVE: { type: 'neutral', label: '已停用' }
  },
  // Audit statuses
  audit: {
    PENDING: { type: 'warning', label: '待审核' },
    APPROVED: { type: 'success', label: '已通过' },
    REJECTED: { type: 'danger', label: '已驳回' }
  },
  // Commission statuses
  commission: {
    FROZEN: { type: 'warning', label: '冻结中' },
    SETTLED: { type: 'success', label: '已结算' },
    CANCELED: { type: 'neutral', label: '已取消' }
  },
  // Agreement statuses
  agreement: {
    ACTIVE: { type: 'success', label: '协议有效' },
    PENDING: { type: 'warning', label: '协议待签' },
    EXPIRED: { type: 'danger', label: '协议过期' }
  },
  // Product statuses
  product: {
    DRAFT: { type: 'neutral', label: '草稿' },
    PENDING_REVIEW: { type: 'warning', label: '待审核' },
    ON_SHELF: { type: 'success', label: '已上架' },
    OFF_SHELF: { type: 'neutral', label: '已下架' },
    REJECTED: { type: 'danger', label: '已驳回' }
  },
  // Withdraw statuses
  withdraw: {
    PENDING: { type: 'warning', label: '待审核' },
    APPROVED: { type: 'info', label: '已通过' },
    REJECTED: { type: 'danger', label: '已驳回' },
    PROCESSING: { type: 'primary', label: '处理中' },
    COMPLETED: { type: 'success', label: '已完成' },
    FAILED: { type: 'danger', label: '失败' }
  },
  // User statuses
  user: {
    ACTIVE: { type: 'success', label: '正常' },
    DISABLED: { type: 'danger', label: '已禁用' },
    PENDING: { type: 'warning', label: '待激活' }
  }
}

const resolved = computed(() => {
  if (props.status && props.type) {
    const map = STATUS_MAP[props.type]
    if (map && map[props.status]) {
      return map[props.status]
    }
  }
  // Fallback: treat type as direct color type
  if (['default', 'primary', 'success', 'warning', 'danger', 'info', 'neutral'].includes(props.type)) {
    return { type: props.type, label: props.label || props.status }
  }
  return { type: 'default', label: props.label || props.status }
})

const tagClass = computed(() => [
  `status-tag--${resolved.value.type}`,
  { 'status-tag--outline': props.outline }
])

const displayLabel = computed(() => props.label || resolved.value.label)
</script>

<style scoped>
@import '@/styles/variables.css';

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  line-height: var(--leading-normal);
  white-space: nowrap;
}

/* Dot indicator */
.status-tag__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

/* Type variants */
.status-tag--default {
  background: var(--bg-muted);
  color: var(--text-muted);
}

.status-tag--primary {
  background: var(--primary-50);
  color: var(--primary-deep);
}

.status-tag--success {
  background: var(--success-50);
  color: var(--success-700);
}

.status-tag--warning {
  background: var(--warning-50);
  color: var(--warning-700);
}

.status-tag--danger {
  background: var(--danger-50);
  color: var(--danger-700);
}

.status-tag--info {
  background: var(--info-50);
  color: var(--info-700);
}

.status-tag--neutral {
  background: var(--bg-muted);
  color: var(--text-muted);
}

/* Outline variants */
.status-tag--outline {
  background: transparent;
  border: 1px solid currentColor;
}

.status-tag--outline.status-tag--default {
  border-color: var(--border-muted);
}

.status-tag--outline.status-tag--primary {
  border-color: var(--primary-mid);
}

.status-tag--outline.status-tag--success {
  border-color: var(--success-500);
}

.status-tag--outline.status-tag--warning {
  border-color: var(--warning-500);
}

.status-tag--outline.status-tag--danger {
  border-color: var(--danger-500);
}

.status-tag--outline.status-tag--info {
  border-color: var(--info-500);
}

.status-tag--outline.status-tag--neutral {
  border-color: var(--border-muted);
}
</style>