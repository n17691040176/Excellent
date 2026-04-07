<template>
  <div class="page safe-bottom">
    <van-nav-bar title="服务详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div v-if="loadError" class="page-card">
      <div class="state-card">
        <div class="state-title">服务详情加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
    </div>

    <template v-else>
      <div class="page-card hero-soft">
        <div class="hero-badge">Service Detail</div>
        <h2 class="page-title">{{ detail.service_name || '本地生活服务' }}</h2>
        <p class="page-desc">到店服务下单后生成核销订单，核销完成会触发佣金冻结与结算逻辑。</p>
        <div class="price-panel">
          <div class="price-panel-label">服务售价</div>
          <div class="price-panel-value">¥{{ detail.sale_price || '--' }}</div>
        </div>
        <div class="chip-list">
          <div class="chip">{{ detail.service_type || '服务类型待定' }}</div>
          <div class="chip">{{ detail.verification_type || '核销方式待定' }}</div>
          <div class="chip">{{ detail.status || '状态待定' }}</div>
        </div>
        <div class="soft-section">
          <div class="product-meta">门市价 {{ detail.market_price || '--' }}</div>
          <div class="product-meta">服务类型 {{ detail.service_type || '--' }}</div>
          <div class="product-meta">核销方式 {{ detail.verification_type || '--' }}</div>
          <div class="product-meta">状态 {{ detail.status || '--' }}</div>
        </div>
      </div>

      <div class="page-card">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">下单设置</h3>
          <span class="section-link-text">实时创建</span>
        </div>
        <van-stepper v-model="quantity" min="1" integer />
        <van-field v-model="pointsAmount" type="number" label="使用积分" placeholder="输入积分抵扣金额" />
        <van-field v-model="balanceAmount" type="number" label="使用余额" placeholder="输入余额抵扣金额" />
        <van-field v-model="storeId" type="digit" label="门店 ID" placeholder="可选指定门店 ID" />
        <div class="submit-bar">
          <van-button round block type="primary" @click="submitOrder">{{ submitting ? '提交中...' : '提交服务订单' }}</van-button>
        </div>
      </div>

      <div class="page-card">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">可选门店</h3>
          <span class="section-link-text">{{ stores.length }} 家</span>
        </div>
        <div v-if="stores.length" class="card-stack">
          <div class="soft-section" v-for="item in stores" :key="item.id" @click="pickStore(item.id)">
            <div class="product-name">{{ item.store_name }}</div>
            <div class="product-meta">{{ joinAddress(item) }}</div>
            <div class="product-meta">状态 {{ item.status }}</div>
          </div>
        </div>
        <van-empty v-else image="search" description="当前服务暂无门店信息" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showToast } from 'vant'

import { localLifeApi } from '@/api/modules'
import { normalizeLoadError } from '@/utils/ui'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const stores = ref([])
const quantity = ref(1)
const pointsAmount = ref('0')
const balanceAmount = ref('0')
const storeId = ref('')
const loadError = ref('')
const submitting = ref(false)

function joinAddress(item) {
  return [item.province, item.city, item.district, item.detail_address].filter(Boolean).join(' ')
}

function pickStore(id) {
  storeId.value = String(id)
  showToast(`已选择门店 ${id}`)
}

async function loadData() {
  loadError.value = ''
  try {
    const service = await localLifeApi.serviceDetail(route.params.id)
    detail.value = service || {}
    stores.value = service?.merchant_id ? await localLifeApi.stores(service.merchant_id) : []
    if (service?.store_id) {
      storeId.value = String(service.store_id)
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function submitOrder() {
  submitting.value = true
  try {
    const order = await localLifeApi.createOrder({
      service_id: Number(route.params.id),
      store_id: storeId.value ? Number(storeId.value) : null,
      quantity: quantity.value,
      points_amount: Number(pointsAmount.value || 0),
      balance_amount: Number(balanceAmount.value || 0)
    })
    showSuccessToast('服务订单已创建')
    router.replace(`/orders/${order.id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
