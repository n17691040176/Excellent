<template>
  <div class="metric-card" :class="[`metric-card--${variant}`, { 'metric-card--clickable': clickable }]">
    <!-- 装饰元素 -->
    <div class="metric-card__decoration">
      <span class="decoration-dot"></span>
    </div>

    <div class="metric-card__content">
      <div class="metric-card__header">
        <span class="metric-card__label">{{ label }}</span>
        <span v-if="trend" class="metric-card__trend" :class="trendClass">
          <el-icon v-if="trend.direction === 'up'"><ArrowUp /></el-icon>
          <el-icon v-else><ArrowDown /></el-icon>
          {{ Math.abs(trend.value) }}%
        </span>
      </div>

      <div class="metric-card__value-row">
        <span class="metric-card__number">{{ formattedValue }}</span>
        <div v-if="icon" class="metric-card__icon">
          <el-icon><component :is="icon" /></el-icon>
        </div>
      </div>

      <div v-if="subtext" class="metric-card__subtext">{{ subtext }}</div>
    </div>

    <!-- 底部趋势线（可选装饰） -->
    <div v-if="showSparkline" class="metric-card__sparkline">
      <svg viewBox="0 0 100 30" preserveAspectRatio="none">
        <path :d="sparklinePath" :stroke="sparklineColor" stroke-width="2" fill="none" />
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  value: {
    type: [Number, String],
    required: true
  },
  label: {
    type: String,
    required: true
  },
  subtext: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'success', 'warning', 'danger', 'info', 'neutral'].includes(v)
  },
  trend: {
    type: Object,
    default: null
  },
  icon: {
    type: [String, Object],
    default: ''
  },
  clickable: {
    type: Boolean,
    default: false
  },
  showSparkline: {
    type: Boolean,
    default: false
  },
  sparklineData: {
    type: Array,
    default: () => []
  }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

const trendClass = computed(() => ({
  'metric-card__trend--up': props.trend?.direction === 'up',
  'metric-card__trend--down': props.trend?.direction === 'down'
}))

const sparklineColor = computed(() => {
  const colors = {
    primary: 'var(--accent)',
    success: 'var(--success-500)',
    warning: 'var(--warning-500)',
    danger: 'var(--danger-500)',
    info: 'var(--info-500)',
    neutral: 'var(--text-muted)'
  }
  return colors[props.variant] || colors.neutral
})

const sparklinePath = computed(() => {
  const data = props.sparklineData.length > 0 ? props.sparklineData : [20, 35, 25, 40, 30, 50, 45]
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * 100
    const y = 30 - ((val - min) / range) * 25
    return `${x},${y}`
  })

  return `M ${points.join(' L ')}`
})
</script>

<style scoped>
@import '@/styles/variables.css';

.metric-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: all var(--duration-normal) var(--ease-out);
  overflow: hidden;
}

.metric-card--clickable {
  cursor: pointer;
}

.metric-card--clickable:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--border-default);
  transform: translateY(-2px);
}

/* 装饰元素 */
.metric-card__decoration {
  position: absolute;
  top: 12px;
  right: 12px;
}

.decoration-dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--bg-muted);
}

.metric-card--primary .decoration-dot { background: var(--primary-mid); }
.metric-card--success .decoration-dot { background: var(--success-300); }
.metric-card--warning .decoration-dot { background: var(--warning-300); }
.metric-card--danger .decoration-dot { background: var(--danger-300); }
.metric-card--info .decoration-dot { background: var(--info-300); }
.metric-card--neutral .decoration-dot { background: var(--border-muted); }

/* 内容区 */
.metric-card__content {
  flex: 1;
  position: relative;
  z-index: 1;
}

.metric-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.metric-card__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-muted);
}

.metric-card__trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
}

.metric-card__trend--up {
  color: var(--success-600);
  background: var(--success-50);
}

.metric-card__trend--down {
  color: var(--danger-600);
  background: var(--danger-50);
}

.metric-card__value-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
}

.metric-card__number {
  font-family: var(--font-mono);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  line-height: 1;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  font-feature-settings: 'tnum';
}

.metric-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--bg-muted);
  color: var(--text-muted);
}

.metric-card__subtext {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--leading-normal);
}

/* 变体颜色 */
.metric-card--primary {
  background: linear-gradient(145deg, var(--primary-50) 0%, var(--bg-surface) 100%);
  border-color: var(--primary-100);
}

.metric-card--primary .metric-card__number {
  color: var(--primary-deep);
}

.metric-card--primary .metric-card__icon {
  background: var(--primary-100);
  color: var(--primary-deep);
}

.metric-card--success {
  background: linear-gradient(145deg, var(--success-50) 0%, var(--bg-surface) 100%);
  border-color: var(--success-100);
}

.metric-card--success .metric-card__number {
  color: var(--success-600);
}

.metric-card--warning {
  background: linear-gradient(145deg, var(--warning-50) 0%, var(--bg-surface) 100%);
  border-color: var(--warning-100);
}

.metric-card--warning .metric-card__number {
  color: var(--warning-600);
}

.metric-card--danger {
  background: linear-gradient(145deg, var(--danger-50) 0%, var(--bg-surface) 100%);
  border-color: var(--danger-100);
}

.metric-card--danger .metric-card__number {
  color: var(--danger-600);
}

.metric-card--info {
  background: linear-gradient(145deg, var(--info-50) 0%, var(--bg-surface) 100%);
  border-color: var(--info-100);
}

.metric-card--info .metric-card__number {
  color: var(--info-600);
}

.metric-card--neutral {
  background: var(--bg-surface);
}

.metric-card--neutral .metric-card__number {
  color: var(--text-primary);
}

/* 趋势线 */
.metric-card__sparkline {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 30px;
  opacity: 0.4;
  pointer-events: none;
}

.metric-card__sparkline svg {
  width: 100%;
  height: 100%;
}

/* 响应式 */
@media (max-width: 640px) {
  .metric-card {
    padding: var(--space-4);
  }

  .metric-card__number {
    font-size: var(--text-2xl);
  }

  .metric-card__icon {
    width: 32px;
    height: 32px;
  }
}
</style>