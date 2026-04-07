<template>
  <view class="page">
    <view class="card">
      <view class="title">订单列表</view>
      <view class="desc">
        展示套餐、商城和本地生活订单；支付后进入待确认或待核销状态，完成后驱动返现结算。
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
      <view v-if="filteredRows.length">
        <view class="order-card" v-for="item in filteredRows" :key="item.id" @click="goDetail(item.id)">
          <view class="order-top">
            <view class="order-no">{{ item.order_no }}</view>
            <view class="order-status">{{ item.order_status }}</view>
          </view>
          <view class="order-meta">{{ item.order_type }} / {{ item.zone_type || '--' }}</view>
          <view class="order-meta">应付金额 {{ item.payable_amount }}</view>
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

const rows = ref([])
const activeStatus = ref('all')

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
  rows.value = await orderApi.list()
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
  background: #f3f4f6;
  color: #6b7280;
  font-size: 24rpx;
  margin-right: 16rpx;
}

.status-tab.active {
  background: #0d6efd;
  color: #ffffff;
}

.order-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}

.order-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 10rpx;
}

.order-no {
  font-size: 28rpx;
  font-weight: 600;
  color: #111827;
}

.order-status,
.order-meta,
.empty-text {
  font-size: 24rpx;
  color: #6b7280;
  line-height: 1.6;
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

.minor-btn {
  background: #eef4ff;
  color: #0d6efd;
}

.success-btn {
  background: #ecfdf3;
  color: #16a34a;
}

.danger-btn {
  background: #fef2f2;
  color: #dc2626;
}
</style>
