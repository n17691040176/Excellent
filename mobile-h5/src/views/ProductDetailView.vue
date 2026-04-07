<template>
  <div class="page safe-bottom">
    <van-nav-bar title="商品详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div v-if="loadError" class="page-card">
      <div class="state-card">
        <div class="state-title">商品详情加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
    </div>

    <template v-else>
      <div class="page-card hero-soft">
        <div class="hero-badge">{{ zoneLabel }}</div>
        <h2 class="page-title">{{ detail.product_name || '商品详情' }}</h2>
        <p class="page-desc">{{ zoneDesc }}</p>
        <div class="price-panel">
          <div class="price-panel-label">当前售价</div>
          <div class="price-panel-value">¥{{ detail.sale_price || '--' }}</div>
        </div>
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
          <h3 class="cell-group-title" style="margin: 0;">下单设置</h3>
          <span class="section-link-text">专区下单</span>
        </div>
        <div class="soft-section">
          <div class="product-meta">下单数量 {{ quantity }}</div>
          <div class="product-meta">{{ orderHint }}</div>
          <div class="product-meta" v-if="detail.requires_shipping">收货地址 {{ addressLabel }}</div>
        </div>
        <div style="margin-top: 0.22rem;">
          <van-stepper v-model="quantity" min="1" integer />
        </div>
        <div v-if="detail.requires_shipping" style="margin-top: 0.24rem;">
          <van-cell title="收货地址" :value="addressLabel" is-link to="/addresses" />
        </div>
        <div style="margin-top: 0.24rem;">
          <van-field v-model="deductAmount" type="number" label="资产抵扣" placeholder="按专区规则输入抵扣金额" />
          <van-radio-group v-model="assetType" direction="horizontal">
            <van-radio v-for="item in availableAssets" :key="item.value" :name="item.value">{{ item.label }}</van-radio>
          </van-radio-group>
        </div>
        <div class="submit-bar">
          <van-button round block type="primary" @click="submitOrder">{{ submitting ? '提交中...' : '提交订单' }}</van-button>
        </div>
      </div>

      <div class="page-card">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">专区说明</h3>
          <span class="section-link-text">{{ zoneLabel }}</span>
        </div>
        <div class="soft-section">
          <div class="product-meta">适用规则 {{ zoneDesc }}</div>
          <div class="product-meta">可用资产 {{ availableAssets.map((item) => item.label).join(' / ') || '暂不支持资产抵扣' }}</div>
          <div class="product-meta">订单类型 {{ orderType }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showFailToast, showSuccessToast } from 'vant'

import { addressApi, orderApi, productApi } from '@/api/modules'
import { normalizeLoadError } from '@/utils/ui'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const addresses = ref([])
const quantity = ref(1)
const deductAmount = ref('0')
const assetType = ref('')
const loadError = ref('')
const submitting = ref(false)

const zone = computed(() => String(route.query.zone || 'SELF_OPERATED'))
const zoneLabel = computed(() => ({
  REPURCHASE: '复购区',
  SELF_OPERATED: '自营商城',
  HOT_SALE: '爆款区',
  LOCAL_LIFE: '本地生活'
}[zone.value] || '商品专区'))
const zoneDesc = computed(() => ({
  REPURCHASE: '适合套餐用户进行康养品二次复购，强调折扣和持续消费。',
  SELF_OPERATED: '支持兑换券和 AI 券逻辑，适合平台自营商品成交。',
  HOT_SALE: '爆款区突出积分或余额抢购，提升高频转化。',
  LOCAL_LIFE: '本地生活以到店服务为主，建议前往服务详情走核销单。'
}[zone.value] || ''))
const orderHint = computed(() => ({
  REPURCHASE: '复购区通常以正常支付为主，也可结合积分做补贴对冲。',
  SELF_OPERATED: '自营商城建议使用兑换券或 AI 券抵扣，再完成订单支付。',
  HOT_SALE: '爆款区优先使用积分或余额做低价抢购。',
  LOCAL_LIFE: '若该商品属于服务类，更建议走本地生活服务详情下单链路。'
}[zone.value] || ''))

const availableAssets = computed(() => ({
  REPURCHASE: [
    { label: '积分', value: 'POINTS' }
  ],
  SELF_OPERATED: [
    { label: '兑换券', value: 'VOUCHER' },
    { label: 'AI 券', value: 'AI_COUPON' }
  ],
  HOT_SALE: [
    { label: '积分', value: 'POINTS' },
    { label: '余额', value: 'BALANCE' }
  ],
  LOCAL_LIFE: [
    { label: '积分', value: 'POINTS' },
    { label: '余额', value: 'BALANCE' }
  ]
}[zone.value] || []))

const selectedAddress = computed(() => addresses.value.find((item) => item.is_default) || addresses.value[0] || null)
const addressLabel = computed(() => {
  if (!selectedAddress.value) return '请先新增地址'
  return [selectedAddress.value.province, selectedAddress.value.city, selectedAddress.value.district, selectedAddress.value.detail_address].filter(Boolean).join(' ')
})

const orderType = computed(() => ({
  REPURCHASE: 'REPURCHASE_ORDER',
  SELF_OPERATED: 'SELF_OPERATED_ORDER',
  HOT_SALE: 'HOT_SALE_ORDER',
  LOCAL_LIFE: 'LOCAL_LIFE_ORDER'
}[zone.value] || 'NORMAL_PRODUCT'))

const metrics = computed(() => [
  { label: '市场价', value: detail.value.market_price || '--', meta: '原始参考售价' },
  { label: '库存', value: detail.value.stock || 0, meta: '当前可售库存数量' },
  { label: '销量', value: detail.value.sold_count || 0, meta: '累计成交数量' },
  { label: '发货方式', value: detail.value.drop_shipping_enabled ? '代发' : '普通', meta: detail.value.drop_shipping_enabled ? '支持一件代发' : '普通履约' }
])

async function loadData() {
  loadError.value = ''
  try {
    const [detailData, addressRows] = await Promise.all([
      productApi.detail(route.params.id),
      addressApi.list()
    ])
    detail.value = detailData || {}
    addresses.value = addressRows || []
    assetType.value = availableAssets.value[0]?.value || ''
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function submitOrder() {
  if (detail.value.requires_shipping && !selectedAddress.value) {
    showFailToast('请先新增收货地址')
    return
  }
  submitting.value = true
  try {
    const deductions = []
    if (Number(deductAmount.value || 0) > 0 && assetType.value) {
      deductions.push({
        asset_type: assetType.value,
        amount: Number(deductAmount.value || 0)
      })
    }
    const order = await orderApi.create({
      order_type: orderType.value,
      zone_type: zone.value,
      address_id: selectedAddress.value?.id || null,
      items: [
        {
          product_id: Number(route.params.id),
          quantity: quantity.value
        }
      ],
      asset_deductions: deductions
    })
    showSuccessToast('订单已创建')
    router.replace(`/orders/${order.id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
