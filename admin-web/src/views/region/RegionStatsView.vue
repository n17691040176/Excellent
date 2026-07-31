<template>
  <div class="region-view">
    <div class="page-heading">
      <div>
        <h2>区域订单奖励</h2>
        <p>区域代理仅由后台配置；订单完成后按收货区域和配置比例自动发放余额奖励。</p>
      </div>
      <div class="header-actions">
        <el-button v-permission="'region:manage'" type="primary" @click="openCreateDialog">新增区域代理</el-button>
        <el-button @click="loadData">刷新数据</el-button>
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
      <div class="section-title">
        <div>
          <h3>区域代理配置</h3>
          <p>直接指定会员为区代理或市代理，并维护负责区域、有效期和订单奖励比例。</p>
        </div>
      </div>

      <div class="toolbar-row toolbar-wrap">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用户 / 手机号 / 省市区"
          clearable
          style="max-width: 260px"
          @keyup.enter="loadAgents(1)"
          @clear="loadAgents(1)"
        />
        <el-select v-model="filters.agentType" placeholder="代理类型" clearable style="width: 140px" @change="loadAgents(1)">
          <el-option label="区代理" value="COUNTY_AGENT" />
          <el-option label="市代理" value="CITY_AGENT" />
        </el-select>
        <el-button type="primary" @click="loadAgents(1)">查询</el-button>
        <el-button plain @click="resetAgentFilters">重置</el-button>
      </div>

      <el-table v-loading="loadingAgents" :data="agentRows" border>
        <el-table-column label="代理会员" min-width="180">
          <template #default="{ row }">
            <div class="cell-title">{{ row.user_nickname || `用户 ${row.user_id}` }}</div>
            <div class="cell-meta">{{ row.user_phone || `ID: ${row.user_id}` }}</div>
          </template>
        </el-table-column>
        <el-table-column label="会员等级" width="110">
          <template #default="{ row }"><el-tag size="small">{{ row.member_level_name || '--' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="代理区域" min-width="210">
          <template #default="{ row }">
            <div class="cell-title">{{ row.province }} {{ row.city }}</div>
            <div class="cell-meta">{{ row.agent_type === 'COUNTY_AGENT' ? row.district : '全市' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="代理类型" width="110">
          <template #default="{ row }">{{ agentTypeLabel(row.agent_type) }}</template>
        </el-table-column>
        <el-table-column label="奖励比例" width="110">
          <template #default="{ row }"><span class="rate-text">{{ Number(row.dividend_rate || 0).toFixed(2) }}%</span></template>
        </el-table-column>
        <el-table-column label="有效期" min-width="190">
          <template #default="{ row }">
            <div>{{ formatDate(row.effective_at) }}</div>
            <div class="cell-meta">至 {{ formatExpiry(row.expired_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="订单数" width="90">
          <template #default="{ row }">{{ row.total_orders || 0 }}</template>
        </el-table-column>
        <el-table-column label="累计奖励" width="120">
          <template #default="{ row }"><div class="amount-primary">¥{{ formatMoney(row.total_dividend) }}</div></template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="'region:manage'" link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-permission="'region:manage'" link type="danger" @click="removeAgent(row)">删除</el-button>
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
      />
    </div>

    <div class="panel-card data-card block-gap">
      <div class="section-title">
        <div>
          <h3>区域奖励发放记录</h3>
          <p>记录当前订单完成链路实际计算并发放的区代理、市代理奖励；订单退款后记录会变为已收回。</p>
        </div>
      </div>

      <div class="toolbar-row toolbar-wrap">
        <el-input
          v-model="dividendFilters.keyword"
          placeholder="搜索订单号 / 代理 / 省市区"
          clearable
          style="max-width: 280px"
          @keyup.enter="loadDividends(1)"
          @clear="loadDividends(1)"
        />
        <el-select v-model="dividendFilters.agentType" placeholder="代理类型" clearable style="width: 140px" @change="loadDividends(1)">
          <el-option label="区代理" value="COUNTY_AGENT" />
          <el-option label="市代理" value="CITY_AGENT" />
        </el-select>
        <el-select v-model="dividendFilters.status" placeholder="奖励状态" clearable style="width: 140px" @change="loadDividends(1)">
          <el-option label="已到账" value="SETTLED" />
          <el-option label="已收回" value="EXPIRED" />
        </el-select>
        <el-button type="primary" @click="loadDividends(1)">查询</el-button>
      </div>

      <el-table v-loading="loadingDividends" :data="dividendRows" border>
        <el-table-column prop="order_no" label="订单号" min-width="180" />
        <el-table-column label="代理会员" min-width="170">
          <template #default="{ row }">
            <div class="cell-title">{{ row.agent_nickname || `用户 ${row.agent_user_id}` }}</div>
            <div class="cell-meta">{{ row.agent_phone || `ID: ${row.agent_user_id}` }}</div>
          </template>
        </el-table-column>
        <el-table-column label="代理类型" width="100">
          <template #default="{ row }">{{ agentTypeLabel(row.agent_type) }}</template>
        </el-table-column>
        <el-table-column label="订单区域" min-width="190">
          <template #default="{ row }">{{ row.province }} {{ row.city }} {{ row.district || '' }}</template>
        </el-table-column>
        <el-table-column label="订单实付" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.order_amount) }}</template>
        </el-table-column>
        <el-table-column label="奖励比例" width="100">
          <template #default="{ row }">{{ Number(row.dividend_rate || 0).toFixed(2) }}%</template>
        </el-table-column>
        <el-table-column label="奖励金额" width="120">
          <template #default="{ row }"><div class="amount-primary">¥{{ formatMoney(row.dividend_amount) }}</div></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'SETTLED' ? 'success' : 'info'" size="small">
              {{ row.status === 'SETTLED' ? '已到账' : '已收回' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发放时间" width="170">
          <template #default="{ row }">{{ formatDate(row.settled_at) }}</template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="dividendPage"
        v-model:page-size="dividendPageSize"
        class="table-pagination"
        layout="total, prev, pager, next"
        :total="dividendTotal"
        @current-change="loadDividends"
      />
    </div>

    <el-dialog v-model="agentDialogVisible" :title="editingAgentId ? '编辑区域代理' : '新增区域代理'" width="560px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="代理会员" required>
          <el-select
            v-model="agentForm.userId"
            filterable
            remote
            reserve-keyword
            :remote-method="searchUsers"
            :loading="loadingUsers"
            :disabled="Boolean(editingAgentId)"
            placeholder="输入用户昵称、手机号或 ID 搜索"
            style="width: 100%"
          >
            <el-option
              v-for="item in userOptions"
              :key="item.id"
              :label="`${item.nickname || '未命名用户'} / ${item.phone || `ID ${item.id}`}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="代理类型" required>
          <el-radio-group v-model="agentForm.agentType" @change="handleAgentTypeChange">
            <el-radio value="COUNTY_AGENT">区代理</el-radio>
            <el-radio value="CITY_AGENT">市代理</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="省份" required><el-input v-model="agentForm.province" placeholder="例如：浙江省" /></el-form-item>
        <el-form-item label="城市" required><el-input v-model="agentForm.city" placeholder="例如：杭州市" /></el-form-item>
        <el-form-item v-if="agentForm.agentType === 'COUNTY_AGENT'" label="区县" required>
          <el-input v-model="agentForm.district" placeholder="例如：西湖区" />
        </el-form-item>
        <el-form-item label="奖励比例" required>
          <el-input-number v-model="agentForm.dividendRate" :min="0" :max="100" :precision="2" :step="0.1" />
          <span class="unit">%</span>
        </el-form-item>
        <el-form-item label="生效时间">
          <el-date-picker v-model="agentForm.effectiveAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="默认立即生效" style="width: 100%" />
        </el-form-item>
        <el-form-item label="失效时间">
          <el-date-picker v-model="agentForm.expiredAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="留空表示长期有效" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="agentForm.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="agentDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingAgent" @click="saveAgent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { regionApi, userApi } from '@/api/modules'

const loadingAgents = ref(false)
const loadingDividends = ref(false)
const loadingUsers = ref(false)
const savingAgent = ref(false)
const summary = ref({})
const agentRows = ref([])
const agentTotal = ref(0)
const filters = ref({ keyword: '', agentType: '' })
const agentPage = ref(1)
const agentPageSize = ref(20)
const dividendRows = ref([])
const dividendTotal = ref(0)
const dividendPage = ref(1)
const dividendPageSize = ref(20)
const dividendFilters = ref({ keyword: '', status: '', agentType: '' })
const agentDialogVisible = ref(false)
const editingAgentId = ref(null)
const userOptions = ref([])
const agentForm = ref(createEmptyForm())

const metrics = computed(() => [
  { label: '区域代理', value: summary.value.total_agents || 0, subtext: '当前生效配置' },
  { label: '区代理', value: summary.value.county_agents || 0, subtext: '按省市区匹配订单' },
  { label: '市代理', value: summary.value.city_agents || 0, subtext: '按省市匹配订单' },
  { label: '累计区域奖励', value: `¥${formatMoney(summary.value.total_dividend_amount)}`, subtext: `已到账 ${summary.value.total_dividend_records || 0} 笔` }
])

function createEmptyForm() {
  return {
    userId: null,
    agentType: 'COUNTY_AGENT',
    province: '',
    city: '',
    district: '',
    dividendRate: 1,
    effectiveAt: null,
    expiredAt: null,
    remark: ''
  }
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

function formatExpiry(value) {
  return value ? formatDate(value) : '长期有效'
}

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function agentTypeLabel(value) {
  return { COUNTY_AGENT: '区代理', CITY_AGENT: '市代理' }[value] || value || '--'
}

async function loadData() {
  const [summaryData] = await Promise.all([regionApi.summary(), loadAgents(1), loadDividends(1)])
  summary.value = summaryData || {}
}

async function loadAgents(nextPage = agentPage.value) {
  loadingAgents.value = true
  try {
    agentPage.value = nextPage
    const data = await regionApi.agents({
      keyword: filters.value.keyword || undefined,
      agent_type: filters.value.agentType || undefined,
      page: agentPage.value,
      page_size: agentPageSize.value
    })
    agentRows.value = data.items || []
    agentTotal.value = data.total || 0
  } finally {
    loadingAgents.value = false
  }
}

async function loadDividends(nextPage = dividendPage.value) {
  loadingDividends.value = true
  try {
    dividendPage.value = nextPage
    const data = await regionApi.dividends({
      keyword: dividendFilters.value.keyword || undefined,
      status: dividendFilters.value.status || undefined,
      agent_type: dividendFilters.value.agentType || undefined,
      page: dividendPage.value,
      page_size: dividendPageSize.value
    })
    dividendRows.value = data.items || []
    dividendTotal.value = data.total || 0
  } finally {
    loadingDividends.value = false
  }
}

function resetAgentFilters() {
  filters.value = { keyword: '', agentType: '' }
  loadAgents(1)
}

async function searchUsers(keyword = '') {
  loadingUsers.value = true
  try {
    const data = await userApi.list({ keyword: keyword || undefined, page: 1, page_size: 20 })
    userOptions.value = data.items || []
  } finally {
    loadingUsers.value = false
  }
}

function openCreateDialog() {
  editingAgentId.value = null
  agentForm.value = createEmptyForm()
  userOptions.value = []
  agentDialogVisible.value = true
  searchUsers()
}

function openEditDialog(row) {
  editingAgentId.value = row.id
  userOptions.value = [{ id: row.user_id, nickname: row.user_nickname, phone: row.user_phone }]
  agentForm.value = {
    userId: row.user_id,
    agentType: row.agent_type,
    province: row.province || '',
    city: row.city || '',
    district: row.district || '',
    dividendRate: Number(row.dividend_rate || 0),
    effectiveAt: row.effective_at ? dayjs(row.effective_at).format('YYYY-MM-DDTHH:mm:ss') : null,
    expiredAt: row.expired_at ? dayjs(row.expired_at).format('YYYY-MM-DDTHH:mm:ss') : null,
    remark: row.audit_remark || ''
  }
  agentDialogVisible.value = true
}

function handleAgentTypeChange(value) {
  agentForm.value.dividendRate = value === 'CITY_AGENT' ? 0.5 : 1
  if (value === 'CITY_AGENT') agentForm.value.district = ''
}

async function saveAgent() {
  const form = agentForm.value
  if (!form.userId || !form.province.trim() || !form.city.trim() || (form.agentType === 'COUNTY_AGENT' && !form.district.trim())) {
    ElMessage.warning('请完整填写代理会员和代理区域')
    return
  }
  const payload = {
    agent_type: form.agentType,
    province: form.province.trim(),
    city: form.city.trim(),
    district: form.agentType === 'COUNTY_AGENT' ? form.district.trim() : '',
    dividend_rate: form.dividendRate,
    effective_at: form.effectiveAt || null,
    expired_at: form.expiredAt || null,
    remark: form.remark || null
  }
  savingAgent.value = true
  try {
    if (editingAgentId.value) await regionApi.updateAgent(editingAgentId.value, payload)
    else await regionApi.createAgent({ user_id: form.userId, ...payload })
    ElMessage.success(editingAgentId.value ? '区域代理配置已更新' : '区域代理已配置')
    agentDialogVisible.value = false
    await loadData()
  } finally {
    savingAgent.value = false
  }
}

async function removeAgent(row) {
  await ElMessageBox.confirm(
    `确认删除 ${row.user_nickname || `用户 ${row.user_id}`} 的${agentTypeLabel(row.agent_type)}配置？历史奖励记录会保留。`,
    '删除区域代理',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  )
  await regionApi.deleteAgent(row.id)
  ElMessage.success('区域代理配置已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.region-view {
  display: grid;
  gap: 18px;
}

.block-gap {
  margin-top: 4px;
}

.header-actions,
.toolbar-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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

.amount-primary {
  font-size: 15px;
  font-weight: 700;
  color: var(--primary-deep);
}

.rate-text {
  font-weight: 600;
  color: var(--text-primary);
}

.unit {
  margin-left: 8px;
  color: var(--text-secondary);
}

.table-pagination {
  margin-top: 18px;
  justify-content: flex-end;
}
</style>
