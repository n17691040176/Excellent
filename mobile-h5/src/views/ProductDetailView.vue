<template>
  <div class="page safe-bottom">
    <van-nav-bar title="商品详情" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <div class="soft-chip">{{ zoneLabel }}</div>
      <h2 class="page-title">{{ detail.product_name || '商品详情' }}</h2>
      <p class="page-desc">{{ zoneDesc }}</p>
      <div class="price-row">
        <div class="price-main">{{ detail.sale_price || '--' }}</div>
        <div class="price-sub">当前售价</div>
      </div>
      <van-cell-group inset>
        <van-cell title="市场价" :value="String(detail.market_price || '--')" />
        <van-cell title="库存" :value="String(detail.stock || 0)" />
        <van-cell title="销量" :value="String(detail.sold_count || 0)" />
        <van-cell title="发货方式" :value="detail.drop_shipping_enabled ? '支持一件代发' : '普通履约'" />
      </van-cell-group>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">下单设置</h3>
      <van-stepper v-model="quantity" min="1" integer />
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
        <van-button round block type="primary" @click="submitOrder">提交订单</van-button>
      </div>
      <p class="page-desc" style="margin-top: 0.18rem;">{{ orderHint }}</p>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">专区说明</h3>
      <van-cell-group inset>
        <van-cell title="适用规则" :label="zoneDesc" />
        <van-cell title="可用资产" :label="availableAssets.map((item) => item.label).join(' / ') || '暂不支持资产抵扣'" />
      </van-cell-group>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showFailToast, showSuccessToast } from 'vant'

import { addressApi, orderApi, productApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const addresses = ref([])
const quantity = ref(1)
const deductAmount = ref('0')
const assetType = ref('')

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

async function loadData() {
  const [detailData, addressRows] = await Promise.all([
    productApi.detail(route.params.id),
    addressApi.list()
  ])
  detail.value = detailData || {}
  addresses.value = addressRows || []
  assetType.value = availableAssets.value[0]?.value || ''
}

async function submitOrder() {
  if (detail.value.requires_shipping && !selectedAddress.value) {
    showFailToast('请先新增收货地址')
    return
  }
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
}

onMounted(loadData)
</script>
