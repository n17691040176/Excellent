<template>
  <div class="withdraw-view">
    <div class="page-heading">
      <div>
        <h2>提现管理</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <el-button type="primary" @click="loadData">刷新列表</el-button>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="panel-card data-card block-gap">
      <div class="toolbar-row">
        <el-input v-model="keyword" placeholder="搜索用户 ID / 备注" clearable style="max-width: 260px;" />
        <el-select v-model="statusFilter" placeholder="审核状态" clearable style="width: 180px;">
          <el-option label="待审核" value="PENDING" />
          <el-option label="已通过" value="APPROVED" />
          <el-option label="已驳回" value="REJECTED" />
          <el-option label="已打款" value="PAID" />
        </el-select>
        <el-select v-model="typeFilter" placeholder="提现类型" clearable style="width: 180px;">
          <el-option label="佣金提现" value="COMMISSION" />
          <el-option label="余额提现" value="BALANCE" />
          <el-option label="积分提现" value="POINTS" />
        </el-select>
      </div>

      <el-table :data="pagedRows" border>
        <el-table-column prop="id" label="申请 ID" width="100" />
        <el-table-column prop="user_id" label="用户 ID" width="100" />
        <el-table-column prop="team_id" label="团队 ID" width="100" />
        <el-table-column prop="withdraw_type" label="提现类型" min-width="120" />
        <el-table-column prop="amount" label="提现金额" min-width="120" />
        <el-table-column prop="net_amount" label="实际到账" min-width="120" />
        <el-table-column prop="voucher_amount" label="转消费金" min-width="120" />
        <el-table-column label="审核状态" width="120">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="申请备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="申请时间" min-width="170">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="审核时间" min-width="170">
          <template #default="scope">{{ formatDate(scope.row.reviewed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
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
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="total, prev, pager, next"
        :total="filteredRows.length"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessageBox } from 'element-plus'

import { commissionApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const rows = ref([])
const keyword = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const page = ref(1)
const pageSize = ref(10)

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '当前仅处理所属团队用户发起的提现申请，避免跨团队误审。'
    : '集中处理平台佣金、余额、积分提现申请，避免资金流审核滞后。'
)

const metrics = computed(() => {
  const pendingAmount = rows.value
    .filter((item) => item.status === 'PENDING')
    .reduce((sum, item) => sum + Number(item.amount || 0), 0)
  return [
    { label: '待审申请', value: rows.value.filter((item) => item.status === 'PENDING').length, subtext: `待处理金额 ${pendingAmount.toFixed(2)}` },
    { label: '已通过申请', value: rows.value.filter((item) => item.status === 'APPROVED').length, subtext: '等待打款或已入账' },
    { label: '已驳回申请', value: rows.value.filter((item) => item.status === 'REJECTED').length, subtext: '请关注备注与复审' },
    { label: '累计提现金额', value: rows.value.reduce((sum, item) => sum + Number(item.amount || 0), 0).toFixed(2), subtext: '包含佣金、余额、积分' }
  ]
})

const filteredRows = computed(() => {
  const term = keyword.value.trim()
  return rows.value.filter((item) => {
    const hitKeyword = !term || String(item.user_id).includes(term) || (item.remark || '').includes(term)
    const hitStatus = !statusFilter.value || item.status === statusFilter.value
    const hitType = !typeFilter.value || item.withdraw_type === typeFilter.value
    return hitKeyword && hitStatus && hitType
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

function statusType(status) {
  return {
    PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'danger',
    PAID: 'primary'
  }[status] || 'info'
}

async function loadData() {
  rows.value = await commissionApi.withdraws()
}

async function review(row, action) {
  const actionText = action === 'approve' ? '通过' : '驳回'
  await ElMessageBox.confirm(`确认${actionText}该提现申请吗？`, '提现审核', { type: 'warning' })
  if (action === 'approve') {
    await commissionApi.approveWithdraw(row.id)
  } else {
    await commissionApi.rejectWithdraw(row.id)
  }
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.withdraw-view {
  display: grid;
  gap: 18px;
}

.block-gap {
  margin-top: 18px;
}
</style>
