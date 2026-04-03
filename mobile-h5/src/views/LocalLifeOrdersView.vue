<template>
  <div class="page safe-bottom">
    <van-nav-bar title="本地生活订单" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-card">
      <div class="hero-badge">Local Life Orders</div>
      <h2 class="page-title">到店服务订单与核销进度</h2>
      <p class="page-desc">本地生活订单支付后进入待核销状态，门店或后台核销成功后自动完成，并触发分佣结算。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="filter-row">
        <van-button
          v-for="item in filters"
          :key="item.value"
          size="small"
          :type="activeFilter === item.value ? 'primary' : 'default'"
          plain
          @click="activeFilter = item.value"
        >{{ item.label }}</van-button>
      </div>

      <van-cell-group inset>
        <van-cell
          v-for="item in filteredOrders"
          :key="item.id"
          is-link
          @click="goDetail(item.id)"
          :title="item.order_no"
          :label="`${statusDesc(item)} / 应付 ${item.payable_amount}`"
        >
          <template #value>
            <div>{{ item.order_status }}</div>
            <div :class="['status-pill', statusClass(item)]">{{ statusLabel(item) }}</div>
          </template>
        </van-cell>
      </van-cell-group>
      <van-empty v-if="!filteredOrders.length" image="search" description="当前状态下暂无本地生活订单" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { localLifeApi } from '@/api/modules'

const router = useRouter()
const rows = ref([])
const activeFilter = ref('ALL')

const filters = [
  { label: '全部', value: 'ALL' },
  { label: '待支付', value: 'CREATED' },
  { label: '待核销', value: 'PAID' },
  { label: '已完成', value: 'CONFIRMED' },
  { label: '已关闭', value: 'CLOSED' }
]

const filteredOrders = computed(() => {
  if (activeFilter.value === 'ALL') return rows.value
  return rows.value.filter((item) => item.order_status === activeFilter.value)
})

const metrics = computed(() => [
  { label: '本地生活订单', value: rows.value.length, meta: '到店服务总订单数' },
  { label: '待支付', value: rows.value.filter((item) => item.order_status === 'CREATED').length, meta: '等待用户完成支付' },
  { label: '待核销', value: rows.value.filter((item) => item.order_status === 'PAID').length, meta: '支付完成，等待门店核销' },
  { label: '已完成', value: rows.value.filter((item) => item.order_status === 'CONFIRMED').length, meta: '核销完成并进入结算' }
])

function statusLabel(item) {
  return {
    CREATED: '待支付',
    PAID: '待核销',
    CONFIRMED: '已完成',
    CLOSED: '已关闭'
  }[item.order_status] || item.order_status
}

function statusClass(item) {
  return {
    CREATED: 'status-warning',
    PAID: 'status-primary',
    CONFIRMED: 'status-success',
    CLOSED: 'status-muted'
  }[item.order_status] || 'status-muted'
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
  router.push(`/orders/${id}`)
}

async function loadData() {
  rows.value = await localLifeApi.orders()
}

onMounted(loadData)
</script>
