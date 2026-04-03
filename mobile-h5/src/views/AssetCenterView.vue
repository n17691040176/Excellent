<template>
  <div class="page safe-bottom">
    <van-nav-bar title="资产中心" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">四类资产账户</h2>
      <p class="page-desc">余额承接设备与广告收益，积分负责补贴与转赠，兑换券用于商城抵扣，AI 券承接自营商城返券与套餐抵扣。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">快捷操作</h3>
      <div class="inline-actions" style="display: grid; grid-template-columns: 1fr 1fr;">
        <van-button round plain type="primary" @click="handleSignin">每日签到领券</van-button>
        <van-button round type="primary" @click="showTransfer = true">积分转赠</van-button>
      </div>
    </div>

    <div class="page-card">
      <van-tabs v-model:active="activeType" animated>
        <van-tab v-for="item in assetTabs" :key="item.value" :title="item.label" :name="item.value">
          <div class="zone-card">
            <div class="zone-head">
              <div class="zone-title">{{ item.label }}</div>
              <div class="zone-tip">{{ item.tip }}</div>
            </div>
            <van-cell-group inset>
              <van-cell title="可用金额" :value="formatAmount(detail.available_amount)" />
              <van-cell title="冻结金额" :value="formatAmount(detail.frozen_amount)" />
              <van-cell title="累计收入" :value="formatAmount(detail.total_amount)" />
              <van-cell title="累计消耗" :value="formatAmount(detail.consumed_amount)" />
              <van-cell title="累计提现" :value="formatAmount(detail.withdrawn_amount)" />
            </van-cell-group>
          </div>

          <div class="page-card" style="margin: 0.24rem 0 0; padding: 0; box-shadow: none; border: none; background: transparent;">
            <h3 class="cell-group-title">流水明细</h3>
            <van-cell-group inset>
              <van-cell v-for="ledger in ledgers" :key="ledger.id" :title="ledger.business_type" :label="formatDate(ledger.created_at)">
                <template #value>
                  <div>{{ ledger.direction }}</div>
                  <div>{{ formatAmount(ledger.change_amount) }}</div>
                </template>
              </van-cell>
            </van-cell-group>
            <van-empty v-if="!ledgers.length" image="search" description="暂无资产流水" />
          </div>
        </van-tab>
      </van-tabs>
    </div>

    <van-popup v-model:show="showTransfer" position="bottom" round :style="{ height: '58%' }">
      <div class="page" style="padding-bottom: 0.4rem;">
        <h3 class="cell-group-title">积分转赠</h3>
        <p class="page-desc">积分仅允许在上下级关系之间转赠，用于补贴对冲或商城消费。</p>
        <van-form @submit="submitTransfer">
          <van-field v-model="transferForm.to_user_id" label="目标用户 ID" type="digit" placeholder="请输入上级或下级用户 ID" />
          <van-field v-model="transferForm.amount" label="转赠积分" type="number" placeholder="请输入积分数量" />
          <van-field v-model="transferForm.remark" label="备注" placeholder="可选填写转赠说明" />
          <div class="submit-bar">
            <van-button round block type="primary" native-type="submit">提交转赠</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { showSuccessToast } from 'vant'

import { assetApi } from '@/api/modules'

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
const transferForm = reactive({
  to_user_id: '',
  amount: '',
  remark: ''
})

const metrics = computed(() => [
  { label: '余额', value: formatAmount(summary.value.BALANCE), meta: '设备与广告收益沉淀' },
  { label: '积分', value: formatAmount(summary.value.POINTS), meta: '补贴、转赠、对冲' },
  { label: '兑换券', value: formatAmount(summary.value.VOUCHER), meta: '签到与套餐购券奖励' },
  { label: 'AI 券', value: formatAmount(summary.value.AI_COUPON), meta: '自营商城返券与套餐抵扣' }
])

function formatAmount(value) {
  return Number(value || 0).toFixed(2)
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
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
  showSuccessToast('签到成功，兑换券已到账')
  await loadData()
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
  showSuccessToast('积分转赠成功')
  activeType.value = 'POINTS'
  await loadData()
}

watch(activeType, async () => {
  await loadCurrentAsset()
})

onMounted(loadData)
</script>
