<template>
  <div class="orders-view">
    <div class="page-heading">
      <div>
        <h2>订单管理</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <div class="toolbar-row">
        <el-button plain @click="resetFilters">重置筛选</el-button>
        <el-button type="primary" @click="loadData">刷新订单</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="panel-card data-card block-gap">
      <div class="toolbar-row toolbar-wrap">
        <el-input
          v-model="filters.keyword"
          clearable
          placeholder="搜索订单号 / 用户昵称 / 手机号"
          style="max-width: 280px;"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="filters.order_status" clearable placeholder="订单状态" style="width: 160px;">
          <el-option v-for="item in orderStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.pay_status" clearable placeholder="支付状态" style="width: 160px;">
          <el-option v-for="item in payStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.order_type" clearable placeholder="订单类型" style="width: 180px;">
          <el-option v-for="item in orderTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.zone_type" clearable placeholder="业务专区" style="width: 170px;">
          <el-option v-for="item in zoneTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button plain @click="handleSearch">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border>
        <el-table-column prop="order_no" label="订单号" min-width="180" />
        <el-table-column label="用户信息" min-width="180">
          <template #default="{ row }">
            <div class="cell-title">{{ row.user_nickname || '--' }}</div>
            <div class="cell-meta">{{ row.user_phone || '--' }}</div>
            <div class="cell-meta">{{ row.team_name || '未绑定团队' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单类型" min-width="160">
          <template #default="{ row }">
            <el-tag size="small">{{ orderTypeLabel(row.order_type) }}</el-tag>
            <div class="cell-meta">{{ zoneTypeLabel(row.zone_type) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="商品摘要" min-width="240">
          <template #default="{ row }">
            <div class="cell-title">{{ row.title || '--' }}</div>
            <div class="cell-meta">{{ row.products_summary || '--' }}</div>
            <div class="cell-meta">商品数 {{ row.item_count || 0 }}</div>
          </template>
        </el-table-column>
        <el-table-column label="金额" min-width="150">
          <template #default="{ row }">
            <div>总额 {{ formatMoney(row.total_amount) }}</div>
            <div class="cell-meta">优惠 {{ formatMoney(row.discount_amount) }}</div>
            <div class="cell-meta">待付 {{ formatMoney(row.payable_amount) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单状态" width="120">
          <template #default="{ row }">
            <el-tag :type="orderStatusType(row.order_status)">{{ row.status_text || row.order_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付状态" width="120">
          <template #default="{ row }">
            <el-tag :type="payStatusType(row.pay_status)">{{ payStatusLabel(row.pay_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物流状态" min-width="160">
          <template #default="{ row }">
            <el-tag :type="deliveryTagType(row.delivery_status)">{{ row.delivery_status_text }}</el-tag>
            <div class="cell-meta">{{ row.tracking_no || '无需物流' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-permission="'orders:manage'"
              link
              type="success"
              :disabled="row.pay_status === 'PAID' || row.order_status === 'CLOSED'"
              @click="handleAction(row, 'pay')"
            >
              置为已支付
            </el-button>
            <el-button
              v-permission="'orders:manage'"
              link
              type="warning"
              :disabled="!row.can_confirm"
              @click="handleAction(row, 'confirm')"
            >
              确认完成
            </el-button>
            <el-button
              v-permission="'orders:manage'"
              link
              type="danger"
              :disabled="row.order_status === 'CLOSED' || row.order_status === 'CONFIRMED' || row.pay_status === 'PAID'"
              @click="handleAction(row, 'close')"
            >
              关闭订单
            </el-button>
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

    <el-drawer v-model="detailVisible" title="订单详情" size="960px" destroy-on-close>
      <div v-loading="detailLoading" class="detail-layout">
        <template v-if="detail">
          <div class="panel-card data-card">
            <div class="detail-top">
              <div>
                <div class="detail-title">{{ detail.title || detail.order_no }}</div>
                <div class="cell-meta">订单号 {{ detail.order_no }}</div>
              </div>
              <div class="detail-tags">
                <el-tag :type="orderStatusType(detail.order_status)">{{ detail.status_text || detail.order_status }}</el-tag>
                <el-tag :type="payStatusType(detail.pay_status)">{{ payStatusLabel(detail.pay_status) }}</el-tag>
                <el-tag :type="deliveryTagType(detail.delivery_status)">{{ detail.delivery_status_text }}</el-tag>
              </div>
            </div>

            <el-descriptions :column="2" border class="detail-desc">
              <el-descriptions-item label="用户">{{ detail.user?.nickname || '--' }} / {{ detail.user?.phone || '--' }}</el-descriptions-item>
              <el-descriptions-item label="团队">{{ detail.team?.name || '未绑定团队' }}</el-descriptions-item>
              <el-descriptions-item label="订单类型">{{ orderTypeLabel(detail.order_type) }}</el-descriptions-item>
              <el-descriptions-item label="业务专区">{{ zoneTypeLabel(detail.zone_type) }}</el-descriptions-item>
              <el-descriptions-item label="支付组合">{{ detail.payment_combo || '--' }}</el-descriptions-item>
              <el-descriptions-item label="物流方式">{{ detail.delivery_mode_text || '无需物流' }}</el-descriptions-item>
              <el-descriptions-item label="总金额">{{ formatMoney(detail.total_amount) }}</el-descriptions-item>
              <el-descriptions-item label="优惠金额">{{ formatMoney(detail.discount_amount) }}</el-descriptions-item>
              <el-descriptions-item label="待支付">{{ formatMoney(detail.payable_amount) }}</el-descriptions-item>
              <el-descriptions-item label="已支付">{{ formatMoney(detail.paid_amount) }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(detail.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatDate(detail.updated_at) }}</el-descriptions-item>
              <el-descriptions-item label="支付时间">{{ formatDate(detail.paid_at) }}</el-descriptions-item>
              <el-descriptions-item label="完成时间">{{ formatDate(detail.confirmed_at) }}</el-descriptions-item>
              <el-descriptions-item label="物流单号" :span="2">{{ detail.tracking_no || '无需物流' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="split-grid block-gap">
            <div class="panel-card data-card">
              <div class="section-title">
                <div>
                  <h3>订单商品</h3>
                  <p>与移动端订单详情保持同一组商品明细。</p>
                </div>
              </div>
              <el-table :data="detail.items || []" border>
                <el-table-column prop="product_name" label="商品名称" min-width="220" />
                <el-table-column prop="quantity" label="数量" width="90" />
                <el-table-column label="单价" width="120">
                  <template #default="{ row }">{{ formatMoney(row.unit_price) }}</template>
                </el-table-column>
                <el-table-column label="小计" width="120">
                  <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
                </el-table-column>
              </el-table>
            </div>

            <div class="panel-card data-card">
              <div class="section-title">
                <div>
                  <h3>物流轨迹</h3>
                  <p>直接对齐移动端物流详情页时间轴。</p>
                </div>
              </div>
              <div class="timeline-list">
                <div v-for="item in detail.shipment?.timeline || detail.timeline || []" :key="`${item.title}-${item.time}`" class="timeline-item">
                  <div class="timeline-dot" :class="{ active: item.active }"></div>
                  <div>
                    <div class="cell-title">{{ item.title }}</div>
                    <div class="cell-meta">{{ formatDate(item.time) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { orderApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const loading = ref(false)
const detailLoading = ref(false)
const detailVisible = ref(false)
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
  { label: '待支付', value: 'CREATED' },
  { label: '已支付', value: 'PAID' },
  { label: '已完成', value: 'CONFIRMED' },
  { label: '已关闭', value: 'CLOSED' },
  { label: '已退款', value: 'REFUNDED' }
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

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '按移动端订单链路统一后台视角，当前仅展示所属团队订单。'
    : '按移动端订单、支付与物流字段统一后台管理接口。'
)

const metrics = computed(() => {
  const currentRows = rows.value
  return [
    { label: '当前结果', value: total.value, subtext: `本页 ${currentRows.length} 条订单` },
    { label: '待支付', value: currentRows.filter((item) => item.order_status === 'CREATED').length, subtext: '可人工补记支付或继续跟单' },
    { label: '运输中', value: currentRows.filter((item) => item.delivery_status === 'shipping').length, subtext: '移动端物流页展示中' },
    { label: '已完成', value: currentRows.filter((item) => item.order_status === 'CONFIRMED').length, subtext: '已完成收货或服务履约' }
  ]
})

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
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
    CREATED: 'warning',
    PAID: 'primary',
    CONFIRMED: 'success',
    CLOSED: 'info',
    REFUNDED: 'danger'
  }[status] || 'info'
}

function payStatusType(status) {
  return {
    UNPAID: 'info',
    PAID: 'success',
    REFUNDED: 'danger'
  }[status] || 'info'
}

function deliveryTagType(status) {
  return {
    pending: 'warning',
    shipping: 'primary',
    delivered: 'success',
    not_required: 'info'
  }[status] || 'info'
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
  await loadDetail(row.id)
}

async function handleAction(row, action) {
  const actionMap = {
    pay: { label: '置为已支付', request: () => orderApi.markPaid(row.id) },
    confirm: { label: '确认完成', request: () => orderApi.confirm(row.id) },
    close: { label: '关闭订单', request: () => orderApi.close(row.id) }
  }
  const target = actionMap[action]
  if (!target) return
  await ElMessageBox.confirm(`确认${target.label} ${row.order_no} 吗？`, '订单操作', { type: 'warning' })
  await target.request()
  ElMessage.success(`${target.label}成功`)
  await loadData()
  if (detailVisible.value && detail.value?.id === row.id) {
    await loadDetail(row.id)
  }
}

function handleSearch() {
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
.orders-view {
  display: grid;
  gap: 18px;
}

.block-gap {
  margin-top: 18px;
}

.toolbar-wrap {
  flex-wrap: wrap;
}

.table-pagination {
  margin-top: 18px;
  justify-content: flex-end;
}

.cell-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand-deep);
}

.cell-meta {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(58, 45, 36, 0.68);
}

.detail-layout {
  display: grid;
  gap: 18px;
}

.detail-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.detail-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--brand-deep);
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.detail-desc {
  margin-top: 18px;
}

.timeline-list {
  display: grid;
  gap: 14px;
}

.timeline-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 5px;
  background: rgba(198, 132, 79, 0.22);
}

.timeline-dot.active {
  background: var(--brand-primary);
}
</style>
