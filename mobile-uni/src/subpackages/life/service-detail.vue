<template>
  <view class="page">
    <view v-if="loadError" class="card">
      <view class="status-card">
        <view class="status-title">服务详情加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
    </view>

    <template v-else>
      <view class="card hero-card">
        <view class="badge">Service Detail</view>
        <view class="title">{{ detail.service_name || '本地生活服务' }}</view>
        <view class="desc">到店服务下单后生成核销订单，核销完成会触发佣金冻结与结算逻辑。</view>
        <view class="service-price">¥{{ detail.sale_price || '--' }}</view>
        <view class="hero-tags">
          <view class="hero-tag">{{ detail.service_type || '服务类型待定' }}</view>
          <view class="hero-tag">{{ detail.verification_type || '核销方式待定' }}</view>
          <view class="hero-tag">{{ detail.status || '状态待定' }}</view>
        </view>
        <view class="info-list">
          <view class="info-row">门市价：{{ detail.market_price || '--' }}</view>
          <view class="info-row">服务类型：{{ detail.service_type || '--' }}</view>
          <view class="info-row">核销方式：{{ detail.verification_type || '--' }}</view>
          <view class="info-row">状态：{{ detail.status || '--' }}</view>
        </view>
      </view>

      <view class="card">
        <view class="section-head">
          <view class="section-title">下单设置</view>
          <view class="section-link">实时创建</view>
        </view>
        <input v-model="quantity" class="input" type="number" placeholder="购买数量，默认 1" />
        <input v-model="pointsAmount" class="input" type="digit" placeholder="输入积分抵扣金额" />
        <input v-model="balanceAmount" class="input" type="digit" placeholder="输入余额抵扣金额" />
        <input v-model="storeId" class="input" type="number" placeholder="可选指定门店 ID" />
        <button class="primary-btn" @click="submitOrder">{{ submitting ? '提交中...' : '提交服务订单' }}</button>
      </view>

      <view class="card">
        <view class="section-head">
          <view class="section-title">可选门店</view>
          <view class="section-link">{{ stores.length }} 家</view>
        </view>
        <view v-if="stores.length" class="store-list">
          <view class="store-card" v-for="item in stores" :key="item.id" @click="pickStore(item.id)">
            <view class="line-title">{{ item.store_name }}</view>
            <view class="line-meta">{{ joinAddress(item) }}</view>
            <view class="line-meta">状态 {{ item.status || '--' }}</view>
          </view>
        </view>
        <view v-else class="empty-text">当前服务暂无门店信息</view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { localLifeApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError } from '../../utils/ui'

const serviceId = ref('')
const detail = ref({})
const stores = ref([])
const quantity = ref('1')
const pointsAmount = ref('0')
const balanceAmount = ref('0')
const storeId = ref('')
const loadError = ref('')
const submitting = ref(false)

function joinAddress(item) {
  return [item.province, item.city, item.district, item.detail_address].filter(Boolean).join(' ')
}

function pickStore(id) {
  storeId.value = String(id)
  uni.showToast({ title: `已选择门店 ${id}`, icon: 'none' })
}

async function loadData() {
  loadError.value = ''
  try {
    const service = await localLifeApi.serviceDetail(serviceId.value)
    detail.value = service || {}
    stores.value = service?.merchant_id ? await localLifeApi.stores(service.merchant_id) : []
    if (service?.store_id) {
      storeId.value = String(service.store_id)
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function submitOrder() {
  submitting.value = true
  try {
    const order = await localLifeApi.createOrder({
      service_id: Number(serviceId.value),
      store_id: storeId.value ? Number(storeId.value) : null,
      quantity: Number(quantity.value || 1),
      points_amount: Number(pointsAmount.value || 0),
      balance_amount: Number(balanceAmount.value || 0)
    })
    uni.showToast({ title: '服务订单已创建', icon: 'success' })
    uni.redirectTo({ url: `/subpackages/order/detail?id=${order.id}` })
  } finally {
    submitting.value = false
  }
}

onLoad((options) => {
  if (!ensureLogin()) {
    return
  }
  serviceId.value = String(options?.id || '')
  if (!serviceId.value) {
    uni.showToast({ title: '缺少服务编号', icon: 'none' })
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

.service-price {
  font-size: 48rpx;
  font-weight: 700;
  color: #1e8f64;
  margin-bottom: 18rpx;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-bottom: 20rpx;
}

.hero-tag {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #e7f6ef;
  color: #1e8f64;
  font-size: 22rpx;
}

.store-list {
  display: grid;
  gap: 16rpx;
}

.store-card {
  background: linear-gradient(180deg, #fcfdfa 0%, #f4f8f3 100%);
  border-radius: 24rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(21, 55, 45, 0.05);
}

.retry-btn {
  margin-top: 20rpx;
}
</style>
