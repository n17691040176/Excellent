<template>
  <div class="page safe-bottom">
    <van-nav-bar title="服务详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">{{ detail.service_name || '本地生活服务' }}</h2>
      <p class="page-desc">到店服务下单后生成核销订单，核销完成会触发佣金冻结与结算逻辑。</p>
      <div class="price-row">
        <div class="price-main">{{ detail.sale_price || '--' }}</div>
        <div class="price-sub">服务售价</div>
      </div>
      <van-cell-group inset>
        <van-cell title="门市价" :value="String(detail.market_price || '--')" />
        <van-cell title="服务类型" :value="detail.service_type || '--'" />
        <van-cell title="核销方式" :value="detail.verification_type || '--'" />
        <van-cell title="状态" :value="detail.status || '--'" />
      </van-cell-group>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">下单设置</h3>
      <van-stepper v-model="quantity" min="1" integer />
      <van-field v-model="pointsAmount" type="number" label="使用积分" placeholder="输入积分抵扣金额" />
      <van-field v-model="balanceAmount" type="number" label="使用余额" placeholder="输入余额抵扣金额" />
      <van-field v-model="storeId" type="digit" label="门店 ID" placeholder="可选指定门店 ID" />
      <div class="submit-bar">
        <van-button round block type="primary" @click="submitOrder">提交服务订单</van-button>
      </div>
      <p class="page-desc" style="margin-top: 0.18rem;">下单后会生成核销码，门店核销成功后订单完成，返现链路随之结算。</p>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">可选门店</h3>
      <van-cell-group inset>
        <van-cell v-for="item in stores" :key="item.id" :title="item.store_name" :label="joinAddress(item)">
          <template #value>{{ item.status }}</template>
        </van-cell>
      </van-cell-group>
      <van-empty v-if="!stores.length" image="search" description="当前服务暂无门店信息" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'

import { localLifeApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const stores = ref([])
const quantity = ref(1)
const pointsAmount = ref('0')
const balanceAmount = ref('0')
const storeId = ref('')

function joinAddress(item) {
  return [item.province, item.city, item.district, item.detail_address].filter(Boolean).join(' ')
}

async function loadData() {
  const service = await localLifeApi.serviceDetail(route.params.id)
  detail.value = service || {}
  stores.value = service?.merchant_id ? await localLifeApi.stores(service.merchant_id) : []
  if (service?.store_id) {
    storeId.value = String(service.store_id)
  }
}

async function submitOrder() {
  const order = await localLifeApi.createOrder({
    service_id: Number(route.params.id),
    store_id: storeId.value ? Number(storeId.value) : null,
    quantity: quantity.value,
    points_amount: Number(pointsAmount.value || 0),
    balance_amount: Number(balanceAmount.value || 0)
  })
  showSuccessToast('服务订单已创建')
  router.replace(`/orders/${order.id}`)
}

onMounted(loadData)
</script>
