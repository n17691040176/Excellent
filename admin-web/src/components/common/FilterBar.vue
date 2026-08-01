<template>
  <div class="filter-bar" :class="{ 'filter-bar--collapsed': isCollapsed && collapsible }">
    <div class="filter-bar__row">
      <div class="filter-bar__fields">
        <template v-for="field in visibleFields" :key="field.key">
          <!-- Input 类型 -->
          <div v-if="field.type === 'input'" class="filter-field filter-field--input">
            <el-input
              v-model="localFilters[field.key]"
              :placeholder="field.placeholder || `请输入${field.label || ''}`"
              :clearable="true"
              @keyup.enter="handleSearch"
            >
              <template #prefix v-if="field.label">
                <span class="filter-field__label">{{ field.label }}</span>
              </template>
            </el-input>
          </div>

          <!-- Select 类型 -->
          <div v-else-if="field.type === 'select'" class="filter-field filter-field--select">
            <span v-if="field.label" class="filter-field__label-inline">{{ field.label }}</span>
            <el-select
              v-model="localFilters[field.key]"
              :placeholder="field.placeholder || `选择${field.label || ''}`"
              :clearable="true"
              :style="{ width: field.width ? `${field.width}px` : '140px' }"
            >
              <el-option
                v-for="opt in field.options"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </div>

          <!-- Date 类型 -->
          <div v-else-if="field.type === 'date'" class="filter-field filter-field--date">
            <span v-if="field.label" class="filter-field__label-inline">{{ field.label }}</span>
            <el-date-picker
              v-model="localFilters[field.key]"
              type="date"
              :placeholder="field.placeholder || '选择日期'"
              :clearable="true"
              :style="{ width: field.width ? `${field.width}px` : '140px' }"
            />
          </div>

          <!-- DateRange 类型 -->
          <div v-else-if="field.type === 'dateRange'" class="filter-field filter-field--date-range">
            <span v-if="field.label" class="filter-field__label-inline">{{ field.label }}</span>
            <el-date-picker
              v-model="localFilters[field.key]"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              :clearable="true"
              :style="{ width: field.width ? `${field.width}px` : '260px' }"
            />
          </div>
        </template>
      </div>

      <div class="filter-bar__actions">
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button
          v-if="collapsible && fields.length > collapseThreshold"
          link
          @click="isCollapsed = !isCollapsed"
        >
          {{ isCollapsed ? '展开' : '收起' }}
          <el-icon>
            <ArrowUp v-if="!isCollapsed" />
            <ArrowDown v-else />
          </el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Search, ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  fields: {
    type: Array,
    required: true
  },
  modelValue: {
    type: Object,
    default: () => ({})
  },
  collapsible: {
    type: Boolean,
    default: true
  },
  collapseThreshold: {
    type: Number,
    default: 4
  },
  layout: {
    type: String,
    default: 'horizontal',
    validator: (v) => ['horizontal', 'vertical'].includes(v)
  }
})

const emit = defineEmits(['update:modelValue', 'search', 'reset'])

const localFilters = ref({ ...props.modelValue })
const isCollapsed = ref(true)

const hasSameFilterValues = (left = {}, right = {}) => {
  const leftKeys = Object.keys(left)
  const rightKeys = Object.keys(right)

  return leftKeys.length === rightKeys.length
    && leftKeys.every((key) => Object.prototype.hasOwnProperty.call(right, key) && Object.is(left[key], right[key]))
}

const visibleFields = computed(() => {
  if (!props.collapsible || !isCollapsed.value) {
    return props.fields
  }
  return props.fields.slice(0, props.collapseThreshold)
})

watch(
  () => props.modelValue,
  (val) => {
    if (!hasSameFilterValues(val, localFilters.value)) {
      localFilters.value = { ...val }
    }
  },
  { deep: true, immediate: true }
)

watch(
  localFilters,
  (val) => {
    if (!hasSameFilterValues(val, props.modelValue)) {
      emit('update:modelValue', { ...val })
    }
  },
  { deep: true }
)

const handleSearch = () => {
  emit('search', { ...localFilters.value })
}

const handleReset = () => {
  const resetFilters = {}
  props.fields.forEach((field) => {
    resetFilters[field.key] = field.defaultValue ?? null
  })
  localFilters.value = resetFilters
  emit('reset', resetFilters)
}
</script>

<style scoped>
@import '@/styles/variables.css';

.filter-bar {
  padding: var(--space-4) var(--space-5);
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
}

.filter-bar__row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.filter-bar__fields {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
  flex-wrap: wrap;
}

.filter-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.filter-field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.filter-field__label {
  padding-left: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.filter-field__label-inline {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.filter-field--input :deep(.el-input) {
  width: 220px;
}

.filter-field--input :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .filter-bar__row {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar__fields {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar__actions {
    justify-content: flex-end;
    padding-top: var(--space-3);
    border-top: 1px solid var(--border-light);
  }

  .filter-field--input :deep(.el-input) {
    width: 100%;
  }

  .filter-field--select :deep(.el-select),
  .filter-field--date :deep(.el-date-editor),
  .filter-field--date-range :deep(.el-date-editor) {
    width: 100% !important;
  }
}
</style>
