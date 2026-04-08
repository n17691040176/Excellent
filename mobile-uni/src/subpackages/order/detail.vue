<template>
  <view class="page">
    <view v-if="loadError" class="card">
      <view class="status-card">
        <view class="status-title">订单详情加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
    </view>

    <template v-else>
      <view class="card hero-card">
        <view class="hero-top">
          <view class="badge">{{ order.order_type || '订单' }}</view>
          <view class="status-pill" :class="orderStatusTone(order.order_status)">{{ orderStatusLabel(order.order_status) }}</view>
        </view>
        <view class="title">{{ order.order_no || '订单详情' }}</view>
        <view class="desc">{{ detailDesc }}</view>
        <view class="price-row">
          <view class="price-label">应付金额</view>
          <view class="price-value">¥{{ order.payable_amount || '--' }}</view>
        </view>
        <view class="info-list">
          <view class="info-row">支付状态：{{ order.pay_status || '--' }}</view>
          <view class="info-row">订单类型：{{ order.order_type || '--' }}</view>
          <view class="info-row">专区类型：{{ order.zone_type || '--' }}</view>
          <view class="info-row">创建时间：{{ formatDate(order.created_at) }}</view>
          <view class="info-row">支付时间：{{ formatDate(order.paid_at) }}</view>
          <view class="info-row">完成时间：{{ formatDate(order.confirmed_at) }}</view>
        </view>
      </view>

      <view class="card" v-if="items.length">
        <view class="section-head">
          <view class="section-title">订单商品</view>
          <view class="section-link">{{ items.length }} 项</view>
        </view>
        <view class="list-wrap">
          <view class="line-card" v-for="item in items" :key="item.id">
            <view class="line-title">{{ item.product_name }}</view>
            <view class="line-meta">数量 {{ item.quantity }} / 单价 ¥{{ item.unit_price }}</view>
            <view class="line-meta">小计 ¥{{ item.total_amount }}</view>
          </view>
        </view>
      </view>

      <view class="card" v-if="deductions.length">
        <view class="section-head">
          <view class="section-title">资产抵扣</view>
          <view class="section-link">{{ deductions.length }} 条</view>
        </view>
        <view class="list-wrap">
          <view class="line-card" v-for="item in deductions" :key="item.id">
            <view class="line-title">{{ item.asset_type }}</view>
            <view class="line-meta">
              {{ item.deduct_rate ? `抵扣比例 ${item.deduct_rate}%` : '资产抵扣' }}
            </view>
            <view class="line-meta">抵扣金额 ¥{{ item.deduct_amount }}</view>
          </view>
        </view>
      </view>

      <view class="card" v-if="isLocalLife && localLife.local_order">
        <view class="section-head">
          <view class="section-title">核销信息</view>
          <view class="section-link">本地生活</view>
        </view>
        <view class="info-list">
          <view class="info-row">核销码：{{ localLife.local_order.verification_code || '--' }}</view>
          <view class="info-row">核销时间：{{ formatDate(localLife.local_order.verified_at) }}</view>
          <view class="info-row">服务名称：{{ localLife.service?.service_name || '--' }}</view>
          <view class="info-row">联盟商家：{{ localLife.merchant?.merchant_name || '--' }}</view>
          <view class="info-row">履约门店：{{ localLife.store?.store_name || '--' }}</view>
        </view>
      </view>

      <view class="card">
        <view class="section-title">订单操作</view>
        <view class="action-list">
          <button v-if="order.order_status === 'CREATED'" class="primary-btn" @click="payDemo">{{ actionLoading === 'pay' ? '处理中...' : '演示支付' }}</button>
          <button v-if="canConfirm" class="success-btn" @click="confirmOrder">{{ actionLoading === 'confirm' ? '处理中...' : '确认完成' }}</button>
          <button v-if="order.order_status === 'CREATED'" class="danger-btn" @click="cancelOrder">{{ actionLoading === 'cancel' ? '处理中...' : '取消订单' }}</button>
          <button class="secondary-btn" @click="backToList">返回订单列表</button>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { localLifeApi, orderApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError, orderStatusLabel, orderStatusTone } from '../../utils/ui'

const orderId = ref('')
const detail = ref({})
const localLife = ref({})
const items = ref([])
const deductions = ref([])
const loadError = ref('')
const actionLoading = ref('')

const order = computed(() => detail.value.order || {})
const isLocalLife = computed(() => order.value.order_type === 'LOCAL_LIFE_ORDER')
const canConfirm = computed(() => order.value.order_status === 'PAID' && !isLocalLife.value)
const detailDesc = computed(() => {
  if (isLocalLife.value) {
    return '本地生活订单支付后展示核销码，等待门店核销完成。'
  }
  if (order.value.order_type === 'PACKAGE_ORDER') {
    return '套餐订单支付后会触发赠券、积分补贴与返现冻结逻辑。'
  }
  return '商城订单支付并确认完成后，会进入返现结算流程。'
})

function formatDate(value) {
  if (!value) {
    return '--'
  }
  return String(value).replace('T', ' ').slice(0, 16)
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

async function loadData() {
  loadError.value = ''
  try {
    detail.value = await orderApi.detail(orderId.value)
    items.value = detail.value.items || []
    deductions.value = detail.value.asset_deductions || []
    if (order.value.order_type === 'LOCAL_LIFE_ORDER') {
      localLife.value = await localLifeApi.orderDetail(orderId.value)
    } else {
      localLife.value = {}
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function payDemo() {
  if (!(await confirmAction(`确认对订单 ${order.value.order_no} 执行演示支付吗？`))) {
    return
  }
  actionLoading.value = 'pay'
  try {
    await orderApi.payDemo(orderId.value)
    uni.showToast({ title: '订单已支付', icon: 'success' })
    loadData()
  } finally {
    actionLoading.value = ''
  }
}

async function confirmOrder() {
  if (!(await confirmAction(`确认订单 ${order.value.order_no} 已完成吗？`))) {
    return
  }
  actionLoading.value = 'confirm'
  try {
    await orderApi.confirm(orderId.value)
    uni.showToast({ title: '订单已确认完成', icon: 'success' })
    loadData()
  } finally {
    actionLoading.value = ''
  }
}

async function cancelOrder() {
  if (!(await confirmAction(`确认取消订单 ${order.value.order_no} 吗？`))) {
    return
  }
  actionLoading.value = 'cancel'
  try {
    await orderApi.cancel(orderId.value)
    uni.showToast({ title: '订单已取消', icon: 'success' })
    backToList()
  } finally {
    actionLoading.value = ''
  }
}

function backToList() {
  uni.navigateTo({ url: '/pages/orders/list' })
}

onLoad((options) => {
  if (!ensureLogin()) {
    return
  }
  orderId.value = String(options?.id || '')
  if (!orderId.value) {
    uni.showToast({ title: '缺少订单编号', icon: 'none' })
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

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.price-row {
  background: var(--theme-dark-panel);
  border-radius: 24rpx;
  padding: 24rpx;
  margin: 18rpx 0 20rpx;
  color: #ffffff;
  box-shadow: 0 16rpx 32rpx rgba(111, 84, 58, 0.14);
}

.price-label {
  font-size: 22rpx;
  opacity: 0.72;
  margin-bottom: 10rpx;
}

.price-value {
  font-size: 50rpx;
  font-weight: 700;
  line-height: 1.1;
}

.list-wrap,
.retry-btn {
  margin-top: 8rpx;
}

.action-list {
  display: grid;
  gap: 16rpx;
}

</style>
