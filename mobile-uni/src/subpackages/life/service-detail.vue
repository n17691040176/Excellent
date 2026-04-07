<template>
  <view class="page">
    <view class="card">
      <view class="title">{{ detail.service_name || '本地生活服务' }}</view>
      <view class="desc">到店服务下单后生成核销订单，核销完成会触发佣金冻结与结算逻辑。</view>
      <view class="price">服务售价 {{ detail.sale_price || '--' }}</view>
      <view class="info-list">
        <view class="info-row">门市价：{{ detail.market_price || '--' }}</view>
        <view class="info-row">服务类型：{{ detail.service_type || '--' }}</view>
        <view class="info-row">核销方式：{{ detail.verification_type || '--' }}</view>
        <view class="info-row">状态：{{ detail.status || '--' }}</view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">下单设置</view>
      <input v-model="quantity" class="input" type="number" placeholder="购买数量，默认 1" />
      <input v-model="pointsAmount" class="input" type="digit" placeholder="输入积分抵扣金额" />
      <input v-model="balanceAmount" class="input" type="digit" placeholder="输入余额抵扣金额" />
      <input v-model="storeId" class="input" type="number" placeholder="可选指定门店 ID" />
      <button class="primary-btn" @click="submitOrder">提交服务订单</button>
    </view>

    <view class="card">
      <view class="section-title">可选门店</view>
      <view v-if="stores.length">
        <view class="line-card" v-for="item in stores" :key="item.id">
          <view class="line-title">{{ item.store_name }}</view>
          <view class="line-meta">{{ joinAddress(item) }}</view>
          <view class="line-meta">状态 {{ item.status }}</view>
        </view>
      </view>
      <view v-else class="empty-text">当前服务暂无门店信息</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { localLifeApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const serviceId = ref('')
const detail = ref({})
const stores = ref([])
const quantity = ref('1')
const pointsAmount = ref('0')
const balanceAmount = ref('0')
const storeId = ref('')

function joinAddress(item) {
  return [item.province, item.city, item.district, item.detail_address].filter(Boolean).join(' ')
}

async function loadData() {
  const service = await localLifeApi.serviceDetail(serviceId.value)
  detail.value = service || {}
  stores.value = service?.merchant_id ? await localLifeApi.stores(service.merchant_id) : []
  if (service?.store_id) {
    storeId.value = String(service.store_id)
  }
}

async function submitOrder() {
  const order = await localLifeApi.createOrder({
    service_id: Number(serviceId.value),
    store_id: storeId.value ? Number(storeId.value) : null,
    quantity: Number(quantity.value || 1),
    points_amount: Number(pointsAmount.value || 0),
    balance_amount: Number(balanceAmount.value || 0)
  })
  uni.showToast({ title: '服务订单已创建', icon: 'success' })
  uni.redirectTo({ url: `/subpackages/order/detail?id=${order.id}` })
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
.price { font-size: 34rpx; font-weight: 700; color: #0d6efd; margin-bottom: 20rpx; }
</style>
