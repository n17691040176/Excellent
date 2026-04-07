<template>
  <view class="page">
    <view class="card">
      <view class="badge">Local Life Orders</view>
      <view class="title">到店服务订单与核销进度</view>
      <view class="desc">本地生活订单支付后进入待核销状态，门店或后台核销成功后自动完成，并触发分佣结算。</view>
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

      <view v-if="filteredOrders.length">
        <view class="line-card" v-for="item in filteredOrders" :key="item.id" @click="goDetail(item.id)">
          <view class="line-title">{{ item.order_no }}</view>
          <view class="line-meta">{{ statusDesc(item) }} / 应付 {{ item.payable_amount }}</view>
          <view class="line-meta">{{ statusLabel(item) }}</view>
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

const rows = ref([])
const activeFilter = ref('ALL')

const filters = [
  { label: '全部', value: 'ALL' },
  { label: '待支付', value: 'CREATED' },
  { label: '待核销', value: 'PAID' },
  { label: '已完成', value: 'CONFIRMED' },
  { label: '已关闭', value: 'CLOSED' }
]

const filteredOrders = computed(() => (activeFilter.value === 'ALL' ? rows.value : rows.value.filter((item) => item.order_status === activeFilter.value)))

const metrics = computed(() => [
  { label: '本地生活订单', value: rows.value.length, meta: '到店服务总订单数' },
  { label: '待支付', value: rows.value.filter((item) => item.order_status === 'CREATED').length, meta: '等待用户完成支付' },
  { label: '待核销', value: rows.value.filter((item) => item.order_status === 'PAID').length, meta: '支付完成，等待门店核销' },
  { label: '已完成', value: rows.value.filter((item) => item.order_status === 'CONFIRMED').length, meta: '核销完成并进入结算' }
])

function statusLabel(item) {
  return { CREATED: '待支付', PAID: '待核销', CONFIRMED: '已完成', CLOSED: '已关闭' }[item.order_status] || item.order_status
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
  rows.value = await localLifeApi.orders()
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
</style>
