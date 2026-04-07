<template>
  <view class="page">
    <view class="card">
      <view class="tag">{{ order.order_type || '订单' }}</view>
      <view class="title">{{ order.order_no || '订单详情' }}</view>
      <view class="desc">{{ detailDesc }}</view>
      <view class="price">应付金额 {{ order.payable_amount || '--' }}</view>
      <view class="info-list">
        <view class="info-row">订单状态：{{ order.order_status || '--' }}</view>
        <view class="info-row">支付状态：{{ order.pay_status || '--' }}</view>
        <view class="info-row">订单类型：{{ order.order_type || '--' }}</view>
        <view class="info-row">专区类型：{{ order.zone_type || '--' }}</view>
        <view class="info-row">创建时间：{{ formatDate(order.created_at) }}</view>
        <view class="info-row">支付时间：{{ formatDate(order.paid_at) }}</view>
        <view class="info-row">完成时间：{{ formatDate(order.confirmed_at) }}</view>
      </view>
    </view>

    <view class="card" v-if="items.length">
      <view class="section-title">订单商品</view>
      <view class="line-card" v-for="item in items" :key="item.id">
        <view class="line-title">{{ item.product_name }}</view>
        <view class="line-meta">数量 {{ item.quantity }} / 单价 {{ item.unit_price }}</view>
        <view class="line-meta">小计 {{ item.total_amount }}</view>
      </view>
    </view>

    <view class="card" v-if="deductions.length">
      <view class="section-title">资产抵扣</view>
      <view class="line-card" v-for="item in deductions" :key="item.id">
        <view class="line-title">{{ item.asset_type }}</view>
        <view class="line-meta">
          {{ item.deduct_rate ? `抵扣比例 ${item.deduct_rate}%` : '资产抵扣' }}
        </view>
        <view class="line-meta">抵扣金额 {{ item.deduct_amount }}</view>
      </view>
    </view>

    <view class="card" v-if="isLocalLife && localLife.local_order">
      <view class="section-title">核销信息</view>
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
        <button v-if="order.order_status === 'CREATED'" class="primary-btn" @click="payDemo">演示支付</button>
        <button v-if="canConfirm" class="success-btn" @click="confirmOrder">确认完成</button>
        <button v-if="order.order_status === 'CREATED'" class="danger-btn" @click="cancelOrder">取消订单</button>
        <button class="secondary-btn" @click="backToList">返回订单列表</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { localLifeApi, orderApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const orderId = ref('')
const detail = ref({})
const localLife = ref({})
const items = ref([])
const deductions = ref([])

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
  detail.value = await orderApi.detail(orderId.value)
  items.value = detail.value.items || []
  deductions.value = detail.value.asset_deductions || []
  if (order.value.order_type === 'LOCAL_LIFE_ORDER') {
    localLife.value = await localLifeApi.orderDetail(orderId.value)
  } else {
    localLife.value = {}
  }
}

async function payDemo() {
  if (!(await confirmAction(`确认对订单 ${order.value.order_no} 执行演示支付吗？`))) {
    return
  }
  await orderApi.payDemo(orderId.value)
  uni.showToast({ title: '订单已支付', icon: 'success' })
  loadData()
}

async function confirmOrder() {
  if (!(await confirmAction(`确认订单 ${order.value.order_no} 已完成吗？`))) {
    return
  }
  await orderApi.confirm(orderId.value)
  uni.showToast({ title: '订单已确认完成', icon: 'success' })
  loadData()
}

async function cancelOrder() {
  if (!(await confirmAction(`确认取消订单 ${order.value.order_no} 吗？`))) {
    return
  }
  await orderApi.cancel(orderId.value)
  uni.showToast({ title: '订单已取消', icon: 'success' })
  backToList()
}

function backToList() {
  uni.switchTab({ url: '/pages/orders/list' })
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
.page { min-height: 100vh; padding: 32rpx; }
.card { background: #ffffff; border-radius: 24rpx; padding: 32rpx; margin-bottom: 24rpx; }
.tag {
  display: inline-flex;
  align-items: center;
  height: 48rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #0d6efd;
  font-size: 24rpx;
  margin-bottom: 16rpx;
}
.title { font-size: 40rpx; font-weight: 600; margin-bottom: 16rpx; }
.desc { font-size: 28rpx; color: #6b7280; line-height: 1.6; margin-bottom: 20rpx; }
.price { font-size: 34rpx; font-weight: 700; color: #0d6efd; margin-bottom: 20rpx; }
.section-title { font-size: 34rpx; font-weight: 600; margin-bottom: 20rpx; }
.info-list { display: grid; gap: 12rpx; }
.info-row, .line-meta { font-size: 26rpx; color: #4b5563; line-height: 1.6; }
.line-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}
.line-title { font-size: 30rpx; font-weight: 600; margin-bottom: 8rpx; }
.action-list { display: grid; gap: 16rpx; }
.primary-btn,
.success-btn,
.danger-btn,
.secondary-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  font-size: 30rpx;
}
.primary-btn { background: #0d6efd; color: #ffffff; }
.success-btn { background: #ecfdf3; color: #16a34a; }
.danger-btn { background: #fef2f2; color: #dc2626; }
.secondary-btn { background: #f3f4f6; color: #374151; }
</style>
