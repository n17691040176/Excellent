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

    <div class="panel-card data-card">
      <div class="section-title-lite">
        <h3>商品分润规则</h3>
        <p>同步商品管理中已启用的专属分润配置；普通会员、经销商按推荐关系结算，区代理、市代理按订单区域结算。</p>
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
        <el-table-column label="分润方式" width="120">
          <template #default="{ row }">{{ row.method === 'FIXED_AMOUNT' ? '固定金额' : '利润比例' }}</template>
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

    <div class="panel-card data-card">
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
          <el-table v-loading="loadingFlows" :data="commissionFlows" border>
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
              <template #default="{ row }">{{ formatRate(row.rate) }}</template>
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
import { PageHeader, MetricCard, StatusTag } from '@/components/common'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
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

const zoneOptions = [
  { label: '复购区', value: 'REPURCHASE' },
  { label: '自营商城', value: 'SELF_OPERATED' },
  { label: '爆款区', value: 'HOT_SALE' },
  { label: '本地生活', value: 'LOCAL_LIFE' }
]

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
