<template>
  <div class="withdraw-view">
    <PageHeader title="提现管理" :description="scopeHint">
      <template #actions>
        <el-button v-if="userStore.role === 'SUPER_ADMIN'" :icon="Setting" plain @click="openConfig">手续费配置</el-button>
        <el-button v-permission="'withdraws:export'" :icon="Download" type="success" plain :loading="exporting" @click="exportExcel">导出打款清单</el-button>
        <el-button :icon="Refresh" type="primary" @click="loadData">刷新</el-button>
      </template>
    </PageHeader>

    <div class="metric-grid">
      <MetricCard v-for="item in metrics" :key="item.label" v-bind="item" />
    </div>

    <div class="panel-card data-card">
      <FilterBar :fields="filterFields" v-model="filters" @search="handleSearch" @reset="handleReset" />

      <el-table v-loading="loading" :data="rows" border>
        <el-table-column prop="source_no" label="提现单号" width="130" />
        <el-table-column label="用户信息" min-width="150">
          <template #default="{ row }">
            <div class="cell-title">{{ row.user_nickname || `ID: ${row.user_id}` }}</div>
            <div class="cell-meta">{{ row.user_phone || '--' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="team_name" label="团队" min-width="120" show-overflow-tooltip />
        <el-table-column label="收款银行卡" min-width="220">
          <template #default="{ row }">
            <div class="cell-title">{{ row.bank_name || '--' }} · {{ row.bank_holder_name || '--' }}</div>
            <div class="cell-meta">{{ row.masked_bank_card_number || '--' }}</div>
            <div v-if="row.bank_branch_name" class="cell-meta">{{ row.bank_branch_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="申请金额" width="115">
          <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="手续费" width="120">
          <template #default="{ row }">
            <div>¥{{ formatMoney(row.fee_amount) }}</div>
            <div class="cell-meta">{{ formatMoney(row.fee_rate) }}%</div>
          </template>
        </el-table-column>
        <el-table-column label="实际打款" width="125">
          <template #default="{ row }"><span class="amount-primary">¥{{ formatMoney(row.net_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><StatusTag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</StatusTag></template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.remark || '--' }}</div>
            <div v-if="row.review_remark" class="review-remark">审核：{{ row.review_remark }}</div>
          </template>
        </el-table-column>
        <el-table-column label="申请时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button v-permission="'withdraws:review'" link type="success" :disabled="row.status !== 'PENDING'" @click="review(row, 'approve')">通过</el-button>
              <el-button v-permission="'withdraws:review'" link type="danger" :disabled="row.status !== 'PENDING'" @click="review(row, 'reject')">驳回</el-button>
              <el-button v-permission="'withdraws:pay'" link type="primary" :disabled="row.status !== 'APPROVED'" @click="pay(row)">确认打款</el-button>
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

    <el-dialog v-model="reviewDialogVisible" :title="reviewAction === 'approve' ? '通过提现申请' : '驳回提现申请'" width="480px" destroy-on-close>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="申请用户">{{ currentReviewRow?.user_nickname || currentReviewRow?.user_id }}</el-descriptions-item>
        <el-descriptions-item label="收款账户">{{ currentReviewRow?.bank_name }} {{ currentReviewRow?.masked_bank_card_number }}</el-descriptions-item>
        <el-descriptions-item label="实际打款"><span class="amount-primary">¥{{ formatMoney(currentReviewRow?.net_amount) }}</span></el-descriptions-item>
      </el-descriptions>
      <el-input v-model="reviewForm.remark" class="dialog-remark" type="textarea" :rows="3" :placeholder="reviewAction === 'approve' ? '审核备注（选填）' : '驳回原因（必填）'" />
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button :type="reviewAction === 'approve' ? 'success' : 'danger'" @click="confirmReview">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="configDialogVisible" title="佣金提现配置" width="460px">
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="手续费率">
          <el-input-number v-model="configForm.fee_rate" :min="0" :max="100" :precision="2" :step="0.1" />
          <span class="unit">%</span>
        </el-form-item>
        <el-form-item label="单笔最低金额"><el-input-number v-model="configForm.min_amount" :min="0.01" :precision="2" /></el-form-item>
        <el-form-item label="单笔最高金额"><el-input-number v-model="configForm.max_amount" :min="0.01" :precision="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Download, Refresh, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { commissionApi } from '@/api/modules'
import { PageHeader, MetricCard, FilterBar, StatusTag } from '@/components/common'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/datetime'

const userStore = useUserStore()
const loading = ref(false)
const exporting = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = ref({ keyword: '', status: '', dateRange: [] })
const reviewDialogVisible = ref(false)
const reviewAction = ref('approve')
const currentReviewRow = ref(null)
const reviewForm = ref({ remark: '' })
const configDialogVisible = ref(false)
const configForm = ref({ fee_rate: 0, min_amount: 1, max_amount: 50000 })

const statusOptions = [
  { label: '待审核', value: 'PENDING' },
  { label: '待打款', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '已打款', value: 'PAID' }
]
const filterFields = [
  { key: 'keyword', type: 'input', placeholder: '提现单号 / 用户 / 手机号 / 持卡人', width: 260 },
  { key: 'status', type: 'select', label: '状态', options: statusOptions, width: 130 },
  { key: 'dateRange', type: 'dateRange', label: '申请时间', width: 260 }
]
const scopeHint = computed(() => userStore.role === 'TEAM_ADMIN' ? '审核本团队佣金提现，财务打款后确认完成。' : '审核平台佣金提现并导出财务打款清单。')
const metrics = computed(() => {
  const pending = rows.value.filter((item) => item.status === 'PENDING')
  const approved = rows.value.filter((item) => item.status === 'APPROVED')
  return [
    { label: '当前页待审核', value: pending.length, subtext: `¥${sumAmount(pending, 'amount')}`, variant: 'warning' },
    { label: '当前页待打款', value: approved.length, subtext: `¥${sumAmount(approved, 'net_amount')}`, variant: 'success' },
    { label: '当前页手续费', value: `¥${sumAmount(rows.value, 'fee_amount')}`, subtext: '按申请时费率锁定', variant: 'primary' },
    { label: '筛选结果', value: total.value, subtext: '仅佣金提现', variant: 'neutral' }
  ]
})

function formatMoney(value) { return Number(value || 0).toFixed(2) }
function formatDate(value) { return formatDateTime(value) }
function sumAmount(items, key) { return items.reduce((sum, item) => sum + Number(item[key] || 0), 0).toFixed(2) }
function statusLabel(value) { return statusOptions.find((item) => item.value === value)?.label || value || '--' }
function statusType(status) { return ({ PENDING: 'warning', APPROVED: 'success', REJECTED: 'danger', PAID: 'primary' })[status] || 'default' }
function requestParams(includePage = true) {
  const params = {
    keyword: filters.value.keyword || undefined,
    status: filters.value.status || undefined,
    start_date: filters.value.dateRange?.[0] || undefined,
    end_date: filters.value.dateRange?.[1] || undefined
  }
  if (includePage) Object.assign(params, { page: page.value, page_size: pageSize.value })
  return params
}

async function loadData() {
  loading.value = true
  try {
    const data = await commissionApi.withdraws(requestParams())
    rows.value = data?.items || []
    total.value = Number(data?.total || 0)
  } finally { loading.value = false }
}
function handleSearch() { page.value = 1; loadData() }
function handleReset() { filters.value = { keyword: '', status: '', dateRange: [] }; page.value = 1; loadData() }
function handlePageSizeChange() { page.value = 1; loadData() }
function review(row, action) { currentReviewRow.value = row; reviewAction.value = action; reviewForm.value = { remark: '' }; reviewDialogVisible.value = true }

async function confirmReview() {
  if (reviewAction.value === 'reject' && !reviewForm.value.remark.trim()) return ElMessage.warning('请填写驳回原因')
  if (reviewAction.value === 'approve') await commissionApi.approveWithdraw(currentReviewRow.value.id, reviewForm.value.remark)
  else await commissionApi.rejectWithdraw(currentReviewRow.value.id, reviewForm.value.remark)
  reviewDialogVisible.value = false
  ElMessage.success(reviewAction.value === 'approve' ? '提现申请已通过' : '提现申请已驳回')
  await loadData()
}

async function pay(row) {
  await ElMessageBox.confirm(`请确认财务已向 ${row.bank_holder_name}（${row.bank_name} ${row.masked_bank_card_number}）打款 ¥${formatMoney(row.net_amount)}。确认后佣金将计入已提现。`, '确认已打款', { type: 'warning', confirmButtonText: '确认已打款' })
  await commissionApi.payWithdraw(row.id)
  ElMessage.success('已确认打款')
  await loadData()
}

async function exportExcel() {
  exporting.value = true
  try {
    const params = requestParams(false)
    params.status = filters.value.status || 'APPROVED'
    const blob = await commissionApi.exportWithdraws(params)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `提现打款清单-${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('打款清单已导出')
  } finally { exporting.value = false }
}

async function openConfig() { configForm.value = await commissionApi.withdrawConfig(); configDialogVisible.value = true }
async function saveConfig() {
  if (Number(configForm.value.max_amount) < Number(configForm.value.min_amount)) return ElMessage.warning('最高金额不能低于最低金额')
  await commissionApi.updateWithdrawConfig(configForm.value)
  configDialogVisible.value = false
  ElMessage.success('提现配置已保存')
}

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';
.withdraw-view { display: grid; gap: var(--space-4); }
.data-card { padding: var(--space-5); }
.cell-title { font-size: var(--text-base); font-weight: var(--font-medium); color: var(--text-primary); }
.cell-meta { margin-top: 4px; font-size: var(--text-sm); color: var(--text-muted); }
.amount-primary { font-size: var(--text-base); font-weight: var(--font-bold); color: var(--primary-deep); }
.review-remark { margin-top: 4px; color: var(--primary-deep); }
.table-pagination { margin-top: var(--space-5); justify-content: flex-end; }
.action-group { display: flex; gap: var(--space-1); }
.dialog-remark { margin-top: var(--space-4); }
.unit { margin-left: 8px; color: var(--text-muted); }
</style>
