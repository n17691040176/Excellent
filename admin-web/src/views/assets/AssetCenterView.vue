<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>资产中心</h2>
        <p>围绕余额、积分、兑换券、AI 券四套账户查看资金与券值流转。</p>
      </div>
      <el-button type="primary" @click="loadData">刷新资产</el-button>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="split-grid" style="margin-top: 18px;">
      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>资产说明</h3>
            <p>资产体系与四大专区消费和补贴逻辑一一映射。</p>
          </div>
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
        </div>
      </div>

      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>当前账户</h3>
            <p>以下数据读取当前登录管理员自身资产账户。</p>
          </div>
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

    <div class="panel-card data-card" style="margin-top: 18px;">
      <div class="toolbar-row">
        <el-select v-model="assetType" placeholder="资产类型" style="width: 180px;">
          <el-option v-for="item in assetOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索业务类型 / 备注" clearable style="max-width: 280px;" />
      </div>

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

const assetOptions = [
  { label: '余额', value: 'BALANCE' },
  { label: '积分', value: 'POINTS' },
  { label: '兑换券', value: 'VOUCHER' },
  { label: 'AI 券', value: 'AI_COUPON' }
]

const summary = ref({})
const detail = ref({})
const ledgers = ref([])
const keyword = ref('')
const assetType = ref('BALANCE')
const page = ref(1)
const pageSize = ref(10)

const metrics = computed(() => [
  { label: '余额账户', value: Number(summary.value.BALANCE || 0).toFixed(2), subtext: '可提现或用于爆款区' },
  { label: '积分账户', value: Number(summary.value.POINTS || 0).toFixed(2), subtext: '补贴、转赠与商城消费' },
  { label: '兑换券账户', value: Number(summary.value.VOUCHER || 0).toFixed(2), subtext: '套餐奖励与签到发放' },
  { label: 'AI 券账户', value: Number(summary.value.AI_COUPON || 0).toFixed(2), subtext: '自营商城返券与套餐抵扣' }
])

const assetCards = computed(() => [
  { code: 'available', title: '可用余额', amount: Number(detail.value.available_amount || 0).toFixed(2), meta: '当前资产可支配额度' },
  { code: 'frozen', title: '冻结金额', amount: Number(detail.value.frozen_amount || 0).toFixed(2), meta: '待释放或待审核' },
  { code: 'consumed', title: '累计消耗', amount: Number(detail.value.consumed_amount || 0).toFixed(2), meta: '历史支出或抵扣' },
  { code: 'withdrawn', title: '累计提现', amount: Number(detail.value.withdrawn_amount || 0).toFixed(2), meta: '仅部分资产支持提现' }
])

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
