<template>
  <view class="page packages-page">
    <view class="card hero-card">
      <view class="badge">Package Center</view>
      <view class="title">先看入场门槛，再看能换来什么资格</view>
      <view class="desc">
        套餐页改成先给全局判断，再列出每档权益和已购资格。用户不需要逐条比对，也能快速知道哪一档更适合当前阶段。
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
        <view class="section-title">可选套餐</view>
        <view class="section-link">{{ packages.length }} 档</view>
      </view>

      <view v-if="loadError" class="status-card">
        <view class="status-title">套餐加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else-if="loading">
        <view class="skeleton-block"></view>
        <view class="skeleton-block"></view>
      </view>
      <view v-else-if="packages.length" class="package-list">
        <view class="package-card tap-item" v-for="item in packages" :key="item.id" @click="goDetail(item.id)">
          <view class="package-head">
            <view>
              <view class="item-title">{{ item.package_name }}</view>
              <view class="item-meta">AI 券抵扣上限 {{ item.ai_coupon_max_deduct_rate }}%</view>
            </view>
            <view class="price-box">
              <view class="price-label">到手门槛</view>
              <view class="price-value">¥{{ item.package_price }}</view>
            </view>
          </view>
          <view class="package-meta-grid">
            <view class="meta-chip">购券 {{ item.voucher_reward_rate }}%</view>
            <view class="meta-chip">推荐赠券 {{ item.referral_voucher_rate }}%</view>
            <view class="meta-chip">上架额度 {{ item.grants_product_quota }}</view>
          </view>
          <view class="item-meta">
            购买后进入复购体系，同时获得兑换券、积分补贴和商城经营资格，适合作为平台消费和推广的统一起点。
          </view>
        </view>
      </view>
      <view v-else class="empty-text">暂无可购买套餐</view>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="section-title">我的套餐资格</view>
        <view class="section-link">{{ qualifications.length }} 条</view>
      </view>
      <view v-if="!loadError && loading">
        <view class="skeleton-block short"></view>
      </view>
      <view v-else-if="qualifications.length" class="qualification-list">
        <view class="qualification-card" v-for="item in qualifications" :key="item.order_id">
          <view class="qualification-top">
            <view class="item-title">{{ item.package_name }}</view>
            <view class="status-pill" :class="orderStatusTone(item.order_status)">{{ orderStatusLabel(item.order_status) }}</view>
          </view>
          <view class="item-meta">订单 {{ item.order_id }} / 上架额度 {{ item.grants_product_quota }}</view>
          <view class="item-meta">实付 ¥{{ item.paid_amount }} / 已沉淀可持续使用的经营资格</view>
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
import { normalizeLoadError, orderStatusLabel, orderStatusTone } from '../../utils/ui'

const packages = ref([])
const qualifications = ref([])
const loading = ref(false)
const loadError = ref('')

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
  loading.value = true
  loadError.value = ''
  try {
    const [packageRows, qualificationRows] = await Promise.all([
      packageApi.list(),
      packageApi.qualifications()
    ])
    packages.value = packageRows || []
    qualifications.value = qualificationRows || []
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
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
    radial-gradient(circle at top left, rgba(62, 152, 108, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 246, 0.98) 100%);
}

.package-list,
.qualification-list {
  display: grid;
  gap: 16rpx;
}

.package-card {
  background: linear-gradient(180deg, #fcfdfa 0%, #f4f8f3 100%);
  border-radius: 24rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(21, 55, 45, 0.05);
}

.package-head,
.qualification-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.price-box {
  min-width: 164rpx;
  padding: 18rpx;
  border-radius: 22rpx;
  background: #18342e;
  color: #ffffff;
  box-sizing: border-box;
}

.price-label {
  font-size: 20rpx;
  opacity: 0.72;
  margin-bottom: 8rpx;
}

.price-value {
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1;
}

.package-meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-bottom: 14rpx;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #e7f6ef;
  color: #1e8f64;
  font-size: 22rpx;
}
</style>
