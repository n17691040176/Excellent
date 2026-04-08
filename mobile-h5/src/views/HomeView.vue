<template>
  <div class="page safe-bottom">
    <van-nav-bar title="商城首页" fixed placeholder />

    <div class="page-card">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">入场套餐</h3>
        <span class="section-link-text" @click="goPackages">查看全部</span>
      </div>

      <div v-if="loadError" class="state-card">
        <div class="state-title">首页数据加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
      <div v-else-if="loading" class="card-stack">
        <div class="skeleton-card"></div>
        <div class="skeleton-card short"></div>
      </div>
      <div v-else-if="packages.length" class="card-stack">
        <div class="soft-section" v-for="item in packages.slice(0, 2)" :key="item.id" @click="goPackage(item.id)">
          <div class="top-row">
            <div>
              <div class="product-name">{{ item.package_name }}</div>
              <div class="product-meta">AI 券抵扣上限 {{ item.ai_coupon_max_deduct_rate }}%</div>
            </div>
            <div class="price-main">¥{{ item.package_price }}</div>
          </div>
          <div class="chip-list" style="margin-bottom: 0.14rem;">
            <div class="chip">购券 {{ item.voucher_reward_rate }}%</div>
            <div class="chip">推荐赠券 {{ item.referral_voucher_rate }}%</div>
          </div>
          <div class="product-meta">购买后进入复购区并获得平台消费与返利的基础资格。</div>
        </div>
      </div>
      <van-empty v-else image="search" description="暂无套餐上架" />
    </div>

    <div class="page-card">
      <div class="section-head" style="margin-bottom: 0.2rem;">
        <h3 class="cell-group-title" style="margin: 0;">四区分类</h3>
        <span class="section-link-text" @click="router.push('/categories')">进入分类</span>
      </div>
      <div class="card-stack">
        <div class="soft-section" v-for="item in zoneTabs" :key="item.key" @click="openZone(item.key)">
          <div class="top-row">
            <div class="zone-title">{{ item.title }}</div>
            <div class="soft-chip">{{ zoneList(item.key).length }} 条</div>
          </div>
          <div class="zone-tip">{{ item.tip }}</div>
          <div class="product-meta" style="margin-top: 0.12rem;">
            {{ zoneList(item.key).length ? displayName(zoneList(item.key)[0]) : '该专区暂无内容' }}
          </div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="section-head" style="margin-bottom: 0.2rem;">
        <h3 class="cell-group-title" style="margin: 0;">快捷入口</h3>
        <span class="section-link-text" @click="router.push('/profile')">个人中心</span>
      </div>
      <div class="quick-grid">
        <div class="quick-card" v-for="item in quickActions" :key="item.key" @click="handleQuick(item.key)">
          <div class="quick-title">{{ item.title }}</div>
          <div class="quick-desc">{{ item.desc }}</div>
        </div>
      </div>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppTabbar from '@/components/AppTabbar.vue'
import { homeApi, localLifeApi, packageApi } from '@/api/modules'
import { normalizeLoadError } from '@/utils/ui'

const router = useRouter()
const packages = ref([])
const loading = ref(false)
const loadError = ref('')
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
const quickActions = [
  { key: 'categories', title: '分类选品', desc: '按四区快速筛选商品与服务' },
  { key: 'life', title: '本地生活', desc: '浏览联盟商家与服务供给' },
  { key: 'team', title: '我的团队', desc: '管理归属与成员结构' },
  { key: 'invite', title: '邀请好友', desc: '分享邀请码完成绑定' },
  { key: 'commission', title: '佣金中心', desc: '跟进冻结与可提现状态' },
  { key: 'orders', title: '我的订单', desc: '统一查看支付与完成进度' },
  { key: 'assets', title: '资产中心', desc: '查看余额、积分与券资产' },
  { key: 'profile', title: '个人中心', desc: '维护资料、签到和账号设置' }
]

function zoneList(key) {
  return lists.value[key] || []
}

function displayName(item) {
  return item.product_name || item.service_name || item.package_name || `内容 ${item.id}`
}

function goPackages() {
  router.push('/packages')
}

function goPackage(id) {
  router.push(`/packages/${id}`)
}

function openZone(zoneKey) {
  router.push({ path: '/categories', query: { zone: zoneKey } })
}

function handleQuick(key) {
  const map = {
    categories: '/categories',
    life: '/life',
    team: '/team',
    invite: '/invite',
    commission: '/commission',
    orders: '/orders',
    assets: '/assets',
    profile: '/profile'
  }
  router.push(map[key])
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const [packageRows, repurchase, selfOperated, hotSale, localLife] = await Promise.all([
      packageApi.list(),
      homeApi.repurchase(),
      homeApi.selfOperated(),
      homeApi.hotSale(),
      localLifeApi.services()
    ])
    packages.value = packageRows || []
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

onMounted(loadData)
</script>
