<template>
  <view class="page">
    <view class="card">
      <view class="badge">Commission Center</view>
      <view class="title">佣金结算与提现进度</view>
      <view class="desc">下级支付后佣金先冻结，确认收货或服务核销后转入可提现余额；提现申请再进入审核流程。</view>
      <view class="metric-grid">
        <view class="metric-card" v-for="item in metrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <view>
          <view class="section-title">提现申请</view>
          <view class="section-desc">仅当佣金进入可提现余额后才能申请，审核结果会记录在下方提现记录中。</view>
        </view>
        <view class="section-link" @click="showWithdraw = !showWithdraw">{{ showWithdraw ? '收起' : '申请提现' }}</view>
      </view>
      <view class="tiny-grid">
        <view class="tiny-panel">
          <view class="tiny-title">待审核</view>
          <view class="tiny-value">{{ pendingWithdraws.length }}</view>
        </view>
        <view class="tiny-panel">
          <view class="tiny-title">已通过</view>
          <view class="tiny-value">{{ approvedWithdraws.length }}</view>
        </view>
        <view class="tiny-panel">
          <view class="tiny-title">已驳回</view>
          <view class="tiny-value">{{ rejectedWithdraws.length }}</view>
        </view>
      </view>
      <view v-if="showWithdraw" class="form-box">
        <input v-model="withdrawForm.amount" class="input" type="digit" placeholder="请输入提现金额" />
        <input v-model="withdrawForm.remark" class="input" placeholder="可填写提现说明" />
        <button class="primary-btn" @click="submitWithdraw">提交申请</button>
      </view>
    </view>

    <view class="card">
      <view class="switch-row">
        <view class="switch-tab" :class="{ active: activeTab === 'flows' }" @click="activeTab = 'flows'">返现流水</view>
        <view class="switch-tab" :class="{ active: activeTab === 'withdraws' }" @click="activeTab = 'withdraws'">提现记录</view>
      </view>

      <template v-if="activeTab === 'flows'">
        <scroll-view scroll-x class="filter-row">
          <view
            class="filter-pill"
            :class="{ active: flowStatus === item.value }"
            v-for="item in flowFilters"
            :key="item.value"
            @click="flowStatus = item.value"
          >
            {{ item.label }}
          </view>
        </scroll-view>
        <view v-if="filteredFlows.length">
          <view class="line-card" v-for="item in filteredFlows" :key="item.id">
            <view class="line-title">订单 {{ item.order_id }}</view>
            <view class="line-meta">{{ item.level }} 级返现 / 来源用户 {{ item.source_user_id }} / 比例 {{ item.rate }}%</view>
            <view class="line-meta">金额 {{ item.commission_amount }} / {{ flowStatusLabel(item.status) }}</view>
          </view>
        </view>
        <view v-else class="empty-text">当前筛选下暂无返现流水</view>
      </template>

      <template v-else>
        <scroll-view scroll-x class="filter-row">
          <view
            class="filter-pill"
            :class="{ active: withdrawStatus === item.value }"
            v-for="item in withdrawFilters"
            :key="item.value"
            @click="withdrawStatus = item.value"
          >
            {{ item.label }}
          </view>
        </scroll-view>
        <view v-if="filteredWithdraws.length">
          <view class="line-card" v-for="item in filteredWithdraws" :key="item.id">
            <view class="line-title">{{ withdrawTypeLabel(item.withdraw_type) }} / 申请 #{{ item.id }}</view>
            <view class="line-meta">{{ withdrawRemark(item) }}</view>
            <view class="line-meta">金额 {{ item.amount }} / {{ withdrawStatusLabel(item.status) }}</view>
          </view>
        </view>
        <view v-else class="empty-text">当前筛选下暂无提现记录</view>
      </template>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { commissionApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const summary = ref({})
const flows = ref([])
const withdraws = ref([])
const activeTab = ref('flows')
const flowStatus = ref('ALL')
const withdrawStatus = ref('ALL')
const showWithdraw = ref(false)
const withdrawForm = reactive({ amount: '', remark: '' })

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

const filteredFlows = computed(() => (flowStatus.value === 'ALL' ? flows.value : flows.value.filter((item) => item.status === flowStatus.value)))
const filteredWithdraws = computed(() => (withdrawStatus.value === 'ALL' ? withdraws.value : withdraws.value.filter((item) => item.status === withdrawStatus.value)))
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
  return { FROZEN: '冻结中', SETTLED: '已结算', CANCELED: '已取消' }[status] || status
}

function withdrawStatusLabel(status) {
  return { PENDING: '待审核', APPROVED: '已通过', REJECTED: '已驳回', PAID: '已打款' }[status] || status
}

function withdrawTypeLabel(type) {
  return { COMMISSION: '佣金提现', BALANCE: '余额提现', POINTS: '积分提现' }[type] || type
}

function withdrawRemark(item) {
  const auditText = item.reviewed_at ? `审核于 ${String(item.reviewed_at).replace('T', ' ').slice(0, 16)}` : '尚未审核'
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
  uni.showToast({ title: '提现申请已提交', icon: 'success' })
  loadData()
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.section-head { display: flex; justify-content: space-between; gap: 16rpx; align-items: flex-start; margin-bottom: 20rpx; }
.section-link { font-size: 26rpx; color: #0d6efd; }
.form-box { margin-top: 20rpx; }
</style>
