<template>
  <view class="page">
    <view class="card hero-card">
      <view class="badge">Local Life</view>
      <view class="title">把联盟商家、服务供给和核销订单放进同一块看板</view>
      <view class="desc">
        本地生活专区围绕到店服务展开，用户需要先判断商家规模和服务供给，再快速跟进支付、核销和完成状态。
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
        <view class="section-title">核销进度</view>
        <view class="section-link" @click="goOrders">查看订单</view>
      </view>
      <view class="section-desc">支付后进入待核销状态，门店核销完成后再进入结算。</view>
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

      <view v-if="loadError" class="status-card">
        <view class="status-title">本地生活数据加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else-if="loading">
        <view class="skeleton-block"></view>
        <view class="skeleton-block short"></view>
      </view>

      <template v-else-if="activeTab === 'services'">
        <view v-if="services.length" class="card-list">
          <view class="service-card tap-item" v-for="item in services" :key="item.id" @click="goService(item.id)">
            <view class="service-top">
              <view>
                <view class="line-title">{{ item.service_name }}</view>
                <view class="line-meta">门市价 ¥{{ item.market_price || '--' }} / 商家 {{ item.merchant_id }}</view>
              </view>
              <view class="service-price">¥{{ item.sale_price }}</view>
            </view>
            <view class="service-tags">
              <view class="service-tag">{{ item.verification_type || '待定核销' }}</view>
              <view class="service-tag">{{ item.service_type || '到店服务' }}</view>
            </view>
            <view class="line-meta">点击进入详情页，可直接下单并指定门店。</view>
          </view>
        </view>
        <view v-else class="empty-text">暂无本地生活服务</view>
      </template>

      <template v-else-if="activeTab === 'merchants'">
        <view v-if="merchants.length" class="card-list">
          <view class="merchant-card" v-for="item in merchants" :key="item.id">
            <view class="line-title">{{ item.merchant_name }}</view>
            <view class="line-meta">{{ item.category_name || '未分类' }} / {{ item.contact_phone || '--' }}</view>
            <view class="line-meta">状态 {{ item.status || '--' }}</view>
            <button class="minor-btn merchant-btn" @click="filterByMerchant(item.id, item.merchant_name)">查看该商家服务</button>
          </view>
        </view>
        <view v-else class="empty-text">暂无联盟商家</view>
      </template>

      <template v-else>
        <view v-if="recentOrders.length" class="card-list">
          <view class="order-card tap-item" v-for="item in recentOrders" :key="item.id" @click="goOrder(item.id)">
            <view class="service-top">
              <view class="line-title">{{ item.order_no }}</view>
              <view class="order-pill" :class="orderStatusTone(item.order_status)">{{ orderLabel(item.order_status) }}</view>
            </view>
            <view class="line-meta">应付金额 ¥{{ item.payable_amount }}</view>
            <view class="line-meta">点击查看详情和后续核销进度。</view>
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
import { normalizeLoadError, orderStatusLabel, orderStatusTone } from '../../utils/ui'

const activeTab = ref('services')
const merchants = ref([])
const services = ref([])
const revenue = ref({})
const orders = ref([])
const loading = ref(false)
const loadError = ref('')

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
  return orderStatusLabel(status, { PAID: '待核销' })
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

async function filterByMerchant(merchantId, merchantName) {
  services.value = await localLifeApi.services(merchantId)
  activeTab.value = 'services'
  uni.showToast({ title: `${merchantName} 服务已筛出`, icon: 'none' })
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
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
    radial-gradient(circle at 100% 0%, rgba(232, 192, 149, 0.24), transparent 34%),
    radial-gradient(circle at 0% 12%, rgba(208, 220, 244, 0.28), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 247, 241, 0.98) 100%);
}

.card-list {
  display: grid;
  gap: 16rpx;
}

.service-card,
.merchant-card,
.order-card {
  background: var(--theme-surface-muted);
  border-radius: 24rpx;
  padding: 24rpx;
  border: 1rpx solid var(--theme-border);
}

.service-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.service-price {
  font-size: 38rpx;
  font-weight: 700;
  color: var(--theme-accent);
  line-height: 1;
}

.service-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.service-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: var(--theme-accent-soft);
  color: var(--theme-accent);
  font-size: 22rpx;
  border: 1rpx solid var(--theme-accent-border);
}

.merchant-btn,
.retry-btn {
  margin-top: 16rpx;
}
</style>
