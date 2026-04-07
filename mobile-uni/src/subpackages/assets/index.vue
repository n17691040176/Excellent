<template>
  <view class="page">
    <view class="card">
      <view class="title">四类资产账户</view>
      <view class="desc">余额承接设备与广告收益，积分负责补贴与转赠，兑换券用于商城抵扣，AI 券承接自营商城返券与套餐抵扣。</view>
      <view class="metric-grid">
        <view class="metric-card" v-for="item in metrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">快捷操作</view>
      <view class="action-row">
        <button class="secondary-btn" @click="handleSignin">每日签到领券</button>
        <button class="primary-btn" @click="showTransfer = !showTransfer">{{ showTransfer ? '收起转赠' : '积分转赠' }}</button>
      </view>
      <view v-if="showTransfer" class="form-box">
        <input v-model="transferForm.to_user_id" class="input" type="number" placeholder="请输入上级或下级用户 ID" />
        <input v-model="transferForm.amount" class="input" type="digit" placeholder="请输入积分数量" />
        <input v-model="transferForm.remark" class="input" placeholder="可选填写转赠说明" />
        <button class="primary-btn" @click="submitTransfer">提交转赠</button>
      </view>
    </view>

    <view class="card">
      <scroll-view scroll-x class="filter-row">
        <view
          class="filter-pill"
          :class="{ active: activeType === item.value }"
          v-for="item in assetTabs"
          :key="item.value"
          @click="activeType = item.value"
        >
          {{ item.label }}
        </view>
      </scroll-view>

      <view class="section-box">
        <view class="section-title">{{ currentTab.label }}</view>
        <view class="section-desc">{{ currentTab.tip }}</view>
        <view class="info-list">
          <view class="info-row">可用金额：{{ formatAmount(detail.available_amount) }}</view>
          <view class="info-row">冻结金额：{{ formatAmount(detail.frozen_amount) }}</view>
          <view class="info-row">累计收入：{{ formatAmount(detail.total_amount) }}</view>
          <view class="info-row">累计消耗：{{ formatAmount(detail.consumed_amount) }}</view>
          <view class="info-row">累计提现：{{ formatAmount(detail.withdrawn_amount) }}</view>
        </view>
      </view>

      <view class="section-title" style="margin-top: 24rpx;">流水明细</view>
      <view v-if="ledgers.length">
        <view class="line-card" v-for="ledger in ledgers" :key="ledger.id">
          <view class="line-title">{{ ledger.business_type }}</view>
          <view class="line-meta">{{ formatDate(ledger.created_at) }}</view>
          <view class="line-meta">{{ ledger.direction }} / {{ formatAmount(ledger.change_amount) }}</view>
        </view>
      </view>
      <view v-else class="empty-text">暂无资产流水</view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { assetApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const assetTabs = [
  { label: '余额', value: 'BALANCE', tip: '设备流水分佣，可提现或爆款区消费' },
  { label: '积分', value: 'POINTS', tip: '套餐补贴排队、转赠与商城消费' },
  { label: '兑换券', value: 'VOUCHER', tip: '套餐奖励、签到奖励与商城抵扣' },
  { label: 'AI 券', value: 'AI_COUPON', tip: '自营商城返券与套餐 20% 抵扣' }
]

const summary = ref({})
const detail = ref({})
const ledgers = ref([])
const activeType = ref('BALANCE')
const showTransfer = ref(false)
const transferForm = reactive({ to_user_id: '', amount: '', remark: '' })

const metrics = computed(() => [
  { label: '余额', value: formatAmount(summary.value.BALANCE), meta: '设备与广告收益沉淀' },
  { label: '积分', value: formatAmount(summary.value.POINTS), meta: '补贴、转赠、对冲' },
  { label: '兑换券', value: formatAmount(summary.value.VOUCHER), meta: '签到与套餐购券奖励' },
  { label: 'AI 券', value: formatAmount(summary.value.AI_COUPON), meta: '自营商城返券与套餐抵扣' }
])

const currentTab = computed(() => assetTabs.find((item) => item.value === activeType.value) || assetTabs[0])

function formatAmount(value) {
  return Number(value || 0).toFixed(2)
}

function formatDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '--'
}

async function loadSummary() {
  summary.value = await assetApi.summary()
}

async function loadCurrentAsset() {
  const [detailData, ledgerData] = await Promise.all([
    assetApi.detail(activeType.value),
    assetApi.ledgers(activeType.value)
  ])
  detail.value = detailData || {}
  ledgers.value = ledgerData || []
}

async function loadData() {
  await loadSummary()
  await loadCurrentAsset()
}

async function handleSignin() {
  await assetApi.signin()
  uni.showToast({ title: '签到成功，兑换券已到账', icon: 'success' })
  loadData()
}

async function submitTransfer() {
  await assetApi.transferPoints({
    to_user_id: Number(transferForm.to_user_id),
    amount: Number(transferForm.amount),
    remark: transferForm.remark
  })
  transferForm.to_user_id = ''
  transferForm.amount = ''
  transferForm.remark = ''
  showTransfer.value = false
  activeType.value = 'POINTS'
  uni.showToast({ title: '积分转赠成功', icon: 'success' })
  loadData()
}

watch(activeType, () => {
  loadCurrentAsset()
})

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.form-box { margin-top: 20rpx; }
.line-card { margin-top: 16rpx; }
</style>
