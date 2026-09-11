<template>
  <div class="asset-view">
    <!-- 统一页面头部 -->
    <PageHeader title="资产中心" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="loadData">刷新资产</el-button>
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

    <!-- 资产说明与账户卡片 -->
    <div>
      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>当前账户</h3>
          <p>以下数据读取当前登录管理员自身资产账户。</p>
        </div>
        <div class="tiny-stat-grid">
          <div class="tiny-stat" v-for="item in assetCards" :key="item.code">
            <div class="title">{{ item.title }}</div>
            <div class="number">{{ item.amount }}</div>
            <div class="meta">{{ item.meta }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 资产流水卡片 -->
    <div class="panel-card data-card">
      <!-- 筛选栏 -->
      <div class="toolbar-row">
        <el-select v-model="assetType" placeholder="资产类型" style="width: 180px;">
          <el-option v-for="item in assetOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索业务类型 / 备注" clearable style="max-width: 280px;" />
      </div>

      <!-- 数据表格 -->
      <el-table v-if="assetType === 'COMMISSION'" :data="pagedLedgers" border>
        <el-table-column prop="title" label="收益类型" min-width="160" />
        <el-table-column prop="commission_mode_text" label="分润模式" width="110" />
        <el-table-column prop="commission_amount" label="佣金金额" width="120" />
        <el-table-column label="状态" width="110"><template #default="{ row }">{{ commissionStatus(row.status) }}</template></el-table-column>
        <el-table-column prop="order_id" label="订单 ID" width="110" />
        <el-table-column label="时间" min-width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
      </el-table>
      <el-table v-else :data="pagedLedgers" border>
        <el-table-column prop="id" label="流水 ID" width="100" />
        <el-table-column prop="business_type" label="业务类型" min-width="150" />
        <el-table-column prop="direction" label="方向" width="100" />
        <el-table-column prop="change_amount" label="变动金额" min-width="120" />
        <el-table-column prop="before_amount" label="变动前" min-width="120" />
        <el-table-column prop="after_amount" label="变动后" min-width="120" />
        <el-table-column prop="source_no" label="来源单号" min-width="160" />
        <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
        <el-table-column label="时间" min-width="170">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="total, prev, pager, next"
        :total="filteredLedgers.length"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { formatDateTime } from '@/utils/datetime'

import { assetApi } from '@/api/modules'
import { PageHeader, MetricCard } from '@/components/common'


const assetOptions = [
  { label: '余额', value: 'BALANCE' },
  { label: '佣金', value: 'COMMISSION' },
  { label: '积分', value: 'POINTS' }
]

const summary = ref({})
const detail = ref({})
const ledgers = ref([])
const keyword = ref('')
const assetType = ref('BALANCE')
const page = ref(1)
const pageSize = ref(10)

const scopeHint = '查看余额、佣金和积分。'

const metrics = computed(() => [
  { label: '余额', value: Number(summary.value.BALANCE || 0).toFixed(2), variant: 'primary' },
  { label: '佣金', value: Number(summary.value.COMMISSION || 0).toFixed(2), variant: 'warning' },
  { label: '积分', value: Number(summary.value.POINTS || 0).toFixed(2), variant: 'success' }
])

const assetCards = computed(() => {

  return [
    { code: 'available', title: '可用余额', amount: Number(detail.value.available_amount || 0).toFixed(2), meta: '当前资产可支配额度' },
    { code: 'frozen', title: '冻结金额', amount: Number(detail.value.frozen_amount || 0).toFixed(2), meta: '待释放或待审核' },
    { code: 'consumed', title: assetType.value === 'COMMISSION' ? '累计收益' : '累计消耗', amount: Number((assetType.value === 'COMMISSION' ? detail.value.total_amount : detail.value.consumed_amount) || 0).toFixed(2), meta: '' },
    { code: 'withdrawn', title: '累计提现', amount: Number(detail.value.withdrawn_amount || 0).toFixed(2), meta: '仅部分资产支持提现' }
  ]
})

const filteredLedgers = computed(() => {
  const term = keyword.value.trim()
  return ledgers.value.filter((item) => {
    if (!term) return true
    return [item.business_type, item.remark, item.title, item.order_no].some(value => String(value || '').includes(term))
  })
})

const pagedLedgers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredLedgers.value.slice(start, start + pageSize.value)
})

function formatDate(value) {
  return formatDateTime(value)
}

let latestAssetRequest = 0
async function loadCurrentAsset() {
  const requestId = ++latestAssetRequest
  const type = assetType.value
  const [account, records] = await Promise.all(type === 'COMMISSION'
    ? [assetApi.commissionSummary(), assetApi.commissionFlows()]
    : [assetApi.detail(type), assetApi.ledgers(type)])
  if (requestId !== latestAssetRequest) return
  detail.value = account
  ledgers.value = records
}

function commissionStatus(status) {
  return { FROZEN: '待结算', SETTLED: '已结算', CANCELED: '已撤销' }[status] || status
}

async function loadData() {
  summary.value = await assetApi.summary()
  await loadCurrentAsset()
}

watch(assetType, async () => {
  page.value = 1
  await loadCurrentAsset()
})

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.asset-view {
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

.notice-list {
  display: grid;
  gap: var(--space-3);
}

.tiny-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
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

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  margin-bottom: var(--space-4);
}

@media (max-width: 768px) {
  .tiny-stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
