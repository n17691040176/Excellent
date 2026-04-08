<template>
  <view class="page">
    <view class="card hero-card">
      <view class="badge">Local Life Orders</view>
      <view class="title">围绕核销节点跟进到店服务订单</view>
      <view class="desc">本地生活订单支付后进入待核销状态，核销完成后再触发后续佣金结算。</view>
      <view class="metric-grid">
        <view class="metric-card" v-for="item in metrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <scroll-view scroll-x class="filter-row">
        <view
          class="filter-pill"
          :class="{ active: activeFilter === item.value }"
          v-for="item in filters"
          :key="item.value"
          @click="activeFilter = item.value"
        >
          {{ item.label }}
        </view>
      </scroll-view>

      <view v-if="loadError" class="status-card">
        <view class="status-title">订单列表加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else-if="loading">
        <view class="skeleton-block"></view>
        <view class="skeleton-block short"></view>
      </view>
      <view v-else-if="filteredOrders.length" class="order-list">
        <view class="order-card tap-item" v-for="item in filteredOrders" :key="item.id" @click="goDetail(item.id)">
          <view class="order-top">
            <view class="line-title">{{ item.order_no }}</view>
            <view class="order-pill" :class="orderStatusTone(item.order_status)">{{ statusLabel(item) }}</view>
          </view>
          <view class="line-meta">{{ statusDesc(item) }}</view>
          <view class="line-meta">应付金额 ¥{{ item.payable_amount }}</view>
        </view>
      </view>
      <view v-else class="empty-text">当前状态下暂无本地生活订单</view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { localLifeApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError, orderStatusLabel, orderStatusTone } from '../../utils/ui'

const rows = ref([])
const activeFilter = ref('ALL')
const loading = ref(false)
const loadError = ref('')

const filters = [
  { label: '全部', value: 'ALL' },
  { label: '待支付', value: 'CREATED' },
  { label: '待核销', value: 'PAID' },
  { label: '已完成', value: 'CONFIRMED' },
  { label: '已关闭', value: 'CLOSED' }
]

const filteredOrders = computed(() => (
  activeFilter.value === 'ALL' ? rows.value : rows.value.filter((item) => item.order_status === activeFilter.value)
))

const metrics = computed(() => [
  { label: '本地生活订单', value: rows.value.length, meta: '到店服务总订单数' },
  { label: '待支付', value: rows.value.filter((item) => item.order_status === 'CREATED').length, meta: '等待用户完成支付' },
  { label: '待核销', value: rows.value.filter((item) => item.order_status === 'PAID').length, meta: '支付完成，等待门店核销' },
  { label: '已完成', value: rows.value.filter((item) => item.order_status === 'CONFIRMED').length, meta: '核销完成并进入结算' }
])

function statusLabel(item) {
  return orderStatusLabel(item.order_status, { PAID: '待核销' })
}

function statusDesc(item) {
  return {
    CREATED: '服务订单已创建，待支付后生成可核销状态',
    PAID: '已支付，等待门店或后台核销确认',
    CONFIRMED: '已完成核销，佣金链路已结算',
    CLOSED: '订单已关闭'
  }[item.order_status] || `支付状态 ${item.pay_status}`
}

function goDetail(id) {
  uni.navigateTo({ url: `/subpackages/order/detail?id=${id}` })
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    rows.value = await localLifeApi.orders()
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

.order-list {
  display: grid;
  gap: 16rpx;
}

.order-card {
  background: var(--theme-surface-muted);
  border-radius: 24rpx;
  padding: 24rpx;
  border: 1rpx solid var(--theme-border);
}

.order-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 10rpx;
}

</style>
