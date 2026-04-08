<template>
  <div class="page safe-bottom">
    <van-nav-bar title="分类" fixed placeholder />

    <div class="page-card category-head">
      <div class="section-head category-head-top">
        <div>
          <h3 class="cell-group-title" style="margin: 0;">四区分类</h3>
          <p class="page-desc category-head-desc">按复购区、自营商城、爆款区和本地生活筛选，页面内直接查看可下单内容。</p>
        </div>
        <span class="section-link-text">{{ totalCount }} 条</span>
      </div>

      <div class="category-summary-grid">
        <button
          v-for="item in zones"
          :key="item.key"
          type="button"
          class="category-summary-card"
          :class="{ 'is-active': activeZone === item.key }"
          @click="setZone(item.key)"
        >
          <div class="category-summary-title">{{ item.title }}</div>
          <div class="category-summary-value">{{ zoneCount(item.key) }}</div>
          <div class="category-summary-meta">{{ item.tip }}</div>
        </button>
      </div>
    </div>

    <div class="page-card">
      <div class="category-sticky-panel">
        <div class="category-filter-row">
          <button
            v-for="item in zones"
            :key="item.key"
            type="button"
            class="category-filter-chip"
            :class="{ 'is-active': activeZone === item.key }"
            @click="setZone(item.key)"
          >
            {{ item.title }}
          </button>
        </div>

        <div class="category-sort-row">
          <button
            v-for="item in activeSortOptions"
            :key="item.key"
            type="button"
            class="category-sort-chip"
            :class="{ 'is-active': activeSort === item.key }"
            @click="setSort(item.key)"
          >
            {{ item.title }}
          </button>
        </div>

        <div class="category-search-row">
          <van-field
            v-model="keyword"
            class="category-search-field"
            placeholder="搜索商品或服务名称"
            clearable
          />
        </div>

        <div class="category-price-filter-row">
          <button
            v-for="item in priceRanges"
            :key="item.key"
            type="button"
            class="category-price-chip"
            :class="{ 'is-active': activePriceRange === item.key }"
            @click="setPriceRange(item.key)"
          >
            {{ item.title }}
          </button>
        </div>

        <div class="category-tools-row">
          <div class="category-tools-text">{{ summaryText }}</div>
          <button
            v-if="hasActiveFilters"
            type="button"
            class="category-reset-button"
            @click="resetFilters"
          >
            重置筛选
          </button>
        </div>
      </div>

      <div class="soft-section" style="margin-bottom: 0.18rem;">
        <div class="top-row">
          <div>
            <div class="product-name">{{ activeZoneMeta.title }}</div>
            <div class="product-meta">{{ activeZoneMeta.tip }}</div>
          </div>
          <div class="soft-chip">{{ displayItems.length }} 条</div>
        </div>
      </div>

      <div v-if="loadError" class="state-card">
        <div class="state-title">分类数据加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
      <div v-else-if="loading" class="card-stack">
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card short"></div>
      </div>
      <div v-else-if="displayItems.length" class="card-stack" :class="{ 'category-grid': isCompactGrid }">
        <div
          v-for="item in displayItems"
          :key="`${activeZone}-${item.id}`"
          class="soft-section category-item"
          @click="openItem(item)"
        >
          <div class="top-row">
            <div>
              <div class="product-name">{{ itemName(item) }}</div>
              <div class="product-meta">{{ itemSubMeta(item) }}</div>
            </div>
            <div class="category-price">
              <div class="category-price-main">¥{{ itemPrice(item) }}</div>
              <div class="category-price-sub" v-if="itemMarketPrice(item)">门市价 ¥{{ itemMarketPrice(item) }}</div>
            </div>
          </div>
          <div class="chip-list category-chip-list">
            <div class="chip">{{ activeZoneMeta.title }}</div>
            <div class="chip">{{ itemBadge(item) }}</div>
            <div v-if="itemSecondaryBadge(item)" class="chip">{{ itemSecondaryBadge(item) }}</div>
          </div>
          <div class="product-meta">{{ itemDescription(item) }}</div>
        </div>
      </div>
      <van-empty v-else image="search" description="当前分类暂无内容" />
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppTabbar from '@/components/AppTabbar.vue'
import { homeApi, localLifeApi } from '@/api/modules'
import { normalizeLoadError } from '@/utils/ui'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const activeZone = ref('repurchase')
const activeSort = ref('default')
const activePriceRange = ref('all')
const keyword = ref('')
const lists = ref({
  repurchase: [],
  selfOperated: [],
  hotSale: [],
  localLife: []
})

