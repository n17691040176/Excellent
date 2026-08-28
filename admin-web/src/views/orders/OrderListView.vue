<template>
  <div class="orders-view">
    <!-- 统一页面头部 -->
    <PageHeader title="订单管理" :description="scopeHint">
      <template #actions>
        <el-button plain @click="resetFilters">重置筛选</el-button>
        <el-button type="primary" @click="loadData">
          <el-icon><Refresh /></el-icon>
          刷新订单
        </el-button>
      </template>
    </PageHeader>

    <!-- 指标卡片行 -->
    <div class="metric-grid">
      <MetricCard
        v-for="item in metrics"
        :key="item.label"
        :value="item.value"
        :label="item.label"
        :subtext="item.subtext"
        :variant="item.variant"
      />
    </div>

    <!-- 数据卡片 -->
    <div class="panel-card data-card">
      <!-- 统一的筛选栏 -->
      <FilterBar
        :fields="filterFields"
        v-model="filters"
        @search="handleSearch"
        @reset="handleReset"
      />

      <!-- 数据表格 -->
      <el-table v-loading="loading" :data="rows" border>
        <el-table-column prop="order_no" label="订单号" min-width="180" />
        <el-table-column label="用户信息" min-width="160">
          <template #default="{ row }">
            <div class="cell-title">{{ row.user_nickname || '--' }}</div>
            <div class="cell-meta">{{ row.user_phone || '--' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单类型" width="140">
          <template #default="{ row }">
            <el-tag size="small">{{ orderTypeLabel(row.order_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="商品摘要" min-width="200">
          <template #default="{ row }">
            <div class="cell-title">{{ row.title || '--' }}</div>
            <div class="cell-meta">{{ row.products_summary || '--' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120">
          <template #default="{ row }">
            <div class="cell-title">{{ formatMoney(row.payable_amount) }}</div>
            <div class="cell-meta">共 {{ row.item_count || 0 }} 件</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <StatusTag :type="orderStatusType(row.order_status)">{{ row.status_text || row.order_status }}</StatusTag>
            <div class="cell-meta" style="margin-top: 4px;">
              <StatusTag :type="payStatusType(row.pay_status)" :dot="false">{{ payStatusLabel(row.pay_status) }}</StatusTag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">
            <div class="cell-title">{{ formatDate(row.created_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <!-- 主要操作 -->
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              <!-- 次要操作 -->
              <el-button
                v-permission="'orders:manage'"
                link
                type="success"
                :disabled="row.pay_status === 'PAID' || row.order_status === 'REFUND'"
                @click="handleAction(row, 'pay')"
              >
                支付
              </el-button>
              <el-button
                v-permission="'orders:manage'"
                link
                type="warning"
                :disabled="!row.can_ship"
                @click="handleAction(row, 'ship')"
              >
                发货
              </el-button>
              <!-- 更多操作下拉 -->
              <el-dropdown trigger="click" @command="(cmd) => handleAction(row, cmd)">
                <el-button link>
                  更多
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      command="close"
                      :disabled="!row.can_cancel"
                    >
                      关闭订单
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-permission="'orders:manage'"
                      command="refund"
                      :disabled="!row.can_refund"
                      divided
                    >
                      <span style="color: var(--danger-600);">退款</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="table-pagination"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        @current-change="loadData"
        @size-change="handlePageSizeChange"
      />
    </div>

    <!-- 详情抽屉 - Tab 模式 -->
    <el-drawer v-model="detailVisible" title="订单详情" size="900px" destroy-on-close>
      <div v-loading="detailLoading" class="detail-layout">
        <template v-if="detail">
          <!-- 基本信息卡片 -->
          <div class="panel-card data-card">
            <div class="detail-top">
              <div>
                <div class="detail-title">{{ detail.title || detail.order_no }}</div>
                <div class="cell-meta">订单号 {{ detail.order_no }}</div>
              </div>
              <div class="detail-tags">
                <StatusTag :type="orderStatusType(detail.order_status)">{{ detail.status_text || detail.order_status }}</StatusTag>
                <StatusTag :type="payStatusType(detail.pay_status)">{{ payStatusLabel(detail.pay_status) }}</StatusTag>
                <StatusTag :type="deliveryTagType(detail.delivery_status)">{{ detail.delivery_status_text }}</StatusTag>
              </div>
            </div>

            <el-descriptions :column="2" border class="detail-desc">
              <el-descriptions-item label="用户">{{ detail.user?.nickname || '--' }} / {{ detail.user?.phone || '--' }}</el-descriptions-item>
              <el-descriptions-item label="团队">{{ detail.team?.name || '未绑定团队' }}</el-descriptions-item>
              <el-descriptions-item label="订单类型">{{ orderTypeLabel(detail.order_type) }}</el-descriptions-item>
              <el-descriptions-item label="业务专区">{{ zoneTypeLabel(detail.zone_type) }}</el-descriptions-item>
              <el-descriptions-item label="支付组合">{{ detail.payment_combo || '--' }}</el-descriptions-item>
              <el-descriptions-item label="物流方式">{{ detail.delivery_mode_text || (detail.requires_shipping ? '待配置' : '无需物流') }}</el-descriptions-item>
              <el-descriptions-item label="待支付">
                <span class="text-primary">{{ formatMoney(detail.payable_amount) }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="已支付">{{ formatMoney(detail.paid_amount) }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(detail.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="支付时间">{{ formatDate(detail.paid_at) }}</el-descriptions-item>
              <el-descriptions-item v-if="detail.requires_shipping" label="收货地址" :span="2">
                <template v-if="detail.shipping_address">
                  {{ detail.shipping_address.receiver_name }} / {{ detail.shipping_address.receiver_phone }} / {{ detail.shipping_address.full_address }}
                </template>
                <span v-else class="text-danger">未保存收货地址</span>
              </el-descriptions-item>
              <el-descriptions-item label="物流单号" :span="2">{{ detail.tracking_no || (detail.requires_shipping ? '待发货' : '无需物流') }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- Tab 切换区域 -->
          <div class="detail-tabs">
            <el-tabs v-model="activeTab" class="detail-tabs-inner">
              <el-tab-pane label="订单商品" name="items">
                <el-table :data="detail.items || []" border>
                  <el-table-column prop="product_name" label="商品名称" min-width="220" />
                  <el-table-column prop="quantity" label="数量" width="80" align="center" />
                  <el-table-column label="单价" width="120" align="right">
                    <template #default="{ row }">{{ formatMoney(row.unit_price) }}</template>
                  </el-table-column>
                  <el-table-column label="小计" width="120" align="right">
                    <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="物流轨迹" name="logistics">
                <div class="timeline-list">
                  <div v-for="item in detail.shipment?.timeline || detail.timeline || []" :key="`${item.title}-${item.time}`" class="timeline-item">
                    <div class="timeline-dot" :class="{ active: item.active }"></div>
                    <div>
                      <div class="cell-title">{{ item.title }}</div>
                      <div class="cell-meta">{{ formatDate(item.time) }}</div>
                    </div>
                  </div>
                  <div v-if="!detail.shipment?.timeline?.length && !detail.timeline?.length" class="empty-hint">
                    暂无物流信息
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </template>
      </div>

      <!-- 抽屉底部操作 -->
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button
            v-if="detail?.can_ship"
            type="primary"
            @click="handleShip"
          >
            确认发货
          </el-button>
          <el-button
            v-if="detail?.can_cancel"
            type="warning"
            @click="handleClose"
          >
            关闭订单
          </el-button>
          <el-button
            v-if="detail?.can_refund"
            type="danger"
            @click="handleRefund"
          >
            订单退款
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { formatDateTime } from '@/utils/datetime'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, ArrowDown } from '@element-plus/icons-vue'

import { orderApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { PageHeader, MetricCard, FilterBar, StatusTag } from '@/components/common'

const userStore = useUserStore()

const loading = ref(false)
const detailLoading = ref(false)
const detailVisible = ref(false)
const activeTab = ref('items')
const rows = ref([])
const detail = ref(null)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = ref({
  keyword: '',
  order_status: '',
  pay_status: '',
  order_type: '',
  zone_type: ''
})

const orderStatusOptions = [
  { label: '待支付', value: 'PENDING_PAYMENT' },
  { label: '待发货', value: 'PENDING_SHIP' },
  { label: '已发货', value: 'SHIPPED' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已取消/已退款', value: 'REFUND' }
]

const payStatusOptions = [
  { label: '未支付', value: 'UNPAID' },
  { label: '已支付', value: 'PAID' },
  { label: '已退款', value: 'REFUNDED' }
]

const orderTypeOptions = [
  { label: '普通商品', value: 'NORMAL_PRODUCT' },
  { label: '套餐订单', value: 'PACKAGE_ORDER' },
  { label: '复购订单', value: 'REPURCHASE_ORDER' },
  { label: '自营订单', value: 'SELF_OPERATED_ORDER' },
  { label: '爆款订单', value: 'HOT_SALE_ORDER' },
  { label: '本地生活', value: 'LOCAL_LIFE_ORDER' },
  { label: '供应商入驻', value: 'SUPPLIER_ENTRY_ORDER' }
]

const zoneTypeOptions = [
  { label: '复购区', value: 'REPURCHASE' },
  { label: '自营商城', value: 'SELF_OPERATED' },
  { label: '爆款区', value: 'HOT_SALE' },
  { label: '本地生活', value: 'LOCAL_LIFE' }
]

const refundFailureStatuses = new Set(['FAILED', 'CLOSED', 'ABNORMAL'])
const refundProcessingStatuses = new Set(['PENDING', 'PROCESSING'])

// 筛选字段配置
const filterFields = [
  { key: 'keyword', type: 'input', placeholder: '搜索订单号 / 用户昵称 / 手机号', width: 240 },
  { key: 'order_status', type: 'select', label: '订单状态', options: orderStatusOptions, width: 140 },
  { key: 'pay_status', type: 'select', label: '支付状态', options: payStatusOptions, width: 120 },
  { key: 'order_type', type: 'select', label: '订单类型', options: orderTypeOptions, width: 160 }
]

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '按移动端订单链路统一后台视角，当前仅展示所属团队订单。'
    : '按移动端订单、支付与物流字段统一后台管理接口。'
)

const metrics = computed(() => {
  const currentRows = rows.value
  return [
    { label: '当前结果', value: total.value, subtext: `本页 ${currentRows.length} 条`, variant: 'neutral' },
    { label: '待支付', value: currentRows.filter((item) => item.order_status === 'PENDING_PAYMENT').length, subtext: '待付款', variant: 'warning' },
    { label: '待发货', value: currentRows.filter((item) => item.order_status === 'PENDING_SHIP').length, subtext: '已付款', variant: 'primary' },
    { label: '已完成', value: currentRows.filter((item) => item.order_status === 'COMPLETED').length, subtext: '累计完成', variant: 'success' }
  ]
})

function formatDate(value) {
  return formatDateTime(value)
}

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function orderTypeLabel(value) {
  return orderTypeOptions.find((item) => item.value === value)?.label || value || '--'
}

function zoneTypeLabel(value) {
  return zoneTypeOptions.find((item) => item.value === value)?.label || value || '--'
}

function payStatusLabel(value) {
  return payStatusOptions.find((item) => item.value === value)?.label || value || '--'
}

function orderStatusType(status) {
  return {
    PENDING_PAYMENT: 'warning',
    PENDING_SHIP: 'primary',
    SHIPPED: 'info',
    COMPLETED: 'success',
    REFUND: 'danger'
  }[status] || 'default'
}

function payStatusType(status) {
  return {
    UNPAID: 'default',
    PAID: 'success',
    REFUNDED: 'danger'
  }[status] || 'default'
}

function deliveryTagType(status) {
  return {
    pending: 'warning',
    shipping: 'info',
    delivered: 'success',
    not_required: 'default'
  }[status] || 'default'
}

function showRefundResult(result) {
  const providerStatus = String(result?.provider_status || '').trim().toUpperCase()

  if (refundFailureStatuses.has(providerStatus)) {
    ElMessage.error('退款失败，请稍后重试')
    return
  }

  if (refundProcessingStatuses.has(providerStatus) || result?.completed !== true) {
    ElMessage.warning('退款申请已提交，正在处理中')
    return
  }

  ElMessage.success('订单已退款')
}

function buildParams() {
  return {
    page: page.value,
    page_size: pageSize.value,
    keyword: filters.value.keyword || undefined,
    order_status: filters.value.order_status || undefined,
    pay_status: filters.value.pay_status || undefined,
    order_type: filters.value.order_type || undefined,
    zone_type: filters.value.zone_type || undefined
  }
}

async function loadData() {
  loading.value = true
  try {
    const data = await orderApi.list(buildParams())
    rows.value = data.items || []
    total.value = Number(data.total || 0)
  } finally {
    loading.value = false
  }
}

async function loadDetail(id) {
  detailLoading.value = true
  try {
    detail.value = await orderApi.detail(id)
  } finally {
    detailLoading.value = false
  }
}

async function openDetail(row) {
  detailVisible.value = true
  detail.value = null
  activeTab.value = 'items'
  await loadDetail(row.id)
}

async function handleAction(row, action) {
  if (action === 'ship') {
    const res = await ElMessageBox.prompt('确认发货该订单吗？请填写物流单号', '订单发货', {
      confirmButtonText: '确认发货',
      cancelButtonText: '取消',
      inputPlaceholder: '请输入物流单号',
      inputValidator: (value) => Boolean(String(value || '').trim()) || '物流单号不能为空'
    })
    await orderApi.ship(row.id, { tracking_no: res.value })
    ElMessage.success('发货成功')
    await loadData()
    if (detailVisible.value && detail.value?.id === row.id) {
      await loadDetail(row.id)
    }
    return
  }

  const actionMap = {
    pay: { label: '置为已支付', request: () => orderApi.markPaid(row.id) },
    close: { label: '关闭订单', request: () => orderApi.close(row.id) },
    refund: { label: '退款', request: () => orderApi.refund(row.id) }
  }
  const target = actionMap[action]
  if (!target) return
  await ElMessageBox.confirm(`确认${target.label} ${row.order_no} 吗？`, '订单操作', { type: 'warning' })
  const result = await target.request()
  if (action === 'refund') {
    showRefundResult(result)
  } else {
    ElMessage.success(`${target.label}成功`)
  }
  await loadData()
  if (detailVisible.value && detail.value?.id === row.id) {
    await loadDetail(row.id)
  }
}

async function handleShip() {
  if (!detail.value) return
  const res = await ElMessageBox.prompt('确认发货该订单吗？请填写物流单号', '订单发货', {
    confirmButtonText: '确认发货',
    cancelButtonText: '取消',
    inputPlaceholder: '请输入物流单号',
    inputValidator: (value) => Boolean(String(value || '').trim()) || '物流单号不能为空'
  })
  await orderApi.ship(detail.value.id, { tracking_no: res.value })
  ElMessage.success('发货成功')
  await loadData()
  await loadDetail(detail.value.id)
}

async function handleClose() {
  if (!detail.value) return
  await ElMessageBox.confirm(`确认关闭订单 ${detail.value.order_no} 吗？`, '关闭订单', { type: 'warning' })
  await orderApi.close(detail.value.id)
  ElMessage.success('订单已关闭')
  await loadData()
  await loadDetail(detail.value.id)
}

async function handleRefund() {
  if (!detail.value) return
  await ElMessageBox.confirm(`确认退款订单 ${detail.value.order_no} 吗？`, '订单退款', { type: 'warning' })
  const result = await orderApi.refund(detail.value.id)
  showRefundResult(result)
  await loadData()
  await loadDetail(detail.value.id)
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handleReset() {
  page.value = 1
  loadData()
}

function handlePageSizeChange() {
  page.value = 1
  loadData()
}

function resetFilters() {
  filters.value = {
    keyword: '',
    order_status: '',
    pay_status: '',
    order_type: '',
    zone_type: ''
  }
  page.value = 1
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.orders-view {
  display: grid;
  gap: var(--space-4);
}

.data-card {
  padding: var(--space-5);
}

/* 表格样式 */
.cell-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.cell-meta {
  margin-top: 4px;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.table-pagination {
  margin-top: var(--space-5);
  justify-content: flex-end;
}

/* 操作按钮组 */
.action-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-wrap: wrap;
}

/* 详情抽屉 */
.detail-layout {
  display: grid;
  gap: var(--space-5);
}

.detail-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-light);
}

.detail-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.detail-desc {
  margin-top: var(--space-4);
}

/* Tab 样式 */
.detail-tabs {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.detail-tabs-inner {
  padding: 0 var(--space-4);
}

.detail-tabs-inner :deep(.el-tabs__header) {
  margin: 0;
}

.detail-tabs-inner :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

/* 时间轴 */
.timeline-list {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0;
}

.timeline-item {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.timeline-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  background: var(--border-default);
  flex-shrink: 0;
}

.timeline-dot.active {
  background: var(--primary-mid);
}

.empty-hint {
  text-align: center;
  color: var(--text-muted);
  padding: var(--space-6);
}

/* 抽屉底部 */
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-light);
  background: var(--bg-surface);
}

/* 文字辅助 */
.text-primary {
  color: var(--primary-deep);
  font-weight: var(--font-medium);
}

/* 响应式 */
@media (max-width: 768px) {
  .action-group {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-top {
    flex-direction: column;
  }

  .detail-tags {
    width: 100%;
  }
}
</style>
