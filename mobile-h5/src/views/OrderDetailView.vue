<template>
  <div class="page safe-bottom">
    <van-nav-bar title="订单详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <div class="soft-chip">{{ order.order_type || '订单' }}</div>
      <h2 class="page-title">{{ order.order_no || '订单详情' }}</h2>
      <p class="page-desc">{{ detailDesc }}</p>
      <div class="price-row">
        <div class="price-main">{{ order.payable_amount || '--' }}</div>
        <div class="price-sub">应付金额</div>
      </div>
      <van-cell-group inset>
        <van-cell title="订单状态" :value="order.order_status || '--'" />
        <van-cell title="支付状态" :value="order.pay_status || '--'" />
        <van-cell title="订单类型" :value="order.order_type || '--'" />
        <van-cell title="专区类型" :value="order.zone_type || '--'" />
        <van-cell title="创建时间" :value="formatDate(order.created_at)" />
        <van-cell title="支付时间" :value="formatDate(order.paid_at)" />
        <van-cell title="完成时间" :value="formatDate(order.confirmed_at)" />
      </van-cell-group>
    </div>

    <div class="page-card" v-if="items.length">
      <h3 class="cell-group-title">订单商品</h3>
      <van-cell-group inset>
        <van-cell v-for="item in items" :key="item.id" :title="item.product_name" :label="`数量 ${item.quantity} / 单价 ${item.unit_price}`">
          <template #value>{{ item.total_amount }}</template>
        </van-cell>
      </van-cell-group>
    </div>

    <div class="page-card" v-if="deductions.length">
      <h3 class="cell-group-title">资产抵扣</h3>
      <van-cell-group inset>
        <van-cell v-for="item in deductions" :key="item.id" :title="item.asset_type" :label="item.deduct_rate ? `抵扣比例 ${item.deduct_rate}%` : '资产抵扣'">
          <template #value>{{ item.deduct_amount }}</template>
        </van-cell>
      </van-cell-group>
    </div>

    <div class="page-card" v-if="isLocalLife && localLife.local_order">
      <h3 class="cell-group-title">核销信息</h3>
      <van-cell-group inset>
        <van-cell title="核销码" :value="localLife.local_order.verification_code || '--'" />
        <van-cell title="核销时间" :value="formatDate(localLife.local_order.verified_at)" />
        <van-cell title="服务名称" :value="localLife.service?.service_name || '--'" />
        <van-cell title="联盟商家" :value="localLife.merchant?.merchant_name || '--'" />
        <van-cell title="履约门店" :value="localLife.store?.store_name || '--'" />
      </van-cell-group>
      <p class="page-desc" style="margin-top: 0.18rem;">本地生活订单需由门店或后台核销，核销成功后会自动进入已完成状态并结算分佣。</p>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">订单操作</h3>
      <div class="inline-actions" style="display: grid; grid-template-columns: 1fr 1fr;">
        <van-button round type="primary" @click="payDemo" v-if="order.order_status === 'CREATED'">演示支付</van-button>
        <van-button round plain type="success" @click="confirmOrder" v-if="canConfirm">确认完成</van-button>
        <van-button round plain type="danger" @click="cancelOrder" v-if="order.order_status === 'CREATED'">取消订单</van-button>
        <van-button round plain type="primary" :to="backRoute">返回订单列表</van-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast } from 'vant'

import { localLifeApi, orderApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const localLife = ref({})
const items = ref([])
const deductions = ref([])

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
  detail.value = await orderApi.detail(route.params.id)
  items.value = detail.value.items || []
  deductions.value = detail.value.asset_deductions || []
  if (order.value.order_type === 'LOCAL_LIFE_ORDER') {
    localLife.value = await localLifeApi.orderDetail(route.params.id)
  } else {
    localLife.value = {}
  }
}

async function payDemo() {
  await showConfirmDialog({ title: '提示', message: `确认对订单 ${order.value.order_no} 执行演示支付吗？` })
  await orderApi.payDemo(route.params.id)
  showSuccessToast('订单已支付')
  await loadData()
}

async function confirmOrder() {
  await showConfirmDialog({ title: '提示', message: `确认订单 ${order.value.order_no} 已完成吗？` })
  await orderApi.confirm(route.params.id)
  showSuccessToast('订单已确认完成')
  await loadData()
}

async function cancelOrder() {
  await showConfirmDialog({ title: '提示', message: `确认取消订单 ${order.value.order_no} 吗？` })
  await orderApi.cancel(route.params.id)
  showSuccessToast('订单已取消')
  router.replace('/orders')
}

onMounted(loadData)
</script>
