<template>
  <div class="page safe-bottom">
    <van-nav-bar title="佣金中心" fixed placeholder />

    <div class="page-card hero-card">
      <div class="hero-badge">Commission Center</div>
      <h2 class="page-title">佣金结算与提现进度</h2>
      <p class="page-desc">下级支付后佣金先冻结，确认收货或服务核销后转入可提现余额；提现申请再进入审核流程。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="section-head">
        <div>
          <h3 class="cell-group-title">提现申请</h3>
          <p class="page-desc" style="margin-bottom: 0;">仅当佣金进入可提现余额后才能申请，审核结果会记录在下方提现记录中。</p>
        </div>
        <van-button round type="primary" size="small" @click="showWithdraw = true">申请提现</van-button>
      </div>
      <div class="tiny-grid" style="margin-top: 0.24rem;">
        <div class="tiny-panel">
          <div class="tiny-panel-title">待审核</div>
          <div class="tiny-panel-value">{{ pendingWithdraws.length }}</div>
          <div class="tiny-panel-meta">等待后台审核打款</div>
        </div>
        <div class="tiny-panel">
          <div class="tiny-panel-title">已通过</div>
          <div class="tiny-panel-value">{{ approvedWithdraws.length }}</div>
          <div class="tiny-panel-meta">资金已扣减或待打款</div>
        </div>
        <div class="tiny-panel">
          <div class="tiny-panel-title">已驳回</div>
          <div class="tiny-panel-value">{{ rejectedWithdraws.length }}</div>
          <div class="tiny-panel-meta">请检查备注后重提</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <van-tabs v-model:active="activeTab" animated>
        <van-tab title="返现流水" name="flows">
          <div class="filter-row">
            <van-button
              v-for="item in flowFilters"
              :key="item.value"
              size="small"
              :type="flowStatus === item.value ? 'primary' : 'default'"
              plain
              @click="flowStatus = item.value"
            >{{ item.label }}</van-button>
          </div>
          <van-cell-group inset>
            <van-cell
              v-for="item in filteredFlows"
              :key="item.id"
              :title="`订单 ${item.order_id}`"
              :label="`${item.level} 级返现 / 来源用户 ${item.source_user_id} / 比例 ${item.rate}%`"
            >
              <template #value>
                <div>{{ item.commission_amount }}</div>
                <div :class="['status-pill', flowStatusClass(item.status)]">{{ flowStatusLabel(item.status) }}</div>
              </template>
            </van-cell>
          </van-cell-group>
          <van-empty v-if="!filteredFlows.length" image="search" description="当前筛选下暂无返现流水" />
        </van-tab>

        <van-tab title="提现记录" name="withdraws">
          <div class="filter-row">
            <van-button
              v-for="item in withdrawFilters"
              :key="item.value"
              size="small"
              :type="withdrawStatus === item.value ? 'primary' : 'default'"
              plain
              @click="withdrawStatus = item.value"
            >{{ item.label }}</van-button>
          </div>
          <van-cell-group inset>
            <van-cell
              v-for="item in filteredWithdraws"
              :key="item.id"
              :title="`${withdrawTypeLabel(item.withdraw_type)} / 申请 #${item.id}`"
              :label="withdrawRemark(item)"
            >
              <template #value>
                <div>{{ item.amount }}</div>
                <div :class="['status-pill', withdrawStatusClass(item.status)]">{{ withdrawStatusLabel(item.status) }}</div>
              </template>
            </van-cell>
          </van-cell-group>
          <van-empty v-if="!filteredWithdraws.length" image="search" description="当前筛选下暂无提现记录" />
        </van-tab>
      </van-tabs>
    </div>

    <van-popup v-model:show="showWithdraw" position="bottom" round :style="{ height: '58%' }">
      <div class="page" style="padding-bottom: 0.4rem;">
        <h3 class="cell-group-title">提交提现申请</h3>
        <p class="page-desc">建议确认佣金已结算进入可提现余额后再发起申请，避免因额度不足被驳回。</p>
        <van-form @submit="submitWithdraw">
          <van-field v-model="withdrawForm.amount" label="提现金额" type="number" placeholder="请输入提现金额" />
          <van-field v-model="withdrawForm.remark" label="备注" placeholder="可填写提现说明" />
          <div class="submit-bar">
            <van-button block round type="primary" native-type="submit">提交申请</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { commissionApi } from '@/api/modules'

