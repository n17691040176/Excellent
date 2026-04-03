<template>
  <div class="page safe-bottom">
    <van-nav-bar title="商城首页" fixed placeholder />

    <div class="page-card hero-card">
      <div class="hero-badge">Excellent Mall</div>
      <h2 class="page-title">四区联动的健康消费平台</h2>
      <p class="page-desc">一期与二期能力已合并进同一 App：套餐复购、自营商城、爆款抢购和本地生活统一跑在团队、邀请、返现与资产规则之上。</p>
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
          <h3 class="cell-group-title">套餐专区</h3>
          <p class="page-desc" style="margin-bottom: 0;">套餐是复购区和上架资格的入口，也决定兑换券、AI 券与补贴能力。</p>
        </div>
        <van-button size="small" plain type="primary" to="/packages">查看全部</van-button>
      </div>
      <div v-if="packages.length">
        <div class="product-item" v-for="item in packages.slice(0, 2)" :key="item.id" @click="goPackage(item.id)">
          <div class="product-name">{{ item.package_name }}</div>
          <div class="product-meta">售价 {{ item.package_price }} / AI 券最高抵扣 {{ item.ai_coupon_max_deduct_rate }}%</div>
          <div class="product-meta">购券 {{ item.voucher_reward_rate }}% / 推荐赠券 {{ item.referral_voucher_rate }}%</div>
        </div>
      </div>
      <van-empty v-else image="search" description="暂无套餐上架" />
    </div>

    <div class="page-card">
      <van-tabs v-model:active="activeZone" animated swipeable>
        <van-tab v-for="item in zoneTabs" :key="item.key" :title="item.title">
          <div class="zone-card">
            <div class="zone-head">
              <div class="zone-title">{{ item.title }}</div>
              <div class="zone-tip">{{ item.tip }}</div>
            </div>
            <div v-if="zoneList(item.key).length">
              <div v-for="product in zoneList(item.key)" :key="product.id" class="product-item" @click="goZoneDetail(item.key, product.id)">
                <div class="product-name">{{ displayName(product) }}</div>
                <div class="product-meta">售价 {{ displayPrice(product) }} / 市场价 {{ displayMarketPrice(product) }}</div>
                <div class="product-meta">{{ zoneRule(item.key) }}</div>
              </div>
            </div>
            <van-empty v-else image="search" description="该专区暂无内容" />
          </div>
        </van-tab>
      </van-tabs>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">快捷入口</h3>
      <van-grid :column-num="4" :border="false">
        <van-grid-item icon="coupon-o" text="套餐中心" @click="goPackages" />
        <van-grid-item icon="shop-o" text="本地生活" @click="goLife" />
        <van-grid-item icon="friends-o" text="我的团队" to="/team" />
        <van-grid-item icon="gift-o" text="邀请好友" to="/invite" />
        <van-grid-item icon="balance-o" text="佣金中心" to="/commission" />
        <van-grid-item icon="orders-o" text="我的订单" to="/orders" />
        <van-grid-item icon="location-o" text="收货地址" to="/addresses" />
        <van-grid-item icon="contact-o" text="个人中心" to="/profile" />
      </van-grid>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppTabbar from '@/components/AppTabbar.vue'
import { homeApi, localLifeApi, packageApi } from '@/api/modules'

const router = useRouter()
const activeZone = ref(0)
const packages = ref([])
const lists = ref({
  repurchase: [],
  selfOperated: [],
  hotSale: [],
  localLife: []
})

const zoneTabs = [
  { key: 'repurchase', title: '复购区', tip: '套餐进入，二次复购 4-6 折' },
  { key: 'selfOperated', title: '自营商城', tip: '兑换券 5-7 折抵扣，返 AI 券' },
  { key: 'hotSale', title: '爆款区', tip: '低价抢购，支持积分或余额' },
  { key: 'localLife', title: '本地生活', tip: '联盟商家服务、门店履约与收益联动' }
]

const metrics = computed(() => [
  { label: '套餐中心', value: packages.value.length, meta: '购买套餐可进入复购与资格体系' },
  ...zoneTabs.map((item) => ({
    label: item.title,
    value: zoneList(item.key).length,
    meta: item.tip
  }))
])

function zoneList(key) {
  return lists.value[key] || []
}

function displayName(item) {
  return item.product_name || item.service_name || item.package_name || `内容 ${item.id}`
}

function displayPrice(item) {
  return item.sale_price || item.package_price || '--'
}

function displayMarketPrice(item) {
  return item.market_price || '--'
}

function zoneRule(key) {
  return {
    repurchase: '以康养复购为主，强调套餐用户的二次消费折扣。',
    selfOperated: '支持兑换券抵扣并返 20% AI 券，适合平台自营货盘。',
    hotSale: '强调低价爆品，可用积分或余额快速下单。',
    localLife: '以到店服务与联盟商家为主，核销后沉淀收益与分佣。'
  }[key]
}

function goPackages() {
  router.push('/packages')
}

function goLife() {
  router.push('/life')
}

function goPackage(id) {
  router.push(`/packages/${id}`)
}

function goZoneDetail(zoneKey, id) {
  if (zoneKey === 'localLife') {
    router.push(`/life/services/${id}`)
    return
  }
  router.push(`/products/${id}?zone=${zoneKey.toUpperCase()}`)
}

async function loadData() {
  const [packageRows, repurchase, selfOperated, hotSale, localLife] = await Promise.all([
    packageApi.list(),
    homeApi.repurchase(),
    homeApi.selfOperated(),
    homeApi.hotSale(),
    localLifeApi.services()
  ])
  packages.value = packageRows || []
  lists.value = { repurchase, selfOperated, hotSale, localLife }
}

onMounted(loadData)
</script>
