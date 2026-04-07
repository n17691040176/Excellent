<template>
  <div class="page safe-bottom">
    <van-nav-bar title="本地生活" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-soft">
      <div class="hero-badge">Local Life</div>
      <h2 class="page-title">把联盟商家、服务供给和核销订单放进同一块看板</h2>
      <p class="page-desc">本地生活围绕到店服务展开，先判断商家规模和服务供给，再快速跟进支付、核销和完成状态。</p>
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
          <h3 class="cell-group-title">核销进度</h3>
          <p class="page-desc" style="margin-bottom: 0;">支付后进入待核销状态，门店核销完成后再进入结算。</p>
        </div>
        <span class="section-link-text" @click="router.push('/life/orders')">查看订单</span>
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
          <div v-if="loadError" class="state-card">
            <div class="state-title">本地生活数据加载失败</div>
            <div class="state-desc">{{ loadError }}</div>
            <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
          </div>
          <div v-else-if="loading" class="card-stack">
            <div class="skeleton-card"></div>
            <div class="skeleton-card short"></div>
          </div>
          <div v-else-if="services.length" class="card-stack">
            <div class="soft-section" v-for="item in services" :key="item.id" @click="goService(item.id)">
              <div class="top-row">
                <div>
                  <div class="product-name">{{ item.service_name }}</div>
                  <div class="product-meta">门市价 ¥{{ item.market_price || '--' }} / 商家 {{ item.merchant_id }}</div>
                </div>
                <div class="price-main">¥{{ item.sale_price }}</div>
              </div>
              <div class="chip-list" style="margin-bottom: 0.14rem;">
                <div class="chip">{{ item.verification_type || '待定核销' }}</div>
                <div class="chip">{{ item.service_type || '到店服务' }}</div>
              </div>
              <div class="product-meta">点击进入详情页，可直接下单并指定门店。</div>
            </div>
          </div>
          <van-empty v-else image="search" description="暂无本地生活服务" />
        </van-tab>

        <van-tab title="联盟商家">
          <div v-if="merchants.length" class="card-stack">
            <div class="soft-section" v-for="item in merchants" :key="item.id">
              <div class="product-name">{{ item.merchant_name }}</div>
              <div class="product-meta">{{ item.category_name || '未分类' }} / {{ item.contact_phone || '--' }}</div>
              <div class="product-meta">状态 {{ item.status || '--' }}</div>
              <van-button size="small" plain type="primary" style="margin-top: 0.16rem;" @click="filterByMerchant(item.id, item.merchant_name)">查看服务</van-button>
            </div>
          </div>
          <van-empty v-else image="search" description="暂无联盟商家" />
        </van-tab>

        <van-tab title="最近订单">
          <div v-if="recentOrders.length" class="card-stack">
            <div class="soft-section" v-for="item in recentOrders" :key="item.id" @click="goOrder(item.id)">
              <div class="top-row">
                <div class="product-name">{{ item.order_no }}</div>
                <div class="status-capsule" :class="orderStatusClass(item.order_status)">{{ orderLabel(item.order_status) }}</div>
              </div>
              <div class="product-meta">应付金额 ¥{{ item.payable_amount }}</div>
              <div class="product-meta">点击查看详情和后续核销进度。</div>
            </div>
          </div>
          <van-empty v-else image="search" description="暂无本地生活订单" />
        </van-tab>
      </van-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

import { localLifeApi } from '@/api/modules'
import { normalizeLoadError, orderStatusClass, orderStatusLabel } from '@/utils/ui'

const router = useRouter()
const activeTab = ref(0)
const merchants = ref([])
const services = ref([])
const revenue = ref({})
const orders = ref([])
const loading = ref(false)
const loadError = ref('')

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
  return orderStatusLabel(status, { PAID: '待核销' })
}

function goService(id) {
  router.push(`/life/services/${id}`)
}

function goOrder(id) {
  router.push(`/orders/${id}`)
}

async function filterByMerchant(merchantId, merchantName) {
  services.value = await localLifeApi.services(merchantId)
  activeTab.value = 0
  showToast(`${merchantName} 服务已筛出`)
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
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
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
