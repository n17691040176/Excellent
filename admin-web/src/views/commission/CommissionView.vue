<template>
  <div class="commission-view">
    <!-- 统一页面头部 -->
    <PageHeader title="返现管理" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="loadData">刷新数据</el-button>
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

    <!-- 返现规则与操作提醒 -->
    <div class="split-grid">
      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>返现规则</h3>
          <p>当前后台采用合规二级返现，结算时点依赖订单确认完成。</p>
        </div>
        <div class="tiny-stat-grid">
          <div class="tiny-stat">
            <div class="title">一级返现比例</div>
            <div class="number">{{ config.level1_rate ?? 0 }}%</div>
            <div class="meta">默认推荐人返现比例</div>
          </div>
          <div class="tiny-stat">
            <div class="title">二级返现比例</div>
            <div class="number">{{ config.level2_rate ?? 0 }}%</div>
            <div class="meta">祖级邀请返现比例</div>
          </div>
          <div class="tiny-stat">
            <div class="title">当前状态</div>
            <div class="number">{{ config.is_active ? '启用' : '停用' }}</div>
            <div class="meta">后台只展示一套生效配置</div>
          </div>
        </div>
      </div>

      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>操作提醒</h3>
          <p>提现审核与本地生活核销会直接影响佣金状态变更。</p>
        </div>
        <div class="notice-list">
          <div class="notice-item">
            <strong>冻结逻辑</strong>
            下级有效支付后先冻结，订单确认收货或服务核销后再转可提现余额。
          </div>
          <div class="notice-item">
            <strong>团队边界</strong>
            团队管理员仅查看自身可见数据，避免跨团队干扰与误审。
          </div>
          <div class="notice-item">
            <strong>异常排查</strong>
            若佣金总额上涨但可提现金额不变，优先检查订单确认链路。
          </div>
        </div>
      </div>
    </div>

    <!-- 佣金账户与返现流水 -->
    <div class="panel-card data-card">
      <div class="toolbar-row">
        <el-input
          v-model="keyword"
          placeholder="搜索用户 ID / 手机号，流水页可筛订单 ID"
          clearable
          style="max-width: 320px;"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="statusFilter" placeholder="流水状态" clearable style="width: 180px;" @change="flowPage = 1">
          <el-option label="冻结中" value="FROZEN" />
          <el-option label="已结算" value="SETTLED" />
          <el-option label="已取消" value="CANCELED" />
        </el-select>
        <el-button @click="handleSearch">查询</el-button>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="佣金账户" name="accounts">
          <el-table :data="commissionUsers" border>
            <el-table-column prop="user_id" label="用户 ID" width="100" />
            <el-table-column prop="available_amount" label="可提现佣金" min-width="130" />
            <el-table-column prop="frozen_amount" label="冻结佣金" min-width="130" />
            <el-table-column prop="withdrawn_amount" label="已提现佣金" min-width="130" />
            <el-table-column prop="total_amount" label="累计佣金" min-width="130" />
            <el-table-column label="更新时间" min-width="180">
              <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="userPage"
            v-model:page-size="userPageSize"
            layout="total, prev, pager, next"
            :page-size="userPageSize"
            :total="userTotal"
            @current-change="fetchUsers"
          />
        </el-tab-pane>

        <el-tab-pane label="返现流水" name="flows">
          <el-table :data="pagedFlows" border>
            <el-table-column prop="id" label="流水 ID" width="100" />
            <el-table-column prop="beneficiary_user_id" label="受益用户" width="100" />
            <el-table-column prop="source_user_id" label="来源用户" width="100" />
            <el-table-column prop="order_id" label="订单 ID" width="100" />
            <el-table-column prop="level" label="层级" width="80" />
            <el-table-column prop="rate" label="比例%" width="90" />
            <el-table-column prop="commission_amount" label="返现金额" min-width="120" />
            <el-table-column label="状态" width="110">
              <template #default="scope">
                <StatusTag :status="scope.row.status" type="commission" />
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="170">
              <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="结算时间" min-width="170">
              <template #default="scope">{{ formatDate(scope.row.settled_at) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="flowPage"
            v-model:page-size="flowPageSize"
            layout="total, prev, pager, next"
            :total="filteredFlows.length"
          />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'

import { commissionApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { PageHeader, MetricCard, StatusTag } from '@/components/common'

const userStore = useUserStore()
const config = ref({})
const commissionUsers = ref([])
const commissionUserSummary = ref({})
const commissionFlows = ref([])
const keyword = ref('')
const statusFilter = ref('')
const activeTab = ref('accounts')
const userPage = ref(1)
const userPageSize = ref(20)
const userTotal = ref(0)
const flowPage = ref(1)
const flowPageSize = ref(8)

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '当前仅查看所属团队产生的佣金账户、冻结流水与结算记录。'
    : '统一查看平台两级返现比例、用户佣金池和冻结结算流水。'
)

const metrics = computed(() => {
  const totalAvailable = Number(commissionUserSummary.value.available_amount || 0)
  const totalFrozen = Number(commissionUserSummary.value.frozen_amount || 0)
  const totalCommission = Number(commissionUserSummary.value.total_amount || 0)
  const settledCount = commissionFlows.value.filter((item) => item.status === 'SETTLED').length
  const userCount = Number(commissionUserSummary.value.user_count || userTotal.value || 0)
  return [
    { label: '一级返现比例', value: `${config.value.level1_rate ?? 0}%`, subtext: '一级邀请有效订单返现', variant: 'primary' },
    { label: '二级返现比例', value: `${config.value.level2_rate ?? 0}%`, subtext: '二级邀请有效订单返现', variant: 'neutral' },
    { label: '冻结佣金总额', value: totalFrozen.toFixed(2), subtext: `待订单完成后释放，佣金账户 ${userCount} 个`, variant: 'warning' },
    { label: '累计返现金额', value: totalCommission.toFixed(2), subtext: `已结算流水 ${settledCount} 笔，可提现 ${totalAvailable.toFixed(2)}`, variant: 'success' }
  ]
})

const filteredFlows = computed(() => {
  const term = keyword.value.trim()
  return commissionFlows.value.filter((item) => {
    const hitKeyword = !term || String(item.order_id).includes(term) || String(item.beneficiary_user_id).includes(term)
    const hitStatus = !statusFilter.value || item.status === statusFilter.value
    return hitKeyword && hitStatus
  })
})

const pagedFlows = computed(() => paginate(filteredFlows.value, flowPage.value, flowPageSize.value))

function paginate(list, page, size) {
  const start = (page - 1) * size
  return list.slice(start, start + size)
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

function handleSearch() {
  if (activeTab.value === 'accounts') {
    fetchUsers(1)
    return
  }
  flowPage.value = 1
}

async function fetchUsers(nextPage = userPage.value) {
  userPage.value = nextPage
  const data = await commissionApi.users({
    page: userPage.value,
    page_size: userPageSize.value,
    keyword: keyword.value || undefined
  })
  commissionUsers.value = data.items || []
  commissionUserSummary.value = data.summary || {}
  userTotal.value = data.total || 0
}

async function loadData() {
  const [configData, flowsData] = await Promise.all([
    commissionApi.config(),
    commissionApi.flows()
  ])
  config.value = configData || {}
  commissionFlows.value = flowsData || []
  await fetchUsers(1)
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
  line-height: var(--leading-relaxed);
}

.tiny-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.tiny-stat {
  padding: var(--space-4);
  background: var(--primary-50);
  border-radius: var(--radius-lg);
  text-align: center;
}

.tiny-stat .title {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.tiny-stat .number {
  margin-top: var(--space-2);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--primary-deep);
}

.tiny-stat .meta {
  margin-top: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.notice-list {
  display: grid;
  gap: var(--space-3);
}

.notice-item {
  padding: var(--space-3) var(--space-4);
  background: var(--primary-50);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.notice-item strong {
  color: var(--text-primary);
}

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  margin-bottom: var(--space-4);
}

@media (max-width: 1200px) {
  .tiny-stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
