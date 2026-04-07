<template>
  <div class="page safe-bottom">
    <van-nav-bar title="套餐中心" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-soft">
      <div class="hero-badge">Package Center</div>
      <h2 class="page-title">先看入场门槛，再看能换来什么资格</h2>
      <p class="page-desc">套餐页按全局判断、套餐档位和已购资格三段排布，减少逐条比对成本。</p>
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
        <h3 class="cell-group-title" style="margin: 0;">可选套餐</h3>
        <span class="section-link-text">{{ packages.length }} 档</span>
      </div>
      <div v-if="loadError" class="state-card">
        <div class="state-title">套餐加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
      <div v-else-if="loading" class="card-stack">
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
      </div>
      <div v-else-if="packages.length" class="card-stack">
        <div class="soft-section" v-for="item in packages" :key="item.id" @click="goDetail(item.id)">
          <div class="top-row">
            <div>
              <div class="product-name">{{ item.package_name }}</div>
              <div class="product-meta">AI 券抵扣上限 {{ item.ai_coupon_max_deduct_rate }}%</div>
            </div>
            <div class="price-panel" style="margin: 0; min-width: 1.7rem; padding: 0.18rem 0.2rem;">
              <div class="price-panel-label">到手门槛</div>
              <div class="price-panel-value" style="font-size: 0.4rem;">¥{{ item.package_price }}</div>
            </div>
          </div>
          <div class="chip-list" style="margin-bottom: 0.14rem;">
            <div class="chip">购券 {{ item.voucher_reward_rate }}%</div>
            <div class="chip">推荐赠券 {{ item.referral_voucher_rate }}%</div>
            <div class="chip">上架额度 {{ item.grants_product_quota }}</div>
          </div>
          <div class="product-meta">购买后进入复购体系，同时获得兑换券、积分补贴和商城经营资格。</div>
        </div>
      </div>
      <van-empty v-else image="search" description="暂无可购买套餐" />
    </div>

    <div class="page-card">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">我的套餐资格</h3>
        <span class="section-link-text">{{ qualifications.length }} 条</span>
      </div>
      <div v-if="!loadError && loading" class="card-stack">
        <div class="skeleton-card short"></div>
      </div>
      <div v-else-if="qualifications.length" class="card-stack">
        <div class="soft-section" v-for="item in qualifications" :key="item.order_id">
          <div class="top-row">
            <div class="product-name">{{ item.package_name }}</div>
            <div class="status-capsule" :class="orderStatusClass(item.order_status)">{{ orderStatusLabel(item.order_status) }}</div>
          </div>
          <div class="product-meta">订单 {{ item.order_id }} / 上架额度 {{ item.grants_product_quota }}</div>
          <div class="product-meta">实付 ¥{{ item.paid_amount }} / 已沉淀可持续使用的经营资格</div>
        </div>
      </div>
      <van-empty v-else image="search" description="暂无套餐资格记录" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { packageApi } from '@/api/modules'
import { normalizeLoadError, orderStatusClass, orderStatusLabel } from '@/utils/ui'

const router = useRouter()
const packages = ref([])
const qualifications = ref([])
const loading = ref(false)
const loadError = ref('')

const metrics = computed(() => [
  { label: '套餐数量', value: packages.value.length, meta: '当前可购买套餐' },
  { label: '已购资格', value: qualifications.value.length, meta: '已形成复购或上架资格' },
  { label: '最高 AI 抵扣', value: `${Math.max(0, ...packages.value.map((item) => Number(item.ai_coupon_max_deduct_rate || 0)))}%`, meta: '套餐最高 AI 券抵扣比例' },
  { label: '最高上架额度', value: Math.max(0, ...packages.value.map((item) => Number(item.grants_product_quota || 0))), meta: '套餐可解锁商品上架数量' }
])

function goDetail(id) {
  router.push(`/packages/${id}`)
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const [packageRows, qualificationRows] = await Promise.all([
      packageApi.list(),
      packageApi.qualifications()
    ])
    packages.value = packageRows || []
    qualifications.value = qualificationRows || []
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
