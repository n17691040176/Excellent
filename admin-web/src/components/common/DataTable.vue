<template>
  <div class="data-table">
    <!-- 操作按钮组 -->
    <div v-if="showToolbar" class="data-table__toolbar">
      <div v-if="$slots.toolbarLeft" class="data-table__toolbar-left">
        <slot name="toolbarLeft" />
      </div>
      <div v-if="$slots.toolbarRight" class="data-table__toolbar-right">
        <slot name="toolbarRight" />
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="tableData"
      v-bind="$attrs"
      border
      @selection-change="handleSelectionChange"
    >
      <!-- 选择列 -->
      <el-table-column v-if="selectable" type="selection" width="50" />

      <!-- 动态列 -->
      <template v-for="col in visibleColumns" :key="col.key">
        <!-- 操作列 -->
        <el-table-column
          v-if="col.key === 'actions'"
          :label="col.label || '操作'"
          :width="col.width || 160"
          :fixed="col.fixed || 'right'"
          align="center"
        >
          <template #default="{ row }">
            <div class="action-group">
              <!-- 主要操作 -->
              <template v-if="actions?.primary?.length">
                <el-button
                  v-for="action in getVisibleActions(actions.primary, row)"
                  :key="action.key"
                  link
                  :type="action.type || 'primary'"
                  :disabled="getActionDisabled(action, row)"
                  @click="handleAction(action.key, row)"
                >
                  {{ action.label }}
                </el-button>
              </template>

              <!-- 次要操作 -->
              <template v-if="actions?.secondary?.length">
                <el-button
                  v-for="action in getVisibleActions(actions.secondary, row)"
                  :key="action.key"
                  link
                  :type="action.type || 'default'"
                  :disabled="getActionDisabled(action, row)"
                  @click="handleAction(action.key, row)"
                >
                  {{ action.label }}
                </el-button>
              </template>

              <!-- 更多操作下拉 -->
              <el-dropdown
                v-if="hasMoreActions(row)"
                trigger="click"
                @command="(cmd) => handleAction(cmd, row)"
              >
                <el-button link>
                  更多
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <template v-for="action in getMoreActions(row)" :key="action.key">
                      <el-dropdown-item :command="action.key" :divided="action.divided">
                        <span :class="{ 'text-danger': action.danger }">
                          {{ action.label }}
                        </span>
                      </el-dropdown-item>
                    </template>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>

        <!-- 自定义插槽列 -->
        <el-table-column
          v-else-if="col.slot"
          :prop="col.prop || col.key"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          :align="col.align || 'left'"
          :fixed="col.fixed"
        >
          <template #header>
            <slot :name="`header-${col.key}`">{{ col.label }}</slot>
          </template>
          <template #default="{ row }">
            <slot :name="`column-${col.key}`" :row="row" :column="col" />
          </template>
        </el-table-column>

        <!-- 渲染类型列 -->
        <el-table-column
          v-else
          :prop="col.prop || col.key"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          :align="col.align || 'left'"
          :sortable="col.sortable"
          :fixed="col.fixed"
        >
          <template #default="{ row }">
            <!-- Status 类型 -->
            <template v-if="col.render === 'status'">
              <StatusTag :type="getStatusType(col.options, row[col.key])">
                {{ getOptionLabel(col.options, row[col.key]) }}
              </StatusTag>
            </template>
            <!-- Tag 类型 -->
            <template v-else-if="col.render === 'tag'">
              <el-tag size="small" :type="getTagType(col.options, row[col.key])">
                {{ getOptionLabel(col.options, row[col.key]) }}
              </el-tag>
            </template>
            <!-- Money 类型 -->
            <template v-else-if="col.render === 'money'">
              <span class="money-text">{{ formatMoney(row[col.key]) }}</span>
            </template>
            <!-- Date 类型 -->
            <template v-else-if="col.render === 'date'">
              <span class="date-text">{{ formatDate(row[col.key]) }}</span>
            </template>
            <!-- Boolean 类型 -->
            <template v-else-if="col.render === 'boolean'">
              <el-tag v-if="row[col.key]" type="success" size="small">是</el-tag>
              <el-tag v-else type="info" size="small">否</el-tag>
            </template>
            <!-- 默认文本 -->
            <template v-else>
              {{ row[col.key] ?? '--' }}
            </template>
          </template>
        </el-table-column>
      </template>

      <!-- 展开行 -->
      <el-table-column v-if="$slots.expand" type="expand" width="50">
        <template #default="{ row }">
          <slot name="expand" :row="row" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div v-if="pagination" class="data-table__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :total="pagination.total"
        :page-sizes="pagination.pageSizes || [10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && !tableData.length" class="data-table__empty">
      <el-empty :description="emptyText" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import StatusTag from './StatusTag.vue'

