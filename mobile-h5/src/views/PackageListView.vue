<template>
  <div class="page safe-bottom">
    <van-nav-bar title="套餐中心" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">套餐入场与权益</h2>
      <p class="page-desc">购买套餐可获得兑换券、AI 券抵扣资格、积分补贴与商品上架额度，是平台复购区和资产体系的核心入口。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">套餐列表</h3>
      <div v-if="packages.length">
        <div class="product-item" v-for="item in packages" :key="item.id" @click="goDetail(item.id)">
          <div class="product-name">{{ item.package_name }}</div>
          <div class="product-meta">售价 {{ item.package_price }} / AI 券抵扣上限 {{ item.ai_coupon_max_deduct_rate }}%</div>
          <div class="product-meta">购券 {{ item.voucher_reward_rate }}% / 推荐赠券 {{ item.referral_voucher_rate }}% / 上架额度 {{ item.grants_product_quota }}</div>
        </div>
      </div>
      <van-empty v-else image="search" description="暂无可购买套餐" />
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">我的套餐资格</h3>
      <van-cell-group inset>
        <van-cell v-for="item in qualifications" :key="item.order_id" :title="item.package_name" :label="`订单 ${item.order_id} / 上架额度 ${item.grants_product_quota}`">
          <template #value>
            <div>{{ item.paid_amount }}</div>
            <div>{{ item.order_status }}</div>
          </template>
        </van-cell>
      </van-cell-group>
      <van-empty v-if="!qualifications.length" image="search" description="暂无套餐资格记录" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { packageApi } from '@/api/modules'

const router = useRouter()
const packages = ref([])
const qualifications = ref([])

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
  const [packageRows, qualificationRows] = await Promise.all([
    packageApi.list(),
    packageApi.qualifications()
  ])
  packages.value = packageRows || []
  qualifications.value = qualificationRows || []
}

onMounted(loadData)
</script>
