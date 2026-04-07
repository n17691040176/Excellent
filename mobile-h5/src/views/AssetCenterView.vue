<template>
  <div class="page safe-bottom">
    <van-nav-bar title="资产中心" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-soft">
      <div class="hero-badge">Asset Center</div>
      <h2 class="page-title">把四类资产拆成可理解、可操作、可追踪的账户视图</h2>
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
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">快捷操作</h3>
        <span class="section-link-text">{{ showTransfer ? '积分转赠已展开' : '常用入口' }}</span>
      </div>
      <div class="inline-actions" style="display: grid; grid-template-columns: 1fr 1fr;">
        <van-button round plain type="primary" @click="handleSignin">{{ signinLoading ? '签到中...' : '每日签到领券' }}</van-button>
        <van-button round type="primary" @click="showTransfer = true">积分转赠</van-button>
      </div>
    </div>

    <div class="page-card">
      <van-tabs v-model:active="activeType" animated>
        <van-tab v-for="item in assetTabs" :key="item.value" :title="item.label" :name="item.value">
          <div v-if="loadError" class="state-card">
            <div class="state-title">资产数据加载失败</div>
            <div class="state-desc">{{ loadError }}</div>
            <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
          </div>
          <template v-else>
            <div class="soft-section">
              <div class="section-head" style="margin-bottom: 0.16rem;">
                <div class="zone-title">{{ item.label }}</div>
                <div class="zone-tip">{{ item.tip }}</div>
              </div>
              <div class="product-meta">可用金额 {{ formatAmount(detail.available_amount) }}</div>
              <div class="product-meta">冻结金额 {{ formatAmount(detail.frozen_amount) }}</div>
              <div class="product-meta">累计收入 {{ formatAmount(detail.total_amount) }}</div>
              <div class="product-meta">累计消耗 {{ formatAmount(detail.consumed_amount) }}</div>
              <div class="product-meta">累计提现 {{ formatAmount(detail.withdrawn_amount) }}</div>
            </div>

            <div class="page-card" style="margin: 0.24rem 0 0; padding: 0; box-shadow: none; border: none; background: transparent;">
              <div class="section-head" style="margin-bottom: 0.18rem;">
                <h3 class="cell-group-title" style="margin: 0;">流水明细</h3>
                <span class="section-link-text">{{ ledgers.length }} 条</span>
              </div>
              <div v-if="assetLoading" class="card-stack">
                <div class="skeleton-card short"></div>
              </div>
              <div v-else-if="ledgers.length" class="card-stack">
                <div class="soft-section" v-for="ledger in ledgers" :key="ledger.id">
                  <div class="top-row">
                    <div class="product-name">{{ ledger.business_type }}</div>
                    <div class="status-capsule" :class="assetDirectionClass(ledger.direction)">{{ assetDirectionLabel(ledger.direction) }}</div>
                  </div>
                  <div class="product-meta">{{ formatDate(ledger.created_at) }}</div>
                  <div class="product-meta">变动金额 {{ formatAmount(ledger.change_amount) }}</div>
                </div>
              </div>
              <van-empty v-else image="search" description="暂无资产流水" />
            </div>
          </template>
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
            <van-button round block type="primary" native-type="submit">{{ transferLoading ? '提交中...' : '提交转赠' }}</van-button>
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
import { assetDirectionClass, assetDirectionLabel, normalizeLoadError } from '@/utils/ui'

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
const loadError = ref('')
const assetLoading = ref(false)
const transferLoading = ref(false)
const signinLoading = ref(false)

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
  assetLoading.value = true
  try {
    const [detailData, ledgerData] = await Promise.all([
      assetApi.detail(activeType.value),
      assetApi.ledgers(activeType.value)
    ])
    detail.value = detailData || {}
    ledgers.value = ledgerData || []
  } finally {
    assetLoading.value = false
  }
}

async function loadData() {
  loadError.value = ''
  try {
    await loadSummary()
    await loadCurrentAsset()
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function handleSignin() {
  signinLoading.value = true
  try {
    await assetApi.signin()
    showSuccessToast('签到成功，兑换券已到账')
    await loadData()
  } finally {
    signinLoading.value = false
  }
}

async function submitTransfer() {
  transferLoading.value = true
  try {
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
  } finally {
    transferLoading.value = false
  }
}

watch(activeType, async () => {
  await loadCurrentAsset()
})

onMounted(loadData)
</script>