const zones = [
  { key: 'repurchase', code: 'REPURCHASE', title: '复购区', tip: '套餐进入后的复购商品，适合持续消费。' },
  { key: 'selfOperated', code: 'SELF_OPERATED', title: '自营商城', tip: '平台自营商品，支持券类抵扣与转化。' },
  { key: 'hotSale', code: 'HOT_SALE', title: '爆款区', tip: '突出低价爆款和高频抢购。' },
  { key: 'localLife', code: 'LOCAL_LIFE', title: '本地生活', tip: '到店服务与联盟商家履约内容。' }
]
const priceRanges = [
  { key: 'all', title: '全部价格', min: null, max: null },
  { key: '0-99', title: '100 以下', min: 0, max: 99.99 },
  { key: '100-299', title: '100-299', min: 100, max: 299.99 },
  { key: '300-499', title: '300-499', min: 300, max: 499.99 },
  { key: '500+', title: '500 以上', min: 500, max: null }
]

const totalCount = computed(() => Object.values(lists.value).reduce((sum, rows) => sum + rows.length, 0))

const activeZoneMeta = computed(() => zones.find((item) => item.key === activeZone.value) || zones[0])
const activeItems = computed(() => lists.value[activeZone.value] || [])
const isCompactGrid = computed(() => activeZone.value !== 'localLife')
const activePriceMeta = computed(() => priceRanges.find((item) => item.key === activePriceRange.value) || priceRanges[0])
const filteredItems = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase()

  return activeItems.value.filter((item) => {
    const name = String(itemName(item)).toLowerCase()
    const matchesKeyword = !normalizedKeyword || name.includes(normalizedKeyword)

    const price = Number(item.sale_price || 0)
    const { min, max } = activePriceMeta.value
    const matchesMin = min == null || price >= min
    const matchesMax = max == null || price <= max

    return matchesKeyword && matchesMin && matchesMax
  })
})
const activeSortOptions = computed(() => {
  if (activeZone.value === 'localLife') {
    return [
      { key: 'default', title: '默认' },
      { key: 'latest', title: '最新' },
      { key: 'priceAsc', title: '低价优先' },
      { key: 'priceDesc', title: '高价优先' }
    ]
  }

  return [
    { key: 'default', title: '默认' },
    { key: 'latest', title: '最新' },
    { key: 'priceAsc', title: '低价优先' },
    { key: 'sales', title: '销量优先' }
  ]
})
const displayItems = computed(() => {
  const rows = [...filteredItems.value]

  if (activeSort.value === 'latest') {
    return rows.sort((a, b) => Number(b.id || 0) - Number(a.id || 0))
  }

  if (activeSort.value === 'priceAsc') {
    return rows.sort((a, b) => Number(a.sale_price || 0) - Number(b.sale_price || 0))
  }

  if (activeSort.value === 'priceDesc') {
    return rows.sort((a, b) => Number(b.sale_price || 0) - Number(a.sale_price || 0))
  }

  if (activeSort.value === 'sales') {
    return rows.sort((a, b) => {
      const salesDiff = Number(b.sold_count || 0) - Number(a.sold_count || 0)
      return salesDiff || Number(b.id || 0) - Number(a.id || 0)
    })
  }

  return rows
})
const summaryText = computed(() => {
  const segments = [activeZoneMeta.value.tip]

  if (keyword.value.trim()) {
    segments.push(`搜索“${keyword.value.trim()}”`)
  }

  if (activePriceMeta.value.key !== 'all') {
    segments.push(activePriceMeta.value.title)
  }

  return segments.join(' · ')
})
const hasActiveFilters = computed(() => {
  return activeSort.value !== 'default' || activePriceMeta.value.key !== 'all' || Boolean(keyword.value.trim())
})

function zoneCount(key) {
  return lists.value[key]?.length || 0
}

