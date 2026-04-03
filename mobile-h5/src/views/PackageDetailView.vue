<template>
  <div class="page safe-bottom">
    <van-nav-bar title="套餐详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">{{ detail.package_name || '套餐详情' }}</h2>
      <p class="page-desc">套餐购买后赠送兑换券、推荐奖励券、积分补贴，并可使用 AI 券按比例抵扣。</p>
      <div class="price-row">
        <div class="price-main">{{ detail.package_price || '--' }}</div>
        <div class="price-sub">套餐售价</div>
      </div>
      <van-cell-group inset>
        <van-cell title="购买赠券" :value="`${detail.voucher_reward_rate || 0}%`" />
        <van-cell title="推荐赠券" :value="`${detail.referral_voucher_rate || 0}%`" />
        <van-cell title="AI 券最高抵扣" :value="`${detail.ai_coupon_max_deduct_rate || 0}%`" />
        <van-cell title="上架额度" :value="String(detail.grants_product_quota || 0)" />
      </van-cell-group>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">购买设置</h3>
      <van-cell-group inset>
        <van-cell title="AI 券余额" :value="Number(aiAccount.available_amount || 0).toFixed(2)" />
        <van-cell title="建议抵扣上限" :value="maxAiDeduct.toFixed(2)" />
      </van-cell-group>
      <van-field v-model="useAiCouponAmount" type="number" label="使用 AI 券" placeholder="输入要抵扣的 AI 券数量" />
      <div class="submit-bar">
        <van-button round block type="primary" @click="submitOrder">立即购买套餐</van-button>
      </div>
      <p class="page-desc" style="margin-top: 0.18rem;">当前后端会先生成订单，订单支付状态可由后台演示流转或后续接入正式支付。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'

import { assetApi, packageApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
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
    packageApi.detail(route.params.id),
    assetApi.detail('AI_COUPON')
  ])
  detail.value = detailData || {}
  aiAccount.value = aiData || {}
}

async function submitOrder() {
  const amount = Math.min(Number(useAiCouponAmount.value || 0), maxAiDeduct.value)
  const order = await packageApi.createOrder(route.params.id, {
    use_ai_coupon_amount: amount,
    pay_channel: 'cash'
  })
  showSuccessToast('套餐订单已创建')
  router.replace(`/orders/${order.id}`)
}

onMounted(loadData)
</script>
