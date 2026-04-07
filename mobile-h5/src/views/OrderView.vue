<template>
  <div class="page safe-bottom">
    <van-nav-bar title="我的订单" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-soft">
      <div class="hero-badge">Order Center</div>
      <h2 class="page-title">把不同业务订单收进一套统一的跟进视图</h2>
      <p class="page-desc">按状态而不是业务类型组织订单，优先突出支付、完成和关闭动作。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
      <van-tabs v-model:active="activeStatus" style="margin-top: 0.22rem;">
        <van-tab title="全部" name="all" />
        <van-tab title="待支付" name="CREATED" />
        <van-tab title="待完成" name="PAID" />
        <van-tab title="已完成" name="CONFIRMED" />
        <van-tab title="已关闭" name="CLOSED" />
      </van-tabs>
    </div>

    <div class="page-card">
      <div v-if="loadError" class="state-card">
        <div class="state-title">订单加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
      <div v-else-if="loading" class="card-stack">
        <div class="skeleton-card"></div>
        <div class="skeleton-card short"></div>
      </div>
      <div v-else-if="filteredRows.length" class="card-stack">
        <div class="soft-section" v-for="item in filteredRows" :key="item.id" @click="goDetail(item.id)">
          <div class="top-row">
            <div class="product-name">{{ item.order_no }}</div>
            <div class="status-capsule" :class="orderStatusClass(item.order_status)">{{ orderStatusLabel(item.order_status) }}</div>
          </div>
          <div class="product-meta">业务 {{ item.order_type }} / 分区 {{ item.zone_type || '--' }}</div>
          <div class="product-meta">应付金额 ¥{{ item.payable_amount }}</div>
          <div class="inline-actions" style="margin-top: 0.14rem; flex-wrap: wrap;">
            <van-button size="small" plain type="primary" @click.stop="payDemo(item)" v-if="item.order_status === 'CREATED'">演示支付</van-button>
            <van-button size="small" plain type="success" @click.stop="confirmOrder(item)" v-if="canConfirm(item)">确认完成</van-button>
            <van-button size="small" plain type="danger" @click.stop="cancelOrder(item)" v-if="item.order_status === 'CREATED'">取消订单</van-button>
          </div>
        </div>
      </div>
      <van-empty v-else image="search" description="暂无订单记录" />
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { orderApi } from '@/api/modules'
import { normalizeLoadError, orderStatusClass, orderStatusLabel } from '@/utils/ui'

const router = useRouter()
const rows = ref([])
const activeStatus = ref('all')
const loading = ref(false)
const loadError = ref('')

const filteredRows = computed(() => {
  if (activeStatus.value === 'all') return rows.value
  return rows.value.filter((item) => item.order_status === activeStatus.value)
})

const metrics = computed(() => [
  { label: '全部订单', value: rows.value.length, meta: '统一查看平台交易进度' },
  { label: '待支付', value: rows.value.filter((item) => item.order_status === 'CREATED').length, meta: '可继续支付或取消' },
  { label: '待完成', value: rows.value.filter((item) => item.order_status === 'PAID').length, meta: '等待确认或核销完成' },
  { label: '已完成', value: rows.value.filter((item) => item.order_status === 'CONFIRMED').length, meta: '可驱动返现结算' }
])

function canConfirm(item) {
  return item.order_status === 'PAID' && item.order_type !== 'LOCAL_LIFE_ORDER'
}

function goDetail(id) {
  router.push(`/orders/${id}`)
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
  await showConfirmDialog({ title: '提示', message: `确认对订单 ${item.order_no} 执行演示支付吗？` })
  await orderApi.payDemo(item.id)
  showSuccessToast('订单已进入已支付状态')
  await loadData()
}

async function confirmOrder(item) {
  await showConfirmDialog({ title: '提示', message: `确认订单 ${item.order_no} 已完成吗？` })
  await orderApi.confirm(item.id)
  showSuccessToast('订单已确认完成')
  await loadData()
}

async function cancelOrder(item) {
  await showConfirmDialog({ title: '提示', message: `确认取消订单 ${item.order_no} 吗？` })
  await orderApi.cancel(item.id)
  showSuccessToast('订单已取消')
  await loadData()
}

onMounted(loadData)
</script>