function syncZoneFromRoute(value) {
  const zone = typeof value === 'string' ? value : ''
  activeZone.value = zones.some((item) => item.key === zone) ? zone : 'repurchase'
}

function setZone(key) {
  if (key === activeZone.value) return
  router.replace({ path: '/categories', query: { zone: key } })
}

function setSort(key) {
  activeSort.value = key
}

function setPriceRange(key) {
  activePriceRange.value = key
}

function resetFilters() {
  activeSort.value = 'default'
  activePriceRange.value = 'all'
  keyword.value = ''
}

function itemName(item) {
  return item.product_name || item.service_name || `内容 ${item.id}`
}

function itemPrice(item) {
  return item.sale_price ?? '--'
}

function itemMarketPrice(item) {
  return item.market_price ?? ''
}

function itemSubMeta(item) {
  if (activeZone.value === 'localLife') {
    return `${item.service_type || '到店服务'} / ${item.verification_type || '核销服务'}`
  }
  return `库存 ${item.stock || 0} / 销量 ${item.sold_count || 0}`
}

function itemBadge(item) {
  if (activeZone.value === 'repurchase') {
    return '复购专区'
  }
  if (activeZone.value === 'selfOperated') {
    return item.drop_shipping_enabled ? '支持代发' : '自营发货'
  }
  if (activeZone.value === 'hotSale') {
    return '爆款抢购'
  }
  return item.service_type || '本地服务'
}

function itemSecondaryBadge(item) {
  if (activeZone.value === 'selfOperated' && item.requires_shipping) {
    return '快递发货'
  }
  if (activeZone.value === 'hotSale' && item.requires_shipping) {
    return '限时专区'
  }
  if (activeZone.value === 'localLife') {
    return item.verification_type || ''
  }
  return ''
}

function itemDescription(item) {
  if (activeZone.value === 'repurchase') {
    return '点击进入商品详情，可按复购区规则完成下单。'
  }
  if (activeZone.value === 'selfOperated') {
    return '支持进入详情页后选择券类或 AI 券抵扣。'
  }
  if (activeZone.value === 'hotSale') {
    return '适合积分或余额参与的低价成交商品。'
  }
  return '点击进入服务详情，继续选择门店、核销方式与下单数量。'
}

function openItem(item) {
  if (activeZone.value === 'localLife') {
    router.push(`/life/services/${item.id}`)
    return
  }
  router.push(`/products/${item.id}?zone=${activeZoneMeta.value.code}`)
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const [repurchase, selfOperated, hotSale, localLife] = await Promise.all([
      homeApi.repurchase(),
      homeApi.selfOperated(),
      homeApi.hotSale(),
      localLifeApi.services()
    ])
    lists.value = {
      repurchase: repurchase || [],
      selfOperated: selfOperated || [],
      hotSale: hotSale || [],
      localLife: localLife || []
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query.zone,
  (value) => {
    syncZoneFromRoute(value)
  },
  { immediate: true }
)

watch(activeZone, () => {
  if (!activeSortOptions.value.some((item) => item.key === activeSort.value)) {
    activeSort.value = 'default'
  }
  activePriceRange.value = 'all'
  keyword.value = ''
})

onMounted(loadData)
</script>

<style scoped>
.category-head {
  padding-bottom: 0.2rem;
}

.category-head-top {
  align-items: flex-start;
  margin-bottom: 0.2rem;
}

.category-head-desc {
  margin: 0.08rem 0 0;
}

.category-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.16rem;
}

.category-summary-card {
  width: 100%;
  padding: 0.22rem;
  appearance: none;
  border: 1px solid rgba(24, 52, 59, 0.08);
  border-radius: 0.24rem;
  text-align: left;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(245, 250, 248, 0.88));
}

.category-summary-card.is-active {
  border-color: rgba(31, 143, 110, 0.34);
  background: linear-gradient(180deg, rgba(238, 249, 244, 0.98), rgba(255, 255, 255, 0.96));
  box-shadow: 0 0.14rem 0.28rem rgba(31, 143, 110, 0.1);
}

.category-summary-title {
  font-size: 0.28rem;
  font-weight: 700;
  color: var(--brand-deep);
}

