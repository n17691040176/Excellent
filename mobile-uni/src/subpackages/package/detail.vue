<template>
  <view class="page">
    <view v-if="loadError" class="card">
      <view class="status-card">
        <view class="status-title">套餐详情加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
    </view>

    <template v-else>
      <view class="card hero-card">
        <view class="badge">Package Detail</view>
        <view class="title">{{ detail.package_name || '套餐详情' }}</view>
        <view class="desc">套餐购买后赠送兑换券、推荐奖励券、积分补贴，并可使用 AI 券按比例抵扣。</view>
        <view class="price-row">
          <view class="price-label">套餐售价</view>
          <view class="price-value">¥{{ detail.package_price || '--' }}</view>
        </view>
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
          <view class="section-title">购买设置</view>
          <view class="section-link">立即成单</view>
        </view>
        <view class="info-list info-gap">
          <view class="info-row">AI 券余额：{{ Number(aiAccount.available_amount || 0).toFixed(2) }}</view>
          <view class="info-row">建议抵扣上限：{{ maxAiDeduct.toFixed(2) }}</view>
          <view class="info-row">本次实付预估：{{ estimatedPayAmount.toFixed(2) }}</view>
        </view>
        <input v-model="useAiCouponAmount" class="input" type="digit" placeholder="输入要抵扣的 AI 券数量" />
        <button class="primary-btn" @click="submitOrder">{{ submitting ? '创建订单中...' : '立即购买套餐' }}</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { assetApi, packageApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError } from '../../utils/ui'

const packageId = ref('')
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
      packageApi.detail(packageId.value),
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
    const order = await packageApi.createOrder(packageId.value, {
      use_ai_coupon_amount: appliedAiAmount.value,
      pay_channel: 'cash'
    })
    uni.showToast({ title: '套餐订单已创建', icon: 'success' })
    uni.redirectTo({ url: `/subpackages/order/detail?id=${order.id}` })
  } finally {
    submitting.value = false
  }
}

onLoad((options) => {
  if (!ensureLogin()) {
    return
  }
  packageId.value = String(options?.id || '')
  if (!packageId.value) {
    uni.showToast({ title: '缺少套餐编号', icon: 'none' })
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

.price-row {
  background: #18342e;
  border-radius: 24rpx;
  padding: 24rpx;
  margin: 18rpx 0 10rpx;
  color: #ffffff;
}

.price-label {
  font-size: 22rpx;
  opacity: 0.72;
  margin-bottom: 10rpx;
}

.price-value {
  font-size: 50rpx;
  font-weight: 700;
  line-height: 1.1;
}

.info-gap {
  margin-top: 8rpx;
}
</style>
