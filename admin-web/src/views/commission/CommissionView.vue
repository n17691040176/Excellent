<template>
  <div class="commission-view">
    <PageHeader title="佣金明细" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="loadData">刷新数据</el-button>
      </template>
    </PageHeader>

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

    <div class="panel-card data-card mode-card">
      <div class="mode-summary">
        <span>当前分润模式</span>
        <el-tag :type="activeMode === 'CITY_PARTNER' ? 'success' : 'info'">{{ modeLabel(activeMode) }}</el-tag>
        <div v-if="userStore.role === 'SUPER_ADMIN'" class="mode-actions">
          <el-button link @click="showModeHistory">切换记录</el-button>
          <el-button type="primary" plain @click="modeSettingsVisible = true">模式设置</el-button>
        </div>
      </div>
    </div>

    <el-drawer v-model="modeSettingsVisible" title="分润模式设置" size="min(600px, 100vw)">
      <el-form label-position="top">
        <el-form-item label="分润模式">
          <el-select v-model="selectedMode" aria-label="分润模式" style="width: 100%">
            <el-option v-for="option in modeOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="切换原因"><el-input v-model="modeReason" placeholder="选填" maxlength="500" /></el-form-item>
      </el-form>
      <el-alert title="仅影响之后付款的商品订单" type="info" :closable="false" />
      <div class="settings-heading"><h3>配置检查</h3><el-button link @click="loadReadiness">重新检查</el-button></div>
      <el-table :data="readiness.checks">
        <el-table-column prop="label" label="检查项" min-width="160" />
        <el-table-column label="结果" width="90"><template #default="{ row }"><el-tag :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '通过' : '待完善' }}</el-tag></template></el-table-column>
        <el-table-column label="详情" min-width="160"><template #default="{ row }"><span v-if="!row.passed">{{ row.message }}</span><span v-else>—</span></template></el-table-column>
      </el-table>
      <el-collapse class="policy-details"><el-collapse-item title="结算与退款规则"><p v-for="policy in readiness.policies" :key="policy">{{ policy }}</p></el-collapse-item></el-collapse>
      <template #footer><el-button @click="modeSettingsVisible = false">取消</el-button><el-button type="primary" :loading="switchingMode" :disabled="selectedMode === activeMode" @click="switchMode">确认切换</el-button></template>
    </el-drawer>

    <el-tabs v-model="sectionTab" class="section-tabs">
      <el-tab-pane label="佣金明细" name="ledger" />
      <el-tab-pane label="商品规则" name="rules" />
      <el-tab-pane v-if="userStore.role === 'SUPER_ADMIN'" label="城市合伙人" name="cities" />
      <el-tab-pane v-if="userStore.role === 'SUPER_ADMIN'" label="待处理订单" name="pending" />
    </el-tabs>

    <el-drawer v-model="modeHistoryVisible" title="模式切换记录" size="75%">
      <el-table :data="modeHistoryRows">
        <el-table-column label="切换时间" min-width="175"><template #default="{ row }">{{ formatDate(row.switched_at) }}</template></el-table-column>
        <el-table-column prop="operator_name" label="操作人" />
        <el-table-column label="模式"><template #default="{ row }">{{ modeLabel(row.from_mode) }} → {{ modeLabel(row.to_mode) }}</template></el-table-column>
        <el-table-column prop="reason" label="原因" />
        <el-table-column prop="pending_order_count" label="待结算订单" />
        <el-table-column prop="frozen_commission_amount" label="冻结金额" />
      </el-table>
      <el-pagination v-model:current-page="modeHistoryPage" :page-size="20" :total="modeHistoryTotal" layout="total, prev, pager, next" @current-change="loadModeHistory" />
    </el-drawer>
    <RuleHistoryDrawer v-model="ruleHistoryVisible" :entity-id="ruleHistoryId" entity-type="PRODUCT" />

    <CityPartnerPanel v-if="userStore.role === 'SUPER_ADMIN'" v-show="sectionTab === 'cities' || sectionTab === 'pending'" :pending-only="sectionTab === 'pending'" />
    <FailedSettlementsPanel v-if="userStore.role === 'SUPER_ADMIN'" v-show="sectionTab === 'pending'" />

    <div v-show="sectionTab === 'rules'" class="panel-card data-card">
      <div class="section-title-lite">
        <h3>商品分润规则</h3>
      </div>
      <div class="toolbar-row">
        <el-input
          v-model="ruleKeyword"
          placeholder="搜索商品 ID / 商品名称"
          clearable
          style="max-width: 280px"
          @keyup.enter="loadRules(1)"
          @clear="loadRules(1)"
        />
        <el-select v-model="ruleZone" placeholder="商品专区" clearable style="width: 160px" @change="loadRules(1)">
          <el-option v-for="item in zoneOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" @click="loadRules(1)">查询</el-button>
      </div>
      <el-table v-loading="loadingRules" :data="productRules" border>
        <el-table-column prop="product_id" label="商品 ID" width="100" />
        <el-table-column prop="product_name" label="商品名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="专区" width="120">
          <template #default="{ row }">{{ zoneLabel(row.zone_type) }}</template>
        </el-table-column>
        <el-table-column label="模式" width="150">
          <template #default="{ row }">
            <el-tag :type="rowMode(row) === 'CITY_PARTNER' ? 'success' : 'info'" size="small">
              {{ modeLabel(rowMode(row)) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分润方式" width="140">
          <template #default="{ row }">{{ rowMode(row) === 'CITY_PARTNER' ? '分润池固定金额' : (row.method === 'FIXED_AMOUNT' ? '固定金额' : '利润比例') }}</template>
        </el-table-column>
        <el-table-column v-if="hasCityPartnerRows" label="城市合伙人规则" min-width="330">
          <template #default="{ row }">
            <div v-if="rowMode(row) === 'CITY_PARTNER'" class="city-rule-cell">
              <div><strong>{{ cityPartnerRuleValue(row, 'city_partner_amount') }}</strong> 合伙人</div>
              <div>直推 {{ cityPartnerRuleValue(row, 'direct_reward_amount') }} · 上级起始 {{ cityPartnerRuleValue(row, 'upline_start_amount') }}</div>
              <div>{{ cityPartnerRuleValue(row, 'upline_levels') }}递减 · 每层 50%</div>
            </div>
            <span v-else class="rule-value-disabled">不适用</span>
          </template>
        </el-table-column>
        <el-table-column
          v-for="level in commissionMemberLevels"
          :key="level.key"
          :label="level.label"
          min-width="130"
        >
          <template #default="{ row }">
            <span :class="{ 'rule-value-disabled': !row[`${level.key}_enabled`] }">
              {{ ruleValue(row, level.key) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="170">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="修改记录" width="110"><template #default="{ row }"><el-button link @click="ruleHistoryId = row.product_id; ruleHistoryVisible = true">查看记录</el-button></template></el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="rulePage"
        v-model:page-size="rulePageSize"
        class="table-pagination"
        layout="total, prev, pager, next"
        :total="ruleTotal"
        @current-change="loadRules"
      />
    </div>

    <div v-show="sectionTab === 'ledger'" class="panel-card data-card">
      <div class="toolbar-row">
        <el-input
          v-model="keyword"
          placeholder="搜索用户、手机号或订单号"
          clearable
          style="max-width: 320px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-if="activeTab === 'flows'"
          v-model="statusFilter"
          placeholder="佣金状态"
          clearable
          style="width: 180px"
          @change="fetchFlows(1)"
        >
          <el-option label="冻结中" value="FROZEN" />
          <el-option label="已结算" value="SETTLED" />
          <el-option label="已取消" value="CANCELED" />
        </el-select>
        <el-button @click="handleSearch">查询</el-button>
      </div>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="佣金账户" name="accounts">
          <el-table v-loading="loadingUsers" :data="commissionUsers" border>
            <el-table-column prop="user_id" label="用户 ID" width="110" />
            <el-table-column label="可提现佣金" min-width="130">
              <template #default="{ row }">¥{{ formatMoney(row.available_amount) }}</template>
            </el-table-column>
            <el-table-column label="冻结佣金" min-width="130">
              <template #default="{ row }">¥{{ formatMoney(row.frozen_amount) }}</template>
            </el-table-column>
            <el-table-column label="累计佣金" min-width="130">
              <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
            </el-table-column>
            <el-table-column label="已提现佣金" min-width="130">
              <template #default="{ row }">¥{{ formatMoney(row.withdrawn_amount) }}</template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="userPage"
            v-model:page-size="userPageSize"
            class="table-pagination"
            layout="total, prev, pager, next"
            :total="userTotal"
            @current-change="fetchUsers"
          />
        </el-tab-pane>

        <el-tab-pane label="佣金流水" name="flows">
          <el-table v-loading="loadingFlows" :data="commissionFlows" row-key="record_key" border>
            <el-table-column type="expand"><template #default="{ row }"><el-descriptions :column="1" border class="flow-detail"><el-descriptions-item label="取整前金额">{{ row.commission_mode === 'CITY_PARTNER' ? (row.calculated_amount ?? '历史未留存') : '不适用' }}</el-descriptions-item></el-descriptions></template></el-table-column>
            <el-table-column label="模式" width="140"><template #default="{ row }">{{ modeLabel(row.commission_mode) }}</template></el-table-column>
            <el-table-column prop="order_no" label="订单号" min-width="180" />
            <el-table-column label="受益用户" min-width="170">
              <template #default="{ row }">
                <div>{{ row.beneficiary_nickname || `用户 ${row.beneficiary_user_id}` }}</div>
                <div class="cell-meta">{{ row.beneficiary_phone || `ID: ${row.beneficiary_user_id}` }}</div>
              </template>
            </el-table-column>
            <el-table-column label="来源用户" min-width="170">
              <template #default="{ row }">
                <div>{{ row.source_nickname || `用户 ${row.source_user_id}` }}</div>
                <div class="cell-meta">{{ row.source_phone || `ID: ${row.source_user_id}` }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="level_label" label="分润层级" width="130" />
            <el-table-column label="分润基数" width="120">
              <template #default="{ row }">¥{{ formatMoney(row.base_amount) }}</template>
            </el-table-column>
            <el-table-column label="比例" width="90">
              <template #default="{ row }">{{ row.commission_mode === 'CITY_PARTNER' ? '固定金额' : formatRate(row.rate) }}</template>
            </el-table-column>
            <el-table-column label="佣金金额" width="120">
              <template #default="{ row }">¥{{ formatMoney(row.commission_amount) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }"><StatusTag :status="row.status" type="commission" /></template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="170">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="结算时间" min-width="170">
              <template #default="{ row }">{{ formatDate(row.settled_at) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="flowPage"
            v-model:page-size="flowPageSize"
            class="table-pagination"
            layout="total, prev, pager, next"
            :total="flowTotal"
            @current-change="fetchFlows"
          />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { formatDateTime } from '@/utils/datetime'

import { commissionApi } from '@/api/modules'
import { ElMessage, ElMessageBox } from 'element-plus'
import CityPartnerPanel from './CityPartnerPanel.vue'
import FailedSettlementsPanel from './FailedSettlementsPanel.vue'
import RuleHistoryDrawer from './RuleHistoryDrawer.vue'
import { PageHeader, MetricCard, StatusTag } from '@/components/common'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const sectionTab = ref('ledger')
const modeSettingsVisible = ref(false)
const readiness = ref({ checks: [], policies: [] })
const modeHistoryVisible = ref(false), modeHistoryRows = ref([]), modeHistoryPage = ref(1), modeHistoryTotal = ref(0)
const ruleHistoryVisible = ref(false), ruleHistoryId = ref(null)
async function loadReadiness() { readiness.value = await commissionApi.readiness() }
async function loadModeHistory() { const data = await commissionApi.modeHistory({ page: modeHistoryPage.value }); modeHistoryRows.value = data.items; modeHistoryTotal.value = data.total }
async function showModeHistory() { modeHistoryPage.value = 1; await loadModeHistory(); modeHistoryVisible.value = true }
const loadingUsers = ref(false)
const loadingFlows = ref(false)
const loadingRules = ref(false)
const commissionUsers = ref([])
const commissionUserSummary = ref({})
const commissionFlows = ref([])
const productRules = ref([])
const keyword = ref('')
const statusFilter = ref('')
const activeTab = ref('accounts')
const userPage = ref(1)
const userPageSize = ref(20)
const userTotal = ref(0)
const flowPage = ref(1)
const flowPageSize = ref(20)
const flowTotal = ref(0)
const ruleKeyword = ref('')
const ruleZone = ref('')
const rulePage = ref(1)
const rulePageSize = ref(20)
const ruleTotal = ref(0)

const modeOptions = [
  { label: '原模式', value: 'ORIGINAL' },
  { label: '城市合伙人模式', value: 'CITY_PARTNER' }
]

const zoneOptions = [
  { label: '复购区', value: 'REPURCHASE' },
  { label: '自营商城', value: 'SELF_OPERATED' },
  { label: '爆款区', value: 'HOT_SALE' },
  { label: '本地生活', value: 'LOCAL_LIFE' }
]

const modeStatus = ref({})
const activeMode = computed(() => modeStatus.value.mode || 'ORIGINAL')
const selectedMode = ref('ORIGINAL')
const modeReason = ref('')
const switchingMode = ref(false)
async function loadMode() {
  modeStatus.value = await commissionApi.mode()
  selectedMode.value = modeStatus.value.mode
  if (userStore.role === 'SUPER_ADMIN') await loadReadiness()
}
async function switchMode() {
  if (selectedMode.value === 'CITY_PARTNER') {
    await loadReadiness()
    if (!readiness.value.ready) { ElMessage.warning('请先完成配置检查中的待完善项'); return }
  }
  try {
    await ElMessageBox.confirm(`切换为${modeLabel(selectedMode.value)}，只影响之后付款的订单。`, '确认切换')
  } catch { return }
  switchingMode.value = true
  try {
    await commissionApi.updateMode({ mode: selectedMode.value, reason: modeReason.value || null })
    await loadData()
    modeSettingsVisible.value = false
    ElMessage.success('分润模式已切换')
  } finally { switchingMode.value = false }
}
const hasCityPartnerRows = computed(() => productRules.value.some((row) => rowMode(row) === 'CITY_PARTNER'))

const commissionMemberLevels = [
  { label: '普通会员', key: 'level1' },
  { label: '经销商', key: 'level2' },
  { label: '区代理', key: 'county_agent' },
  { label: '市代理', key: 'city_agent' }
]

const scopeHint = computed(() => userStore.role === 'TEAM_ADMIN'
  ? '查看所属团队的佣金账户、真实订单佣金流水及可见商品分润规则。'
  : '查看平台商品分润规则、用户佣金账户和真实订单佣金流水。'
)

const metrics = computed(() => [
  { label: '可提现佣金', value: `¥${formatMoney(commissionUserSummary.value.available_amount)}`, subtext: `佣金账户 ${commissionUserSummary.value.user_count || userTotal.value || 0} 个`, variant: 'primary' },
  { label: '冻结佣金', value: `¥${formatMoney(commissionUserSummary.value.frozen_amount)}`, subtext: '订单完成后转为可提现', variant: 'warning' },
  { label: '累计佣金', value: `¥${formatMoney(commissionUserSummary.value.total_amount)}`, subtext: '历史产生佣金总额', variant: 'success' },
  { label: '已提现佣金', value: `¥${formatMoney(commissionUserSummary.value.withdrawn_amount)}`, subtext: '历史已审核提现金额', variant: 'neutral' }
])

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function formatRate(value) {
  return `${Number(value || 0).toFixed(2)}%`
}

function formatDate(value) {
  return formatDateTime(value)
}

function zoneLabel(value) {
  return zoneOptions.find((item) => item.value === value)?.label || value || '--'
}

function modeLabel(value) {
  return modeOptions.find((item) => item.value === value)?.label || value || '未标记模式'
}

function rowMode(row = {}) {
  return String(row.commission_mode || row.mode || row.rule_mode || 'ORIGINAL').toUpperCase()
}

function cityPartnerRuleValue(row, key) {
  const aliases = {
    city_partner_amount: ['city_partner_amount', 'city_partner_commission_amount', 'new_mode_city_partner_amount'],
    direct_reward_amount: ['direct_reward_amount', 'city_partner_direct_reward_amount', 'new_mode_direct_reward_amount'],
    upline_start_amount: ['city_partner_upline_initial_amount', 'upline_start_amount', 'city_partner_upline_start_amount', 'new_mode_upline_start_amount'],
    upline_levels: ['city_partner_upline_max_levels', 'upline_levels', 'city_partner_upline_levels', 'new_mode_upline_levels'],
    upline_decay_rate: ['upline_decay_rate', 'city_partner_upline_decay_rate', 'new_mode_upline_decay_rate'],
    tail_account: ['city_partner_remainder_account', 'tail_account', 'city_partner_tail_account', 'new_mode_tail_account']
  }
  const sourceKey = aliases[key]?.find((item) => row[item] !== undefined && row[item] !== null)
  const value = sourceKey ? row[sourceKey] : null
  if (key === 'tail_account') return { COMPANY: '公司尾差账户', COMPANY_ACCOUNT: '公司尾差账户' }[value] || value || '--'
  if (key === 'upline_levels') return value == null ? '--' : `${Number(value)}层`
  if (key === 'upline_decay_rate') return value == null ? '--' : `${Number(value).toFixed(2)}%`
  return value == null ? '--' : `¥${Number(value).toFixed(2)}`
}

function ruleValue(row, level) {
  if (!row[`${level}_enabled`]) return '未启用'
  const suffix = row.method === 'FIXED_AMOUNT' ? 'amount' : 'rate'
  const value = Number(row[`${level}_${suffix}`] || 0).toFixed(2)
  return row.method === 'FIXED_AMOUNT' ? `¥${value} / 件` : `${value}%`
}

function handleSearch() {
  if (activeTab.value === 'accounts') fetchUsers(1)
  else fetchFlows(1)
}

function handleTabChange(name) {
  if (name === 'flows' && !commissionFlows.value.length) fetchFlows(1)
}

async function fetchUsers(nextPage = userPage.value) {
  loadingUsers.value = true
  try {
    userPage.value = nextPage
    const data = await commissionApi.users({
      page: userPage.value,
      page_size: userPageSize.value,
      keyword: keyword.value || undefined
    })
    commissionUsers.value = data.items || []
    commissionUserSummary.value = data.summary || {}
    userTotal.value = data.total || 0
  } finally {
    loadingUsers.value = false
  }
}

async function fetchFlows(nextPage = flowPage.value) {
  loadingFlows.value = true
  try {
    flowPage.value = nextPage
    const data = await commissionApi.flows({
      page: flowPage.value,
      page_size: flowPageSize.value,
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined
    })
    commissionFlows.value = data.items || []
    flowTotal.value = data.total || 0
  } finally {
    loadingFlows.value = false
  }
}

async function loadRules(nextPage = rulePage.value) {
  loadingRules.value = true
  try {
    rulePage.value = nextPage
    const data = await commissionApi.productRules({
      page: rulePage.value,
      page_size: rulePageSize.value,
      keyword: ruleKeyword.value || undefined,
      zone_type: ruleZone.value || undefined
    })
    productRules.value = data.items || []
    ruleTotal.value = data.total || 0
  } finally {
    loadingRules.value = false
  }
}

async function loadData() {
  await loadMode()
  await Promise.all([fetchUsers(1), fetchFlows(1), loadRules(1)])
}

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.commission-view {
  display: grid;
  gap: var(--space-4);
}

.mode-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.mode-summary { align-items: center; justify-content: flex-start; }
.mode-actions { display: flex; gap: 12px; align-items: center; margin-left: auto; }
.settings-heading { display: flex; align-items: center; justify-content: space-between; margin-top: 24px; }
.settings-heading h3 { font-size: 16px; }
.policy-details { margin-top: 24px; }
.section-tabs :deep(.el-tabs__header) { margin: 0; }
.flow-detail { margin: 12px 24px; }

.city-rule-cell {
  line-height: 1.7;
  white-space: normal;
}

.section-title-lite {
  margin-bottom: var(--space-4);
}

.section-title-lite h3 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.section-title-lite p {
  margin: var(--space-2) 0 0;
  color: var(--text-muted);
}

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  margin-bottom: var(--space-4);
}

.table-pagination {
  margin-top: var(--space-4);
  justify-content: flex-end;
}

.cell-meta {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.rule-value-disabled {
  color: var(--text-muted);
}
</style>
