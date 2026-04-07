<template>
  <view class="page">
    <view class="card">
      <view class="title">套餐入场与权益</view>
      <view class="desc">
        购买套餐可获得兑换券、AI 券抵扣资格、积分补贴与商品上架额度，是平台复购区和资产体系的核心入口。
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
      <view class="section-title">套餐列表</view>
      <view v-if="packages.length">
        <view class="list-card" v-for="item in packages" :key="item.id" @click="goDetail(item.id)">
          <view class="item-title">{{ item.package_name }}</view>
          <view class="item-meta">售价 {{ item.package_price }} / AI 券抵扣上限 {{ item.ai_coupon_max_deduct_rate }}%</view>
          <view class="item-meta">
            购券 {{ item.voucher_reward_rate }}% / 推荐赠券 {{ item.referral_voucher_rate }}% / 上架额度 {{ item.grants_product_quota }}
          </view>
        </view>
      </view>
      <view v-else class="empty-text">暂无可购买套餐</view>
    </view>

    <view class="card">
      <view class="section-title">我的套餐资格</view>
      <view v-if="qualifications.length">
        <view class="qualification-card" v-for="item in qualifications" :key="item.order_id">
          <view class="item-title">{{ item.package_name }}</view>
          <view class="item-meta">订单 {{ item.order_id }} / 上架额度 {{ item.grants_product_quota }}</view>
          <view class="item-meta">实付 {{ item.paid_amount }} / 状态 {{ item.order_status }}</view>
        </view>
      </view>
      <view v-else class="empty-text">暂无套餐资格记录</view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { packageApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const packages = ref([])
const qualifications = ref([])

const metrics = computed(() => [
  { label: '套餐数量', value: packages.value.length, meta: '当前可购买套餐' },
  { label: '已购资格', value: qualifications.value.length, meta: '已形成复购或上架资格' },
  {
    label: '最高 AI 抵扣',
    value: `${Math.max(0, ...packages.value.map((item) => Number(item.ai_coupon_max_deduct_rate || 0)))}%`,
    meta: '套餐最高 AI 券抵扣比例'
  },
  {
    label: '最高上架额度',
    value: Math.max(0, ...packages.value.map((item) => Number(item.grants_product_quota || 0))),
    meta: '套餐可解锁商品上架数量'
  }
])

function goDetail(id) {
  uni.navigateTo({ url: `/subpackages/package/detail?id=${id}` })
}

async function loadData() {
  const [packageRows, qualificationRows] = await Promise.all([
    packageApi.list(),
    packageApi.qualifications()
  ])
  packages.value = packageRows || []
  qualifications.value = qualificationRows || []
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 32rpx;
}

.card {
  background: #ffffff;
  border-radius: 24rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
}

.title {
  font-size: 40rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
}

.desc {
  font-size: 28rpx;
  color: #6b7280;
  line-height: 1.6;
}

.section-title {
  font-size: 34rpx;
  font-weight: 600;
  margin-bottom: 20rpx;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 24rpx;
}

.metric-card,
.list-card,
.qualification-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
}

.metric-card {
  min-height: 156rpx;
}

.list-card,
.qualification-card {
  margin-bottom: 16rpx;
}

.metric-label {
  font-size: 24rpx;
  color: #6b7280;
  margin-bottom: 8rpx;
}

.metric-value {
  font-size: 40rpx;
  color: #111827;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.metric-meta,
.item-meta,
.empty-text {
  font-size: 24rpx;
  line-height: 1.6;
  color: #6b7280;
}

.item-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 8rpx;
}
</style>
