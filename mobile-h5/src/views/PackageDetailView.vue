<template>
  <div class="page safe-bottom">
    <van-nav-bar title="套餐详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div v-if="loadError" class="page-card">
      <div class="state-card">
        <div class="state-title">套餐详情加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
    </div>

    <template v-else>
      <div class="page-card hero-soft">
        <div class="hero-badge">Package Detail</div>
        <h2 class="page-title">{{ detail.package_name || '套餐详情' }}</h2>
        <p class="page-desc">套餐购买后赠送兑换券、推荐奖励券、积分补贴，并可使用 AI 券按比例抵扣。</p>
        <div class="price-panel">
          <div class="price-panel-label">套餐售价</div>
          <div class="price-panel-value">¥{{ detail.package_price || '--' }}</div>
        </div>
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
          <h3 class="cell-group-title" style="margin: 0;">购买设置</h3>
          <span class="section-link-text">立即成单</span>
        </div>
        <div class="soft-section">
          <div class="product-meta">AI 券余额 {{ Number(aiAccount.available_amount || 0).toFixed(2) }}</div>
          <div class="product-meta">建议抵扣上限 {{ maxAiDeduct.toFixed(2) }}</div>
          <div class="product-meta">本次实付预估 {{ estimatedPayAmount.toFixed(2) }}</div>
        </div>
        <van-field v-model="useAiCouponAmount" type="number" label="使用 AI 券" placeholder="输入要抵扣的 AI 券数量" />
        <div class="submit-bar">
          <van-button round block type="primary" @click="submitOrder">{{ submitting ? '创建订单中...' : '立即购买套餐' }}</van-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'

import { assetApi, packageApi } from '@/api/modules'
import { normalizeLoadError } from '@/utils/ui'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const aiAccount = ref({})
const useAiCouponAmount = ref('0')
const loadError = ref('')
const submitting = ref(false)

const maxAiDeduct = computed(() => {
  const price = Number(detail.value.package_price || 0)
  const rate = Number(detail.value.ai_coupon_max_deduct_rate || 0) / 100
  const balance = Number(aiAccount.value.available_amount || 0)
  return Math.min(price * rate, balance)
})

const appliedAiAmount = computed(() => Math.min(Number(useAiCouponAmount.value || 0), maxAiDeduct.value))
const estimatedPayAmount = computed(() => Math.max(0, Number(detail.value.package_price || 0) - appliedAiAmount.value))
const metrics = computed(() => [
  { label: '购买赠券', value: `${detail.value.voucher_reward_rate || 0}%`, meta: '购买套餐后发放兑换券' },
  { label: '推荐赠券', value: `${detail.value.referral_voucher_rate || 0}%`, meta: '推荐下单后追加赠券' },
  { label: 'AI 券抵扣', value: `${detail.value.ai_coupon_max_deduct_rate || 0}%`, meta: '单笔订单可抵扣上限' },
  { label: '上架额度', value: detail.value.grants_product_quota || 0, meta: '可解锁商品上架数量' }
])

async function loadData() {
  loadError.value = ''
  try {
    const [detailData, aiData] = await Promise.all([
      packageApi.detail(route.params.id),
      assetApi.detail('AI_COUPON')
    ])
    detail.value = detailData || {}
    aiAccount.value = aiData || {}
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function submitOrder() {
  submitting.value = true
  try {
    const order = await packageApi.createOrder(route.params.id, {
      use_ai_coupon_amount: appliedAiAmount.value,
      pay_channel: 'cash'
    })
    showSuccessToast('套餐订单已创建')
    router.replace(`/orders/${order.id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
