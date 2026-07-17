<template>
  <el-drawer
    v-model="visible"
    :title="title"
    :size="size"
    :direction="direction"
    :destroy-on-close="destroyOnClose"
    @closed="handleClosed"
  >
    <div class="drawer-content">
      <!-- 基础信息区 -->
      <section v-if="hasBasicInfo" class="detail-section">
        <h4 class="section-title">
          <span class="section-icon">
            <el-icon><Document /></el-icon>
          </span>
          {{ basicTitle }}
        </h4>
        <div class="info-grid">
          <slot name="basic-info">
            <div
              v-for="item in basicInfo"
              :key="item.key"
              class="info-item"
            >
              <span class="info-label">{{ item.label }}</span>
              <span class="info-value">
                <slot :name="`info-${item.key}`" :value="item.value">
                  <StatusTag v-if="item.status" :type="item.statusType">
                    {{ item.value }}
                  </StatusTag>
                  <template v-else>{{ item.value ?? '--' }}</template>
                </slot>
              </span>
            </div>
          </slot>
        </div>
      </section>

      <!-- 标签页区 -->
      <section v-if="$slots.tabs" class="detail-section detail-tabs">
        <el-tabs v-model="activeTab" class="detail-tabs-inner">
          <slot name="tabs" />
        </el-tabs>
      </section>

      <!-- 自定义内容区 -->
      <section v-if="$slots.default" class="detail-section">
        <slot />
      </section>

      <!-- 操作区 -->
      <section v-if="showFooter" class="detail-footer">
        <slot name="footer">
          <el-button @click="handleClose">关闭</el-button>
          <template v-if="$slots['footer-extra']">
            <slot name="footer-extra" />
          </template>
        </slot>
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, useSlots } from 'vue'
import { Document } from '@element-plus/icons-vue'
import StatusTag from './StatusTag.vue'

defineOptions({
  name: 'DetailDrawer'
})

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '详情'
  },
  size: {
    type: String,
    default: '600px'
  },
  direction: {
    type: String,
    default: 'rtl'
  },
  destroyOnClose: {
    type: Boolean,
    default: true
  },
  basicInfo: {
    type: Array,
    default: () => []
  },
  basicTitle: {
    type: String,
    default: '基本信息'
  },
  showFooter: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'closed'])

const visible = ref(props.modelValue)
const activeTab = ref('0')

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (!val) {
    activeTab.value = '0'
  }
})

const hasBasicInfo = computed(() => {
  const slots = useSlots()
  return props.basicInfo?.length > 0 || !!slots['basic-info']
})
</script>

<style scoped>
.drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-section {
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border-light);
}

.detail-section:last-of-type {
  border-bottom: none;
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.section-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--primary-50);
  color: var(--primary-deep);
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-item:first-child:nth-last-child(odd) {
  grid-column: span 2;
}

.info-label {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.info-value {
  font-size: var(--text-base);
  color: var(--text-primary);
  word-break: break-word;
}

/* 标签页 */
.detail-tabs {
  padding-top: 0;
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--space-4);
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

.detail-tabs :deep(.el-tabs__item) {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: var(--primary-deep);
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--primary-mid);
}

/* 底部操作区 */
.detail-footer {
  margin-top: auto;
  padding-top: var(--space-5);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

/* 响应式 */
@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-item:first-child:nth-last-child(odd) {
    grid-column: span 1;
  }
}
</style>