const summary = ref({})
const flows = ref([])
const withdraws = ref([])
const activeTab = ref('flows')
const flowStatus = ref('ALL')
const withdrawStatus = ref('ALL')
const showWithdraw = ref(false)
const withdrawForm = reactive({
  amount: '',
  remark: ''
})

const flowFilters = [
  { label: '全部', value: 'ALL' },
  { label: '冻结中', value: 'FROZEN' },
  { label: '已结算', value: 'SETTLED' },
  { label: '已取消', value: 'CANCELED' }
]

const withdrawFilters = [
  { label: '全部', value: 'ALL' },
  { label: '待审核', value: 'PENDING' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '已打款', value: 'PAID' }
]

const filteredFlows = computed(() => {
  if (flowStatus.value === 'ALL') return flows.value
  return flows.value.filter((item) => item.status === flowStatus.value)
})

const filteredWithdraws = computed(() => {
  if (withdrawStatus.value === 'ALL') return withdraws.value
  return withdraws.value.filter((item) => item.status === withdrawStatus.value)
})

const pendingWithdraws = computed(() => withdraws.value.filter((item) => item.status === 'PENDING'))
const approvedWithdraws = computed(() => withdraws.value.filter((item) => item.status === 'APPROVED' || item.status === 'PAID'))
const rejectedWithdraws = computed(() => withdraws.value.filter((item) => item.status === 'REJECTED'))

const metrics = computed(() => [
  { label: '可提现佣金', value: amount(summary.value.available_amount), meta: '已完成订单释放的余额' },
  { label: '冻结佣金', value: amount(summary.value.frozen_amount), meta: '等待收货确认或服务核销' },
  { label: '累计佣金', value: amount(summary.value.total_amount), meta: `${flows.value.filter((item) => item.status === 'SETTLED').length} 笔已结算` },
  { label: '已提现佣金', value: amount(summary.value.withdrawn_amount), meta: `${pendingWithdraws.value.length} 笔申请待审` }
])

function amount(value) {
  return Number(value || 0).toFixed(2)
}

function flowStatusLabel(status) {
  return {
    FROZEN: '冻结中',
    SETTLED: '已结算',
    CANCELED: '已取消'
  }[status] || status
}

function flowStatusClass(status) {
  return {
    FROZEN: 'status-warning',
    SETTLED: 'status-success',
    CANCELED: 'status-muted'
  }[status] || 'status-muted'
}

function withdrawStatusLabel(status) {
  return {
    PENDING: '待审核',
    APPROVED: '已通过',
    REJECTED: '已驳回',
    PAID: '已打款'
  }[status] || status
}

function withdrawStatusClass(status) {
  return {
    PENDING: 'status-warning',
    APPROVED: 'status-success',
    REJECTED: 'status-danger',
    PAID: 'status-primary'
  }[status] || 'status-muted'
}

function withdrawTypeLabel(type) {
  return {
    COMMISSION: '佣金提现',
    BALANCE: '余额提现',
    POINTS: '积分提现'
  }[type] || type
}

function withdrawRemark(item) {
  const auditText = item.reviewed_at ? `审核于 ${dayjs(item.reviewed_at).format('YYYY-MM-DD HH:mm')}` : '尚未审核'
  return item.remark ? `${item.remark} / ${auditText}` : auditText
}

async function loadData() {
  const [summaryData, flowData, withdrawData] = await Promise.all([
    commissionApi.summary(),
    commissionApi.flows(),
    commissionApi.withdraws()
  ])
  summary.value = summaryData || {}
  flows.value = flowData || []
  withdraws.value = withdrawData || []
}

async function submitWithdraw() {
  await commissionApi.createWithdraw({
    withdraw_type: 'COMMISSION',
    amount: Number(withdrawForm.amount || 0),
    remark: withdrawForm.remark
  })
  withdrawForm.amount = ''
  withdrawForm.remark = ''
  showWithdraw.value = false
  activeTab.value = 'withdraws'
  withdrawStatus.value = 'PENDING'
  showSuccessToast('提现申请已提交')
  await loadData()
}

onMounted(loadData)
</script>
