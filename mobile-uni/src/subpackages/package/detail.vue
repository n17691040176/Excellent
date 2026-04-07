<template>
  <view class="page">
    <view class="card">
      <view class="title">{{ detail.package_name || '套餐详情' }}</view>
      <view class="desc">套餐购买后赠送兑换券、推荐奖励券、积分补贴，并可使用 AI 券按比例抵扣。</view>
      <view class="price">套餐售价 {{ detail.package_price || '--' }}</view>
      <view class="info-list">
        <view class="info-row">购买赠券：{{ detail.voucher_reward_rate || 0 }}%</view>
        <view class="info-row">推荐赠券：{{ detail.referral_voucher_rate || 0 }}%</view>
        <view class="info-row">AI 券最高抵扣：{{ detail.ai_coupon_max_deduct_rate || 0 }}%</view>
        <view class="info-row">上架额度：{{ detail.grants_product_quota || 0 }}</view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">购买设置</view>
      <view class="info-row">AI 券余额：{{ Number(aiAccount.available_amount || 0).toFixed(2) }}</view>
      <view class="info-row">建议抵扣上限：{{ maxAiDeduct.toFixed(2) }}</view>
      <input v-model="useAiCouponAmount" class="input" type="digit" placeholder="输入要抵扣的 AI 券数量" />
      <button class="primary-btn" @click="submitOrder">立即购买套餐</button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { assetApi, packageApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const packageId = ref('')
const detail = ref({})
const aiAccount = ref({})
const useAiCouponAmount = ref('0')

const maxAiDeduct = computed(() => {
  const price = Number(detail.value.package_price || 0)
  const rate = Number(detail.value.ai_coupon_max_deduct_rate || 0) / 100
  const balance = Number(aiAccount.value.available_amount || 0)
  return Math.min(price * rate, balance)
})

async function loadData() {
  const [detailData, aiData] = await Promise.all([
    packageApi.detail(packageId.value),
    assetApi.detail('AI_COUPON')
  ])
  detail.value = detailData || {}
  aiAccount.value = aiData || {}
}

async function submitOrder() {
  const amount = Math.min(Number(useAiCouponAmount.value || 0), maxAiDeduct.value)
  const order = await packageApi.createOrder(packageId.value, {
    use_ai_coupon_amount: amount,
    pay_channel: 'cash'
  })
  uni.showToast({ title: '套餐订单已创建', icon: 'success' })
  uni.redirectTo({ url: `/subpackages/order/detail?id=${order.id}` })
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
.page { min-height: 100vh; padding: 32rpx; }
.card { background: #ffffff; border-radius: 24rpx; padding: 32rpx; margin-bottom: 24rpx; }
.title { font-size: 40rpx; font-weight: 600; margin-bottom: 16rpx; }
.desc { font-size: 28rpx; color: #6b7280; line-height: 1.6; margin-bottom: 20rpx; }
.section-title { font-size: 34rpx; font-weight: 600; margin-bottom: 20rpx; }
.price { font-size: 34rpx; font-weight: 700; color: #0d6efd; margin-bottom: 20rpx; }
.info-list { display: grid; gap: 12rpx; }
.info-row { font-size: 26rpx; color: #4b5563; line-height: 1.6; }
.input {
  width: 100%;
  height: 88rpx;
  background: #f5f7fb;
  border-radius: 18rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  margin: 20rpx 0;
  box-sizing: border-box;
}
.primary-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: #0d6efd;
  color: #ffffff;
  font-size: 30rpx;
}
</style>