defineOptions({
  name: 'DataTable',
  inheritAttrs: false
})

const props = defineProps({
  columns: {
    type: Array,
    default: () => []
  },
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  selectable: {
    type: Boolean,
    default: false
  },
  actions: {
    type: Object,
    default: null
  },
  pagination: {
    type: Object,
    default: null
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  showToolbar: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'action',
  'page-change',
  'size-change',
  'selection-change',
  'update:page',
  'update:pageSize'
])

const tableRef = ref(null)
const selectedRows = ref([])

// 分页状态
const currentPage = ref(props.pagination?.current || 1)
const currentPageSize = ref(props.pagination?.pageSize || 20)

// 监听分页变化
watch(() => props.pagination, (val) => {
  if (val) {
    currentPage.value = val.current || 1
    currentPageSize.value = val.pageSize || 20
  }
}, { immediate: true })

// 可见列
const visibleColumns = computed(() =>
  props.columns.filter(col => !col.hidden)
)

// 表格数据
const tableData = computed(() => {
  if (props.pagination) {
    return props.data
  }
  return props.data
})

// 获取操作按钮可见性
function getVisibleActions(actions, row) {
  if (!actions) return []
  return actions.filter(action => {
    if (action.condition) {
      return action.condition(row)
    }
    return true
  }).slice(0, 3) // 最多显示 3 个
}

// 获取更多操作
function getMoreActions(row) {
  if (!props.actions?.more) return []
  return props.actions.more.filter(action => {
    if (action.condition) {
      return action.condition(row)
    }
    return true
  })
}

// 是否有更多操作
function hasMoreActions(row) {
  return getMoreActions(row).length > 0
}

// 获取操作禁用状态
function getActionDisabled(action, row) {
  if (typeof action.disabled === 'boolean') return action.disabled
  if (typeof action.disabled === 'function') return action.disabled(row)
  return false
}

// 处理操作
function handleAction(key, row) {
  emit('action', key, row)
}

// 处理分页变化
function handlePageChange(page) {
  emit('page-change', page)
  emit('update:page', page)
}

// 处理每页数量变化
function handleSizeChange(size) {
  currentPage.value = 1
  emit('size-change', size)
  emit('update:pageSize', size)
}

// 处理选择变化
function handleSelectionChange(selection) {
  selectedRows.value = selection
  emit('selection-change', selection)
}

// 格式化金额
function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

// 格式化日期
function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

// 获取选项标签
function getOptionLabel(options, value) {
  if (!options) return value
  const option = options.find(opt => opt.value === value || opt.value === String(value))
  return option?.label || value || '--'
}

// 获取状态类型
function getStatusType(options, value) {
  if (!options) return 'default'
  const option = options.find(opt => opt.value === value || opt.value === String(value))
  return option?.type || 'default'
}

// 获取标签类型
function getTagType(options, value) {
  if (!options) return 'default'
  const option = options.find(opt => opt.value === value || opt.value === String(value))
  return option?.type || 'default'
}

// 暴露方法
defineExpose({
  tableRef,
  selectedRows,
  clearSelection: () => tableRef.value?.clearSelection(),
  toggleRowSelection: (row, selected) => tableRef.value?.toggleRowSelection(row, selected)
})
</script>

<style scoped>
@import '@/styles/variables.css';

.data-table {
  width: 100%;
}

.data-table__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.data-table__toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.data-table__toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 操作按钮组 */
.action-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-wrap: wrap;
}

/* 分页 */
.data-table__pagination {
  margin-top: var(--space-5);
  display: flex;
  justify-content: flex-end;
}

/* 空状态 */
.data-table__empty {
  padding: var(--space-10) 0;
}

/* 文本样式 */
.money-text {
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.date-text {
  color: var(--text-secondary);
}

.text-danger {
  color: var(--danger-600);
}

/* 响应式 */
@media (max-width: 768px) {
  .data-table__toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .action-group {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
