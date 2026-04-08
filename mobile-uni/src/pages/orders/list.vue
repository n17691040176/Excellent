<template>
  <view class="page orders-page">
    <view class="card hero-card">
      <view class="badge">Order Center</view>
      <view class="title">把不同业务订单收进一套统一的跟进视图</view>
      <view class="desc">
        当前页面按状态而不是业务类型来组织订单，优先突出支付、完成和关闭动作，减少用户在套餐、商城和本地生活之间来回理解。
      </view>
      <view class="metric-grid">
        <view class="metric-card" v-for="item in summaryMetrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>

      <scroll-view scroll-x class="tab-row">
        <view
          class="status-tab"
          :class="{ active: activeStatus === item.value }"
          v-for="item in statusTabs"
          :key="item.value"
          @click="activeStatus = item.value"
        >
          {{ item.label }}
        </view>
      </scroll-view>
    </view>

    <view class="card">
      <view v-if="loadError" class="status-card">
        <view class="status-title">订单加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else-if="loading">
        <view class="skeleton-block"></view>
        <view class="skeleton-block short"></view>
      </view>
      <view v-else-if="filteredRows.length" class="order-list">
        <view class="order-card tap-item" v-for="item in filteredRows" :key="item.id" @click="goDetail(item.id)">
          <view class="order-top">
            <view class="order-no">{{ item.order_no }}</view>
            <view class="order-status status-pill" :class="orderStatusTone(item.order_status)">{{ orderStatusLabel(item.order_status) }}</view>
          </view>
          <view class="order-meta">业务 {{ item.order_type }} / 分区 {{ item.zone_type || '--' }}</view>
          <view class="order-meta">应付金额 ¥{{ item.payable_amount }}</view>
          <view class="actions">
            <button v-if="item.order_status === 'CREATED'" class="minor-btn" @click.stop="payDemo(item)">演示支付</button>
            <button v-if="canConfirm(item)" class="success-btn" @click.stop="confirmOrder(item)">确认完成</button>
            <button v-if="item.order_status === 'CREATED'" class="danger-btn" @click.stop="cancelOrder(item)">取消订单</button>
          </view>
        </view>
      </view>
      <view v-else class="empty-text">暂无订单记录</view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { orderApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError, orderStatusLabel, orderStatusTone } from '../../utils/ui'

const rows = ref([])
const activeStatus = ref('all')
const loading = ref(false)
const loadError = ref('')

const statusTabs = [
  { label: '全部', value: 'all' },
  { label: '待支付', value: 'CREATED' },
  { label: '待完成', value: 'PAID' },
  { label: '已完成', value: 'CONFIRMED' },
  { label: '已关闭', value: 'CLOSED' }
]

const filteredRows = computed(() => {
  if (activeStatus.value === 'all') {
    return rows.value
  }
  return rows.value.filter((item) => item.order_status === activeStatus.value)
})

const summaryMetrics = computed(() => [
  { label: '全部订单', value: rows.value.length, meta: '统一查看平台交易进度' },
  { label: '待支付', value: rows.value.filter((item) => item.order_status === 'CREATED').length, meta: '可继续支付或取消' },
  { label: '待完成', value: rows.value.filter((item) => item.order_status === 'PAID').length, meta: '等待确认或核销完成' },
  { label: '已完成', value: rows.value.filter((item) => item.order_status === 'CONFIRMED').length, meta: '可驱动返现结算' }
])

function canConfirm(item) {
  return item.order_status === 'PAID' && item.order_type !== 'LOCAL_LIFE_ORDER'
}

function confirmAction(content) {
  return new Promise((resolve) => {
    uni.showModal({
      title: '提示',
      content,
      success(result) {
        resolve(result.confirm)
      }
    })
  })
}

function goDetail(id) {
  uni.navigateTo({ url: `/subpackages/order/detail?id=${id}` })
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    rows.value = await orderApi.list()
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

async function payDemo(item) {
  if (!(await confirmAction(`确认对订单 ${item.order_no} 执行演示支付吗？`))) {
    return
  }
  await orderApi.payDemo(item.id)
  uni.showToast({ title: '订单已进入已支付状态', icon: 'success' })
  loadData()
}

async function confirmOrder(item) {
  if (!(await confirmAction(`确认订单 ${item.order_no} 已完成吗？`))) {
    return
  }
  await orderApi.confirm(item.id)
  uni.showToast({ title: '订单已确认完成', icon: 'success' })
  loadData()
}

async function cancelOrder(item) {
  if (!(await confirmAction(`确认取消订单 ${item.order_no} 吗？`))) {
    return
  }
  await orderApi.cancel(item.id)
  uni.showToast({ title: '订单已取消', icon: 'success' })
  loadData()
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

.tab-row {
  white-space: nowrap;
  margin-top: 24rpx;
}

.status-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 64rpx;
  padding: 0 28rpx;
  border-radius: 999rpx;
  background: #f5efe7;
  color: var(--theme-text-muted);
  font-size: 24rpx;
  margin-right: 16rpx;
}

.status-tab.active {
  background: linear-gradient(180deg, #d7793e 0%, #c96a32 100%);
  color: #ffffff;
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

.order-no {
  font-size: 29rpx;
  font-weight: 700;
  color: var(--theme-text);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 16rpx;
}

.minor-btn,
.success-btn,
.danger-btn {
  margin: 0;
  min-width: 160rpx;
  height: 64rpx;
  line-height: 64rpx;
  border-radius: 999rpx;
  font-size: 24rpx;
}

.order-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>
