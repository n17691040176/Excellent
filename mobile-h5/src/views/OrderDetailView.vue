<template>
  <div class="page safe-bottom">
    <van-nav-bar title="订单详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div v-if="loadError" class="page-card">
      <div class="state-card">
        <div class="state-title">订单详情加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
    </div>

    <template v-else>
      <div class="page-card hero-soft">
        <div class="top-row">
          <div class="hero-badge">{{ order.order_type || '订单' }}</div>
          <div class="status-capsule" :class="orderStatusClass(order.order_status)">{{ orderStatusLabel(order.order_status) }}</div>
        </div>
        <h2 class="page-title" style="margin-top: 0.12rem;">{{ order.order_no || '订单详情' }}</h2>
        <p class="page-desc">{{ detailDesc }}</p>
        <div class="price-panel">
          <div class="price-panel-label">应付金额</div>
          <div class="price-panel-value">¥{{ order.payable_amount || '--' }}</div>
        </div>
        <div class="soft-section">
          <div class="product-meta">支付状态 {{ order.pay_status || '--' }}</div>
          <div class="product-meta">订单类型 {{ order.order_type || '--' }}</div>
          <div class="product-meta">专区类型 {{ order.zone_type || '--' }}</div>
          <div class="product-meta">创建时间 {{ formatDate(order.created_at) }}</div>
          <div class="product-meta">支付时间 {{ formatDate(order.paid_at) }}</div>
          <div class="product-meta">完成时间 {{ formatDate(order.confirmed_at) }}</div>
        </div>
      </div>

      <div class="page-card" v-if="items.length">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">订单商品</h3>
          <span class="section-link-text">{{ items.length }} 项</span>
        </div>
        <div class="card-stack">
          <div class="soft-section" v-for="item in items" :key="item.id">
            <div class="product-name">{{ item.product_name }}</div>
            <div class="product-meta">数量 {{ item.quantity }} / 单价 ¥{{ item.unit_price }}</div>
            <div class="product-meta">小计 ¥{{ item.total_amount }}</div>
          </div>
        </div>
      </div>

      <div class="page-card" v-if="deductions.length">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">资产抵扣</h3>
          <span class="section-link-text">{{ deductions.length }} 条</span>
        </div>
        <div class="card-stack">
          <div class="soft-section" v-for="item in deductions" :key="item.id">
            <div class="product-name">{{ item.asset_type }}</div>
            <div class="product-meta">{{ item.deduct_rate ? `抵扣比例 ${item.deduct_rate}%` : '资产抵扣' }}</div>
            <div class="product-meta">抵扣金额 ¥{{ item.deduct_amount }}</div>
          </div>
        </div>
      </div>

      <div class="page-card" v-if="isLocalLife && localLife.local_order">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">核销信息</h3>
          <span class="section-link-text">本地生活</span>
        </div>
        <div class="soft-section">
          <div class="product-meta">核销码 {{ localLife.local_order.verification_code || '--' }}</div>
          <div class="product-meta">核销时间 {{ formatDate(localLife.local_order.verified_at) }}</div>
          <div class="product-meta">服务名称 {{ localLife.service?.service_name || '--' }}</div>
          <div class="product-meta">联盟商家 {{ localLife.merchant?.merchant_name || '--' }}</div>
          <div class="product-meta">履约门店 {{ localLife.store?.store_name || '--' }}</div>
        </div>
      </div>

      <div class="page-card">
        <h3 class="cell-group-title">订单操作</h3>
        <div class="card-stack">
          <van-button round type="primary" @click="payDemo" v-if="order.order_status === 'CREATED'">{{ actionLoading === 'pay' ? '处理中...' : '演示支付' }}</van-button>
          <van-button round plain type="success" @click="confirmOrder" v-if="canConfirm">{{ actionLoading === 'confirm' ? '处理中...' : '确认完成' }}</van-button>
          <van-button round plain type="danger" @click="cancelOrder" v-if="order.order_status === 'CREATED'">{{ actionLoading === 'cancel' ? '处理中...' : '取消订单' }}</van-button>
          <van-button round plain type="primary" :to="backRoute">返回订单列表</van-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast } from 'vant'

import { localLifeApi, orderApi } from '@/api/modules'
import { normalizeLoadError, orderStatusClass, orderStatusLabel } from '@/utils/ui'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const localLife = ref({})
const items = ref([])
const deductions = ref([])
const loadError = ref('')
const actionLoading = ref('')

const order = computed(() => detail.value.order || {})
const isLocalLife = computed(() => order.value.order_type === 'LOCAL_LIFE_ORDER')
const canConfirm = computed(() => order.value.order_status === 'PAID' && !isLocalLife.value)
const backRoute = computed(() => (isLocalLife.value ? '/life/orders' : '/orders'))
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
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

async function loadData() {
  loadError.value = ''
  try {
    detail.value = await orderApi.detail(route.params.id)
    items.value = detail.value.items || []
    deductions.value = detail.value.asset_deductions || []
    if (order.value.order_type === 'LOCAL_LIFE_ORDER') {
      localLife.value = await localLifeApi.orderDetail(route.params.id)
    } else {
      localLife.value = {}
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function payDemo() {
  await showConfirmDialog({ title: '提示', message: `确认对订单 ${order.value.order_no} 执行演示支付吗？` })
  actionLoading.value = 'pay'
  try {
    await orderApi.payDemo(route.params.id)
    showSuccessToast('订单已支付')
    await loadData()
  } finally {
    actionLoading.value = ''
  }
}

async function confirmOrder() {
  await showConfirmDialog({ title: '提示', message: `确认订单 ${order.value.order_no} 已完成吗？` })
  actionLoading.value = 'confirm'
  try {
    await orderApi.confirm(route.params.id)
    showSuccessToast('订单已确认完成')
    await loadData()
  } finally {
    actionLoading.value = ''
  }
}

async function cancelOrder() {
  await showConfirmDialog({ title: '提示', message: `确认取消订单 ${order.value.order_no} 吗？` })
  actionLoading.value = 'cancel'
  try {
    await orderApi.cancel(route.params.id)
    showSuccessToast('订单已取消')
    router.replace('/orders')
  } finally {
    actionLoading.value = ''
  }
}

onMounted(loadData)
</script>
