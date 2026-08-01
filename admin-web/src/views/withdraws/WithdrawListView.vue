<template>
  <div class="withdraw-view">
    <!-- 统一页面头部 -->
    <PageHeader title="提现管理" :description="scopeHint">
      <template #actions>
        <el-button plain @click="resetFilters">重置筛选</el-button>
        <el-button type="primary" @click="loadData">刷新列表</el-button>
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
      <!-- 筛选栏 -->
      <FilterBar
        :fields="filterFields"
        v-model="filters"
        @search="handleSearch"
        @reset="handleReset"
      />

      <!-- 数据表格 -->
      <el-table v-loading="loading" :data="pagedRows" border>
        <el-table-column prop="id" label="申请 ID" width="90" />
        <el-table-column label="用户信息" min-width="160">
          <template #default="{ row }">
            <div class="cell-title">{{ row.user_nickname || `ID: ${row.user_id}` }}</div>
            <div class="cell-meta">{{ row.user_phone || '--' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="team_name" label="团队" min-width="140" show-overflow-tooltip />
        <el-table-column label="提现类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ withdrawTypeLabel(row.withdraw_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提现金额" width="130">
          <template #default="{ row }">
            <div class="amount-text">¥{{ formatMoney(row.amount) }}</div>
            <div v-if="row.voucher_amount > 0" class="cell-meta">含消费金 ¥{{ formatMoney(row.voucher_amount) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="实际到账" width="120">
          <template #default="{ row }">
            <div class="amount-primary">¥{{ formatMoney(row.net_amount) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="110">
          <template #default="scope">
            <StatusTag :type="statusType(scope.row.status)" size="small">{{ statusLabel(scope.row.status) }}</StatusTag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="申请备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="remark-text">{{ row.remark || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="review_remark" label="审核备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="review-remark">{{ row.review_remark || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="申请时间" width="160">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="审核时间" width="160">
          <template #default="scope">{{ formatDate(scope.row.reviewed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <div class="action-group">
              <el-button
                v-permission="'withdraws:review'"
                link
                type="success"
                :disabled="scope.row.status !== 'PENDING'"
                @click="review(scope.row, 'approve')"
              >通过</el-button>
              <el-button
                v-permission="'withdraws:review'"
                link
                type="danger"
                :disabled="scope.row.status !== 'PENDING'"
                @click="review(scope.row, 'reject')"
              >驳回</el-button>
              <el-button
                v-permission="'withdraws:pay'"
                link
                type="primary"
                :disabled="scope.row.status !== 'APPROVED'"
                @click="pay(scope.row)"
              >打款</el-button>
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
        :total="filteredRows.length"
        @size-change="handlePageSizeChange"
      />
    </div>

    <!-- 审核对话框 -->
    <el-dialog
      v-model="reviewDialogVisible"
      :title="reviewAction === 'approve' ? '通过提现申请' : '驳回提现申请'"
      width="480px"
      destroy-on-close
    >
      <el-form :model="reviewForm" label-width="90px">
        <el-form-item label="申请用户">
          <span>{{ currentReviewRow?.user_nickname || `ID: ${currentReviewRow?.user_id}` }}</span>
        </el-form-item>
        <el-form-item label="提现金额">
          <span class="amount-primary">¥{{ formatMoney(currentReviewRow?.amount) }}</span>
        </el-form-item>
        <el-form-item label="审核备注">
          <el-input
            v-model="reviewForm.remark"
            type="textarea"
            :rows="3"
            :placeholder="reviewAction === 'approve' ? '填写打款备注（选填）' : '填写驳回原因（必填）'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button :type="reviewAction === 'approve' ? 'success' : 'danger'" @click="confirmReview">
          {{ reviewAction === 'approve' ? '确认通过' : '确认驳回' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { commissionApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { formatDateTime, isDateTimeInShanghaiDateRange } from '@/utils/datetime'
import { PageHeader, MetricCard, FilterBar, StatusTag } from '@/components/common'

const userStore = useUserStore()

const loading = ref(false)
const rows = ref([])
const page = ref(1)
const pageSize = ref(20)

// 筛选表单
const filters = ref({
  keyword: '',
  status: '',
  withdraw_type: '',
  dateRange: []
})

// 审核对话框
const reviewDialogVisible = ref(false)
const reviewAction = ref('approve')
const currentReviewRow = ref(null)
const reviewForm = ref({ remark: '' })

const withdrawTypeOptions = [
  { label: '佣金提现', value: 'COMMISSION' },
  { label: '余额提现', value: 'BALANCE' },
  { label: '积分提现', value: 'POINTS' }
]

const statusOptions = [
  { label: '待审核', value: 'PENDING' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '已打款', value: 'PAID' }
]

// 筛选字段配置
const filterFields = [
  { key: 'keyword', type: 'input', placeholder: '搜索用户 ID / 手机号 / 备注', width: 220 },
  { key: 'status', type: 'select', label: '审核状态', options: statusOptions, width: 130 },
  { key: 'withdraw_type', type: 'select', label: '提现类型', options: withdrawTypeOptions, width: 140 },
  { key: 'dateRange', type: 'dateRange', label: '申请时间', width: 260 }
]

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '当前仅处理所属团队用户发起的提现申请，避免跨团队误审。'
    : '集中处理平台佣金、余额、积分提现申请，避免资金流审核滞后。'
)

const metrics = computed(() => {
  const pending = rows.value.filter((item) => item.status === 'PENDING')
  const pendingAmount = pending.reduce((sum, item) => sum + Number(item.amount || 0), 0)
  const approved = rows.value.filter((item) => item.status === 'APPROVED')
  const approvedAmount = approved.reduce((sum, item) => sum + Number(item.amount || 0), 0)
  return [
    { label: '待审申请', value: pending.length, subtext: `待处理 ¥${pendingAmount.toFixed(2)}`, variant: 'warning' },
    { label: '已通过', value: approved.length, subtext: `待打款 ¥${approvedAmount.toFixed(2)}`, variant: 'success' },
    { label: '已驳回', value: rows.value.filter((item) => item.status === 'REJECTED').length, subtext: '请关注复审', variant: 'danger' },
    { label: '累计提现', value: rows.value.reduce((sum, item) => sum + Number(item.amount || 0), 0).toFixed(2), subtext: '含各类提现', variant: 'neutral' }
  ]
})

const filteredRows = computed(() => {
  const term = filters.value.keyword?.trim() || ''
  return rows.value.filter((item) => {
    const hitKeyword =
      !term ||
      String(item.user_id).includes(term) ||
      (item.user_phone || '').includes(term) ||
      (item.remark || '').includes(term)
    const hitStatus = !filters.value.status || item.status === filters.value.status
    const hitType = !filters.value.withdraw_type || item.withdraw_type === filters.value.withdraw_type
    const hitDate =
      !filters.value.dateRange?.length ||
      isDateTimeInShanghaiDateRange(item.created_at, filters.value.dateRange[0], filters.value.dateRange[1])
    return hitKeyword && hitStatus && hitType && hitDate
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

function formatDate(value) {
  return formatDateTime(value)
}

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function withdrawTypeLabel(value) {
  return withdrawTypeOptions.find((item) => item.value === value)?.label || value || '--'
}

function statusLabel(value) {
  return statusOptions.find((item) => item.value === value)?.label || value || '--'
}

function statusType(status) {
  return {
    PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'danger',
    PAID: 'primary'
  }[status] || 'default'
}

async function loadData() {
  loading.value = true
  try {
    rows.value = await commissionApi.withdraws()
  } finally {
    loading.value = false
  }
}

async function review(row, action) {
  reviewAction.value = action
  currentReviewRow.value = row
  reviewForm.value = { remark: '' }
  reviewDialogVisible.value = true
}

async function confirmReview() {
  if (reviewAction.value === 'reject' && !reviewForm.value.remark.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }

  try {
    if (reviewAction.value === 'approve') {
      await commissionApi.approveWithdraw(currentReviewRow.value.id)
      ElMessage.success('已通过提现申请')
    } else {
      await commissionApi.rejectWithdraw(currentReviewRow.value.id, reviewForm.value.remark)
      ElMessage.success('已驳回提现申请')
    }
    reviewDialogVisible.value = false
    await loadData()
  } catch (error) {
    // error handled by interceptor
  }
}

async function pay(row) {
  await ElMessageBox.confirm(`确认向用户 ${row.user_nickname || row.user_id} 打款 ¥${row.net_amount || row.amount} 吗？`, '确认打款', {
    type: 'warning'
  })
  try {
    await commissionApi.payWithdraw(row.id)
    ElMessage.success('打款成功')
    await loadData()
  } catch (error) {
    // error handled by interceptor
  }
}

function handleSearch() {
  page.value = 1
}

function handleReset() {
  filters.value = {
    keyword: '',
    status: '',
    withdraw_type: '',
    dateRange: []
  }
  page.value = 1
}

function handlePageSizeChange() {
  page.value = 1
}

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.withdraw-view {
  display: grid;
  gap: var(--space-4);
}

.data-card {
  padding: var(--space-5);
}

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

.amount-text {
  font-size: var(--text-base);
  color: var(--text-primary);
}

.amount-primary {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--primary-deep);
}

.remark-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.review-remark {
  font-size: var(--text-sm);
  color: var(--primary-deep);
}

.table-pagination {
  margin-top: var(--space-5);
  justify-content: flex-end;
}

.action-group {
  display: flex;
  gap: var(--space-1);
}
</style>
