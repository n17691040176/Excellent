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
    <div class="split-grid">
      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>资产说明</h3>
          <p>资产体系与四大专区消费和补贴逻辑一一映射。</p>
        </div>
        <div class="notice-list">
          <div class="notice-item">
            <strong>余额</strong>
            承接设备流水分佣，可提现，也可用于爆款区抢购与本地生活消费。
          </div>
          <div class="notice-item">
            <strong>积分</strong>
            套餐补贴通过排队方式获取，可提现、转赠上下级，或用于商城消费对冲。
          </div>
          <div class="notice-item">
            <strong>兑换券 / AI 券</strong>
            兑换券承接套餐与签到奖励，AI 券承接自营商城购物返券，二者都和套餐抵扣场景有关。
          </div>
          <div class="notice-item">
            <strong>充电宝</strong>
            充电宝按台数入账，绑定、启停会记录到资产流水，设备收益则结算到余额账户。
          </div>
        </div>
      </div>

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
      <el-table :data="pagedLedgers" border>
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
import dayjs from 'dayjs'

import { assetApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { PageHeader, MetricCard } from '@/components/common'

const userStore = useUserStore()

const assetOptions = [
  { label: '余额', value: 'BALANCE' },
  { label: '积分', value: 'POINTS' },
  { label: '兑换券', value: 'VOUCHER' },
  { label: 'AI 券', value: 'AI_COUPON' },
  { label: '充电宝', value: 'POWER_BANK' }
]

const summary = ref({})
const detail = ref({})
const ledgers = ref([])
const keyword = ref('')
const assetType = ref('BALANCE')
const page = ref(1)
const pageSize = ref(10)

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '围绕余额、积分、兑换券、AI 券和充电宝统一查看账户与资产流水。'
    : '围绕余额、积分、兑换券、AI 券和充电宝统一查看账户与资产流水。'
)

const metrics = computed(() => [
  { label: '余额账户', value: Number(summary.value.BALANCE || 0).toFixed(2), subtext: '可提现或用于爆款区', variant: 'primary' },
  { label: '积分账户', value: Number(summary.value.POINTS || 0).toFixed(2), subtext: '补贴、转赠与商城消费', variant: 'success' },
  { label: '兑换券账户', value: Number(summary.value.VOUCHER || 0).toFixed(2), subtext: '套餐奖励与签到发放', variant: 'warning' },
  { label: 'AI 券账户', value: Number(summary.value.AI_COUPON || 0).toFixed(2), subtext: '自营商城返券与套餐抵扣', variant: 'neutral' },
  { label: '充电宝资产', value: Number(summary.value.POWER_BANK || summary.value.power_bank_count || 0).toFixed(0), subtext: '当前生效的充电宝台数', variant: 'info' }
])

const assetCards = computed(() => {
  if (assetType.value === 'POWER_BANK') {
    return [
      { code: 'available', title: '当前生效', amount: Number(detail.value.available_amount || 0).toFixed(0), meta: '当前仍在生效中的设备台数' },
      { code: 'total', title: '累计入账', amount: Number(detail.value.total_amount || 0).toFixed(0), meta: '绑定和重新启用都会累计到这里' },
      { code: 'disabled', title: '停用数量', amount: Number(detail.value.consumed_amount || 0).toFixed(0), meta: '通过停用转出的设备台数' },
      { code: 'frozen', title: '冻结数量', amount: Number(detail.value.frozen_amount || 0).toFixed(0), meta: '预留字段，当前未使用' }
    ]
  }

  return [
    { code: 'available', title: '可用余额', amount: Number(detail.value.available_amount || 0).toFixed(2), meta: '当前资产可支配额度' },
    { code: 'frozen', title: '冻结金额', amount: Number(detail.value.frozen_amount || 0).toFixed(2), meta: '待释放或待审核' },
    { code: 'consumed', title: '累计消耗', amount: Number(detail.value.consumed_amount || 0).toFixed(2), meta: '历史支出或抵扣' },
    { code: 'withdrawn', title: '累计提现', amount: Number(detail.value.withdrawn_amount || 0).toFixed(2), meta: '仅部分资产支持提现' }
  ]
})

const filteredLedgers = computed(() => {
  const term = keyword.value.trim()
  return ledgers.value.filter((item) => {
    if (!term) return true
    return (item.business_type || '').includes(term) || (item.remark || '').includes(term)
  })
})

const pagedLedgers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredLedgers.value.slice(start, start + pageSize.value)
})

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

async function loadCurrentAsset() {
  detail.value = await assetApi.detail(assetType.value)
  ledgers.value = await assetApi.ledgers(assetType.value)
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
