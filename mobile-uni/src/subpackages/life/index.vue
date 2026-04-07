<template>
  <view class="page">
    <view class="card">
      <view class="title">联盟商家与到店服务</view>
      <view class="desc">本地生活专区对接百业联盟商家，服务可按规则产生区县代理、市代理、个人与商家分佣，并带动设备与广告收益。</view>
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
        <view>
          <view class="section-title">快捷入口</view>
          <view class="section-desc">可直接查看本地生活订单进度，支付后进入待核销状态。</view>
        </view>
        <view class="section-link" @click="goOrders">查看订单</view>
      </view>
      <view class="tiny-grid">
        <view class="tiny-panel">
          <view class="tiny-title">待支付</view>
          <view class="tiny-value">{{ orderSummary.created }}</view>
        </view>
        <view class="tiny-panel">
          <view class="tiny-title">待核销</view>
          <view class="tiny-value">{{ orderSummary.paid }}</view>
        </view>
        <view class="tiny-panel">
          <view class="tiny-title">已完成</view>
          <view class="tiny-value">{{ orderSummary.confirmed }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="switch-row">
        <view class="switch-tab" :class="{ active: activeTab === 'services' }" @click="activeTab = 'services'">服务列表</view>
        <view class="switch-tab" :class="{ active: activeTab === 'merchants' }" @click="activeTab = 'merchants'">联盟商家</view>
        <view class="switch-tab" :class="{ active: activeTab === 'orders' }" @click="activeTab = 'orders'">最近订单</view>
      </view>

      <template v-if="activeTab === 'services'">
        <view v-if="services.length">
          <view class="line-card" v-for="item in services" :key="item.id" @click="goService(item.id)">
            <view class="line-title">{{ item.service_name }}</view>
            <view class="line-meta">售价 {{ item.sale_price }} / 门市价 {{ item.market_price || '--' }}</view>
            <view class="line-meta">商家 {{ item.merchant_id }} / 核销方式 {{ item.verification_type }}</view>
          </view>
        </view>
        <view v-else class="empty-text">暂无本地生活服务</view>
      </template>

      <template v-else-if="activeTab === 'merchants'">
        <view v-if="merchants.length">
          <view class="line-card" v-for="item in merchants" :key="item.id">
            <view class="line-title">{{ item.merchant_name }}</view>
            <view class="line-meta">{{ item.category_name }} / {{ item.contact_phone }}</view>
            <view class="line-meta">状态 {{ item.status }}</view>
            <button class="minor-btn" @click="filterByMerchant(item.id)">查看服务</button>
          </view>
        </view>
        <view v-else class="empty-text">暂无联盟商家</view>
      </template>

      <template v-else>
        <view v-if="recentOrders.length">
          <view class="line-card" v-for="item in recentOrders" :key="item.id" @click="goOrder(item.id)">
            <view class="line-title">{{ item.order_no }}</view>
            <view class="line-meta">应付 {{ item.payable_amount }} / {{ orderLabel(item.order_status) }}</view>
          </view>
        </view>
        <view v-else class="empty-text">暂无本地生活订单</view>
      </template>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { localLifeApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const activeTab = ref('services')
const merchants = ref([])
const services = ref([])
const revenue = ref({})
const orders = ref([])

const metrics = computed(() => [
  { label: '联盟商家', value: merchants.value.length, meta: '本地生活接入商家总数' },
  { label: '服务数量', value: services.value.length, meta: '可下单到店服务总数' },
  { label: '设备收益', value: Number(revenue.value.device_revenue_total || 0).toFixed(2), meta: '快充宝、设备流水等' },
  { label: '广告收益', value: Number(revenue.value.ad_revenue_total || 0).toFixed(2), meta: '门店广告与推广位收益' }
])

const orderSummary = computed(() => ({
  created: orders.value.filter((item) => item.order_status === 'CREATED').length,
  paid: orders.value.filter((item) => item.order_status === 'PAID').length,
  confirmed: orders.value.filter((item) => item.order_status === 'CONFIRMED').length
}))

const recentOrders = computed(() => orders.value.slice(0, 5))

function orderLabel(status) {
  return { CREATED: '待支付', PAID: '待核销', CONFIRMED: '已完成', CLOSED: '已关闭' }[status] || status
}

function goService(id) {
  uni.navigateTo({ url: `/subpackages/life/service-detail?id=${id}` })
}

function goOrder(id) {
  uni.navigateTo({ url: `/subpackages/order/detail?id=${id}` })
}

function goOrders() {
  uni.navigateTo({ url: '/subpackages/life/orders' })
}

async function filterByMerchant(merchantId) {
  services.value = await localLifeApi.services(merchantId)
  activeTab.value = 'services'
}

async function loadData() {
  const [merchantRows, serviceRows, revenueData, orderRows] = await Promise.all([
    localLifeApi.merchants(),
    localLifeApi.services(),
    localLifeApi.revenueSummary(),
    localLifeApi.orders()
  ])
  merchants.value = merchantRows || []
  services.value = serviceRows || []
  revenue.value = revenueData || {}
  orders.value = orderRows || []
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.section-head { display: flex; justify-content: space-between; gap: 16rpx; align-items: flex-start; margin-bottom: 20rpx; }
.section-link { font-size: 26rpx; color: #0d6efd; }
.minor-btn { margin-top: 16rpx; height: 72rpx; line-height: 72rpx; border-radius: 16rpx; font-size: 26rpx; }
</style>
