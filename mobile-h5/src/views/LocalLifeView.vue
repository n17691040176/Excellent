<template>
  <div class="page safe-bottom">
    <van-nav-bar title="本地生活" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">联盟商家与到店服务</h2>
      <p class="page-desc">本地生活专区对接百业联盟商家，服务可按规则产生区县代理、市代理、个人与商家分佣，并带动设备与广告收益。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="section-head">
        <div>
          <h3 class="cell-group-title">快捷入口</h3>
          <p class="page-desc" style="margin-bottom: 0;">可直接查看本地生活订单进度，支付后进入待核销状态。</p>
        </div>
        <van-button size="small" round type="primary" to="/life/orders">查看订单</van-button>
      </div>
      <div class="tiny-grid" style="margin-top: 0.24rem;">
        <div class="tiny-panel">
          <div class="tiny-panel-title">待支付</div>
          <div class="tiny-panel-value">{{ orderSummary.created }}</div>
          <div class="tiny-panel-meta">尚未完成支付</div>
        </div>
        <div class="tiny-panel">
          <div class="tiny-panel-title">待核销</div>
          <div class="tiny-panel-value">{{ orderSummary.paid }}</div>
          <div class="tiny-panel-meta">等待门店核销</div>
        </div>
        <div class="tiny-panel">
          <div class="tiny-panel-title">已完成</div>
          <div class="tiny-panel-value">{{ orderSummary.confirmed }}</div>
          <div class="tiny-panel-meta">核销完成并已结算</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <van-tabs v-model:active="activeTab">
        <van-tab title="服务列表">
          <div v-if="services.length">
            <div class="product-item" v-for="item in services" :key="item.id" @click="goService(item.id)">
              <div class="product-name">{{ item.service_name }}</div>
              <div class="product-meta">售价 {{ item.sale_price }} / 门市价 {{ item.market_price || '--' }}</div>
              <div class="product-meta">商家 {{ item.merchant_id }} / 核销方式 {{ item.verification_type }}</div>
            </div>
          </div>
          <van-empty v-else image="search" description="暂无本地生活服务" />
        </van-tab>

        <van-tab title="联盟商家">
          <van-cell-group inset>
            <van-cell v-for="item in merchants" :key="item.id" :title="item.merchant_name" :label="`${item.category_name} / ${item.contact_phone}`">
              <template #value>
                <div>{{ item.status }}</div>
                <div style="margin-top: 0.12rem;">
                  <van-button size="mini" plain type="primary" @click="filterByMerchant(item.id)">查看服务</van-button>
                </div>
              </template>
            </van-cell>
          </van-cell-group>
          <van-empty v-if="!merchants.length" image="search" description="暂无联盟商家" />
        </van-tab>

        <van-tab title="最近订单">
          <van-cell-group inset>
            <van-cell
              v-for="item in recentOrders"
              :key="item.id"
              is-link
              @click="goOrder(item.id)"
              :title="item.order_no"
              :label="`应付 ${item.payable_amount} / ${orderLabel(item.order_status)}`"
            >
              <template #value>
                <div :class="['status-pill', orderClass(item.order_status)]">{{ orderLabel(item.order_status) }}</div>
              </template>
            </van-cell>
          </van-cell-group>
          <van-empty v-if="!recentOrders.length" image="search" description="暂无本地生活订单" />
        </van-tab>
      </van-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { localLifeApi } from '@/api/modules'

const router = useRouter()
const activeTab = ref(0)
const merchants = ref([])
const services = ref([])
const revenue = ref({})
const orders = ref([])

const metrics = computed(() => [
  { label: '联盟商家', value: merchants.value.length, meta: '本地生活接入商家总数' },
  { label: '服务数量', value: services.value.length, meta: '可下单到店服务总数' },
  { label: '设备收益', value: Number(revenue.value.device_revenue_total || 0).toFixed(2), meta: '快充宝、设备流水等' },
  { label: '广告收益', value: Number(revenue.value.ad_revenue_total || 0).toFixed(2), meta: '门店广告与推广位收益' }
])

const orderSummary = computed(() => ({
  created: orders.value.filter((item) => item.order_status === 'CREATED').length,
  paid: orders.value.filter((item) => item.order_status === 'PAID').length,
  confirmed: orders.value.filter((item) => item.order_status === 'CONFIRMED').length
}))

const recentOrders = computed(() => orders.value.slice(0, 5))

function orderLabel(status) {
  return {
    CREATED: '待支付',
    PAID: '待核销',
    CONFIRMED: '已完成',
    CLOSED: '已关闭'
  }[status] || status
}

function orderClass(status) {
  return {
    CREATED: 'status-warning',
    PAID: 'status-primary',
    CONFIRMED: 'status-success',
    CLOSED: 'status-muted'
  }[status] || 'status-muted'
}

function goService(id) {
  router.push(`/life/services/${id}`)
}

function goOrder(id) {
  router.push(`/orders/${id}`)
}

async function filterByMerchant(merchantId) {
  services.value = await localLifeApi.services(merchantId)
  activeTab.value = 0
}

async function loadData() {
  const [merchantRows, serviceRows, revenueData, orderRows] = await Promise.all([
    localLifeApi.merchants(),
    localLifeApi.services(),
    localLifeApi.revenueSummary(),
    localLifeApi.orders()
  ])
  merchants.value = merchantRows || []
  services.value = serviceRows || []
  revenue.value = revenueData || {}
  orders.value = orderRows || []
}

onMounted(loadData)
</script>
