<template>
  <view class="page">
    <view class="card hero-card">
      <view class="badge">Commission Center</view>
      <view class="title">把冻结、释放、提现三段佣金流程看清楚</view>
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
        <button class="primary-btn" @click="submitWithdraw">{{ withdrawLoading ? '提交中...' : '提交申请' }}</button>
      </view>
    </view>

    <view class="card">
      <view class="switch-row">
        <view class="switch-tab" :class="{ active: activeTab === 'flows' }" @click="activeTab = 'flows'">返现流水</view>
        <view class="switch-tab" :class="{ active: activeTab === 'withdraws' }" @click="activeTab = 'withdraws'">提现记录</view>
      </view>

      <view v-if="loadError" class="status-card">
        <view class="status-title">佣金数据加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else-if="loading">
        <view class="skeleton-block"></view>
        <view class="skeleton-block short"></view>
      </view>

      <template v-else-if="activeTab === 'flows'">
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
        <view v-if="filteredFlows.length" class="list-wrap">
          <view class="line-card" v-for="item in filteredFlows" :key="item.id">
            <view class="line-head">
              <view class="line-title">订单 {{ item.order_id }}</view>
              <view class="status-pill" :class="commissionFlowStatusTone(item.status)">{{ commissionFlowStatusLabel(item.status) }}</view>
            </view>
            <view class="line-meta">{{ item.level }} 级返现 / 来源用户 {{ item.source_user_id }} / 比例 {{ item.rate }}%</view>
            <view class="line-meta">金额 ¥{{ item.commission_amount }}</view>
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
        <view v-if="filteredWithdraws.length" class="list-wrap">
          <view class="line-card" v-for="item in filteredWithdraws" :key="item.id">
            <view class="line-head">
              <view class="line-title">{{ withdrawTypeLabel(item.withdraw_type) }} / 申请 #{{ item.id }}</view>
              <view class="status-pill" :class="withdrawStatusTone(item.status)">{{ withdrawStatusLabel(item.status) }}</view>
            </view>
            <view class="line-meta">{{ withdrawRemark(item) }}</view>
            <view class="line-meta">金额 ¥{{ item.amount }}</view>
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
import {
  commissionFlowStatusLabel,
  commissionFlowStatusTone,
  normalizeLoadError,
  withdrawStatusLabel,
  withdrawStatusTone
} from '../../utils/ui'

const summary = ref({})
const flows = ref([])
const withdraws = ref([])
const activeTab = ref('flows')
const flowStatus = ref('ALL')
const withdrawStatus = ref('ALL')
const showWithdraw = ref(false)
const withdrawForm = reactive({ amount: '', remark: '' })
const loading = ref(false)
const loadError = ref('')
const withdrawLoading = ref(false)

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

function withdrawTypeLabel(type) {
  return { COMMISSION: '佣金提现', BALANCE: '余额提现', POINTS: '积分提现' }[type] || type
}

function withdrawRemark(item) {
  const auditText = item.reviewed_at ? `审核于 ${String(item.reviewed_at).replace('T', ' ').slice(0, 16)}` : '尚未审核'
  return item.remark ? `${item.remark} / ${auditText}` : auditText
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const [summaryData, flowData, withdrawData] = await Promise.all([
      commissionApi.summary(),
      commissionApi.flows(),
      commissionApi.withdraws()
    ])
    summary.value = summaryData || {}
    flows.value = flowData || []
    withdraws.value = withdrawData || []
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

async function submitWithdraw() {
  withdrawLoading.value = true
  try {
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
  } finally {
    withdrawLoading.value = false
  }
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.hero-card {
  background:
    radial-gradient(circle at top right, rgba(62, 152, 108, 0.22), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(246, 250, 246, 0.98) 100%);
}

.form-box,
.list-wrap {
  margin-top: 20rpx;
}

.line-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 10rpx;
}

.retry-btn {
  margin-top: 20rpx;
}

.short {
  height: 112rpx;
}
</style>
