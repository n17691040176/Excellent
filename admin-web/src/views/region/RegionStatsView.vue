<template>
  <div class="region-view">
    <div class="page-heading">
      <div>
        <h2>区域订单奖励</h2>
        <p>管理区代理、市代理的订单奖励比例，查询订单奖励发放明细。</p>
      </div>
      <el-button type="primary" @click="loadData">刷新数据</el-button>
    </div>

    <!-- 统计概览 -->
    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="split-layout">
      <!-- 代理申请管理 -->
      <div class="panel-card data-card block-gap">
        <div class="section-title">
          <div>
            <h3>区域代理申请</h3>
            <p>审核区代理、市代理申请并配置区域订单奖励比例。</p>
          </div>
        </div>

        <div class="toolbar-row toolbar-wrap">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索省份 / 城市 / 区县"
            clearable
            style="max-width: 200px;"
            @keyup.enter="loadAgents(1)"
          />
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px;">
            <el-option label="待审核" value="PENDING" />
            <el-option label="已通过" value="APPROVED" />
            <el-option label="已过期" value="EXPIRED" />
          </el-select>
          <el-select v-model="filters.agentType" placeholder="代理类型" clearable style="width: 140px;">
            <el-option label="区代理" value="COUNTY_AGENT" />
            <el-option label="市代理" value="CITY_AGENT" />
          </el-select>
          <el-button type="primary" @click="loadAgents">查询</el-button>
          <el-button plain @click="resetAgentFilters">重置</el-button>
        </div>

        <el-table v-loading="loadingAgents" :data="agentRows" border>
          <el-table-column label="用户信息" min-width="180">
            <template #default="{ row }">
              <div class="cell-title">{{ row.user_nickname || `用户 ${row.user_id}` }}</div>
              <div class="cell-meta">{{ row.user_phone || `ID: ${row.user_id}` }}</div>
            </template>
          </el-table-column>
          <el-table-column label="代理区域" min-width="200">
            <template #default="{ row }">
              <div class="cell-title">{{ row.province }}</div>
              <div class="cell-meta">{{ row.city }} {{ row.district || '' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="代理类型" width="110">
            <template #default="{ row }">
              <el-tag size="small">{{ agentTypeLabel(row.agent_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="奖励比例" width="100">
            <template #default="{ row }">
              <span class="rate-text">{{ row.dividend_rate || 0 }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag :type="agentStatusType(scope.row.status)" size="small">{{ agentStatusLabel(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="订单数" width="100">
            <template #default="{ row }">
              <span class="count-text">{{ row.total_orders || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="累计奖励" width="120">
            <template #default="{ row }">
              <div class="amount-primary">¥{{ formatMoney(row.total_dividend) }}</div>
            </template>
          </el-table-column>
          <el-table-column label="申请时间" width="160">
            <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button
                v-permission="'region:audit'"
                link
                type="success"
                :disabled="scope.row.status !== 'PENDING'"
                @click="auditAgent(scope.row, true)"
              >通过</el-button>
              <el-button
                v-permission="'region:audit'"
                link
                type="danger"
                :disabled="scope.row.status !== 'PENDING'"
                @click="auditAgent(scope.row, false)"
              >驳回</el-button>
              <el-button
                v-permission="'region:reward-config'"
                link
                type="primary"
                :disabled="scope.row.status !== 'APPROVED'"
                @click="openRewardConfig(scope.row)"
              >配置奖励</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="agentPage"
          v-model:page-size="agentPageSize"
          class="table-pagination"
          layout="total, prev, pager, next"
          :total="agentTotal"
          @current-change="loadAgents"
          @size-change="handleAgentPageSizeChange"
        />
      </div>

      <!-- 奖励记录 -->
      <div class="panel-card data-card block-gap">
        <div class="section-title">
          <div>
            <h3>奖励发放记录</h3>
            <p>查看每笔区域订单奖励的代理会员、计算比例和到账状态。</p>
          </div>
        </div>

        <div class="toolbar-row toolbar-wrap">
          <el-input v-model="dividendFilters.keyword" placeholder="搜索订单号 / 代理" clearable style="max-width: 220px" />
          <el-select v-model="dividendFilters.status" placeholder="状态" clearable style="width: 130px">
            <el-option label="已结算" value="SETTLED" />
            <el-option label="冻结中" value="FROZEN" />
            <el-option label="已失效" value="EXPIRED" />
          </el-select>
          <el-button type="primary" @click="loadDividends(1)">查询</el-button>
        </div>

        <el-table v-loading="loadingDividends" :data="dividendRows" border>
          <el-table-column prop="order_no" label="订单号" min-width="180" />
          <el-table-column label="代理区域" min-width="180">
            <template #default="{ row }">
              <div class="cell-title">{{ row.province }}</div>
              <div class="cell-meta">{{ row.city }} {{ row.district || '' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="订单金额" width="120">
            <template #default="{ row }">
              <span class="amount-text">¥{{ formatMoney(row.order_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="奖励比例" width="100">
            <template #default="{ row }">
              <span class="rate-text">{{ Number(row.dividend_rate || 0).toFixed(2) }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="奖励金额" width="120">
            <template #default="{ row }">
              <div class="amount-primary">¥{{ formatMoney(row.dividend_amount) }}</div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag :type="dividendStatusType(scope.row.status)" size="small">{{ dividendStatusLabel(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="结算时间" width="160">
            <template #default="scope">{{ formatDate(scope.row.settled_at) }}</template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="dividendPage"
          v-model:page-size="dividendPageSize"
          class="table-pagination"
          layout="total, prev, pager, next"
          :total="dividendTotal"
          @current-change="loadDividends"
          @size-change="handleDividendPageSizeChange"
        />
      </div>
    </div>

    <!-- 审核对话框 -->
    <el-dialog v-model="auditDialogVisible" title="区域代理审核" width="480px" destroy-on-close>
      <el-form :model="auditForm" label-width="100px">
        <el-form-item label="代理区域">
          <span>{{ currentAuditRow?.province }} {{ currentAuditRow?.city }} {{ currentAuditRow?.district }}</span>
        </el-form-item>
        <el-form-item label="代理类型">
          <el-tag>{{ agentTypeLabel(currentAuditRow?.agent_type) }}</el-tag>
        </el-form-item>
        <el-form-item label="订单奖励比例">
          <el-input-number v-model="auditForm.dividendRate" :min="0" :max="100" :precision="1" />
          <span class="unit">%</span>
        </el-form-item>
        <el-form-item label="审核备注">
          <el-input v-model="auditForm.remark" type="textarea" :rows="3" placeholder="填写审核备注（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="auditDialogVisible = false">取消</el-button>
        <el-button v-if="currentAuditRow?.status === 'PENDING'" type="success" @click="confirmAudit(true)">通过</el-button>
        <el-button v-if="currentAuditRow?.status === 'PENDING'" type="danger" @click="confirmAudit(false)">驳回</el-button>
        <el-button v-else type="primary" @click="confirmAudit(true)">保存比例</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

import { regionApi } from '@/api/modules'

const loading = ref(false)
const loadingAgents = ref(false)
const loadingDividends = ref(false)

// 统计数据
const summary = ref({})

// 代理列表
const agentRows = ref([])
const agentTotal = ref(0)
const filters = ref({
  keyword: '',
  status: '',
  agentType: ''
})
const agentPage = ref(1)
const agentPageSize = ref(10)

// 分红记录
const dividendRows = ref([])
const dividendTotal = ref(0)
const dividendPage = ref(1)
const dividendPageSize = ref(10)
const dividendFilters = ref({ keyword: '', status: '' })

// 审核对话框
const auditDialogVisible = ref(false)
const currentAuditRow = ref(null)
const auditForm = ref({
  dividendRate: 5,
  remark: ''
})

const metrics = computed(() => [
  { label: '区域代理', value: summary.value.total_agents || 0, subtext: '已生效代理' },
  { label: '待审核', value: summary.value.pending_count || 0, subtext: '申请待处理' },
  { label: '奖励记录', value: summary.value.total_dividend_records || 0, subtext: '累计笔数' },
  { label: '累计奖励', value: '¥' + (summary.value.total_dividend_amount || 0), subtext: '已到账金额' }
])

function formatDate(value) {
  if (!value) return '--'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function agentTypeLabel(value) {
  return { COUNTY_AGENT: '区代理', CITY_AGENT: '市代理' }[value] || value || '--'
}

function agentStatusLabel(value) {
  return { PENDING: '待审核', APPROVED: '已通过', REJECTED: '已驳回', EXPIRED: '已过期' }[value] || value || '--'
}

function agentStatusType(status) {
  return { PENDING: 'warning', APPROVED: 'success', REJECTED: 'danger', EXPIRED: 'info' }[status] || 'info'
}

function dividendStatusLabel(value) {
  return { FROZEN: '冻结中', SETTLED: '已结算', EXPIRED: '已过期' }[value] || value || '--'
}

function dividendStatusType(status) {
  return { FROZEN: 'warning', SETTLED: 'success', EXPIRED: 'info' }[status] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    summary.value = await regionApi.summary()
    await Promise.all([loadAgents(), loadDividends()])
  } finally {
    loading.value = false
  }
}

async function loadAgents(nextPage = agentPage.value) {
  loadingAgents.value = true
  try {
    agentPage.value = nextPage
    const params = {
      keyword: filters.value.keyword || undefined,
      status: filters.value.status || undefined,
      agent_type: filters.value.agentType || undefined,
      page: agentPage.value,
      page_size: agentPageSize.value
    }
    const res = await regionApi.agents(params)
    agentRows.value = res.items || []
    agentTotal.value = res.total || 0
  } finally {
    loadingAgents.value = false
  }
}

async function loadDividends(nextPage = dividendPage.value) {
  loadingDividends.value = true
  try {
    dividendPage.value = nextPage
    const res = await regionApi.dividends({
      keyword: dividendFilters.value.keyword || undefined,
      status: dividendFilters.value.status || undefined,
      page: dividendPage.value,
      page_size: dividendPageSize.value
    })
    dividendRows.value = res.items || []
    dividendTotal.value = res.total || 0
  } finally {
    loadingDividends.value = false
  }
}

function resetAgentFilters() {
  filters.value = { keyword: '', status: '', agentType: '' }
  agentPage.value = 1
  loadAgents()
}

function handleAgentPageSizeChange() {
  agentPage.value = 1
  loadAgents(1)
}

function handleDividendPageSizeChange() {
  dividendPage.value = 1
  loadDividends(1)
}

function auditAgent(row) {
  currentAuditRow.value = row
  auditForm.value = {
    dividendRate: row.dividend_rate ?? 0,
    remark: ''
  }
  auditDialogVisible.value = true
}

function openRewardConfig(row) {
  auditAgent(row)
}

async function confirmAudit(approved) {
  try {
    if (currentAuditRow.value.status === 'PENDING') {
      await regionApi.auditAgent(currentAuditRow.value.id, {
        approved,
        remark: auditForm.value.remark || undefined,
        dividend_rate: approved ? auditForm.value.dividendRate : undefined
      })
    } else {
      await regionApi.updateRewardConfig(currentAuditRow.value.id, {
        dividend_rate: auditForm.value.dividendRate
      })
    }
    ElMessage.success(currentAuditRow.value.status === 'PENDING' ? (approved ? '已通过审核' : '已驳回申请') : '奖励比例已更新')
    auditDialogVisible.value = false
    await loadAgents()
    await loadData()
  } catch (error) {
    // error handled by interceptor
  }
}

onMounted(loadData)
</script>

<style scoped>
.region-view {
  display: grid;
  gap: 18px;
}

.block-gap {
  margin-top: 18px;
}

.split-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.toolbar-wrap {
  flex-wrap: wrap;
}

.cell-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.cell-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.amount-text {
  font-size: 14px;
  color: var(--text-primary);
}

.amount-primary {
  font-size: 15px;
  font-weight: 700;
  color: var(--primary-deep);
}

.rate-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.count-text {
  font-size: 14px;
  font-weight: 600;
}

.unit {
  margin-left: 8px;
  color: var(--text-secondary);
}

.table-pagination {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}
</style>