.category-summary-value {
  margin-top: 0.12rem;
  font-size: 0.42rem;
  font-weight: 800;
  color: var(--brand-green);
}

.category-summary-meta {
  margin-top: 0.08rem;
  font-size: 0.22rem;
  line-height: 1.6;
  color: rgba(24, 52, 59, 0.6);
}

.category-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.14rem;
  margin-bottom: 0.16rem;
}

.category-sticky-panel {
  position: sticky;
  top: calc(env(safe-area-inset-top) + 0.92rem);
  z-index: 5;
  margin: -0.04rem -0.04rem 0.2rem;
  padding: 0.04rem;
  border-radius: 0.28rem;
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(255, 255, 255, 0.96));
  box-shadow: 0 0.12rem 0.24rem rgba(24, 52, 59, 0.06);
  backdrop-filter: blur(10px);
}

.category-filter-chip {
  min-width: 1.38rem;
  padding: 0.14rem 0.22rem;
  appearance: none;
  border: 1px solid rgba(24, 52, 59, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: rgba(24, 52, 59, 0.72);
  font-size: 0.24rem;
  font-weight: 600;
}

.category-filter-chip.is-active {
  border-color: transparent;
  background: linear-gradient(135deg, var(--brand-deep), var(--brand-green));
  color: #fff;
}

.category-sort-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.12rem;
  margin-bottom: 0.16rem;
}

.category-sort-chip {
  padding: 0.1rem 0.18rem;
  appearance: none;
  border: 1px solid rgba(24, 52, 59, 0.08);
  border-radius: 999px;
  background: rgba(244, 247, 245, 0.96);
  color: rgba(24, 52, 59, 0.62);
  font-size: 0.22rem;
  font-weight: 600;
}

.category-sort-chip.is-active {
  border-color: rgba(31, 143, 110, 0.24);
  background: rgba(31, 143, 110, 0.12);
  color: var(--brand-green);
}

.category-search-row {
  margin-bottom: 0.16rem;
}

.category-search-field {
  padding: 0.02rem 0.06rem;
  border: 1px solid rgba(24, 52, 59, 0.08);
  border-radius: 0.24rem;
  background: rgba(255, 255, 255, 0.96);
}

.category-price-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.12rem;
  margin-bottom: 0.2rem;
}

.category-price-chip {
  padding: 0.1rem 0.18rem;
  appearance: none;
  border: 1px solid rgba(24, 52, 59, 0.08);
  border-radius: 999px;
  background: rgba(255, 252, 247, 0.96);
  color: rgba(24, 52, 59, 0.62);
  font-size: 0.22rem;
  font-weight: 600;
}

.category-price-chip.is-active {
  border-color: rgba(200, 155, 73, 0.3);
  background: rgba(200, 155, 73, 0.12);
  color: #9d732c;
}

.category-tools-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.16rem;
}

.category-tools-text {
  flex: 1;
  font-size: 0.22rem;
  line-height: 1.6;
  color: rgba(24, 52, 59, 0.58);
}

.category-reset-button {
  flex-shrink: 0;
  padding: 0.1rem 0.18rem;
  appearance: none;
  border: 1px solid rgba(24, 52, 59, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: var(--brand-deep);
  font-size: 0.22rem;
  font-weight: 600;
}

.category-item {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 2.7rem;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.category-item:active {
  transform: scale(0.98);
}

.category-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.18rem;
}

.category-grid .category-item {
  min-height: 3.2rem;
  padding: 0.22rem;
}

.category-grid .top-row {
  flex-direction: column;
  align-items: flex-start;
}

.category-grid .category-price {
  margin-top: 0.18rem;
  text-align: left;
}

.category-grid .category-price-main {
  font-size: 0.4rem;
}

.category-grid .category-chip-list {
  margin-top: auto;
}

.category-price {
  text-align: right;
  flex-shrink: 0;
}

.category-price-main {
  font-size: 0.44rem;
  font-weight: 800;
  color: var(--brand-green);
}

.category-price-sub {
  margin-top: 0.08rem;
  font-size: 0.22rem;
  color: rgba(24, 52, 59, 0.54);
}

.category-chip-list {
  margin-bottom: 0.14rem;
}
</style>
