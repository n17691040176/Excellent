<template>
  <view class="page">
    <view class="card">
      <view class="badge">Excellent Mall</view>
      <view class="title">四区联动的健康消费平台</view>
      <view class="desc">
        一期与二期能力统一跑在同一套后端之上：套餐复购、自营商城、爆款专区和本地生活，共用团队、邀请、返现和资产体系。
      </view>

      <view class="metric-grid">
        <view class="metric-card" v-for="item in metrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="section-title">套餐专区</view>
        <view class="section-link" @click="goPackages">查看全部</view>
      </view>
      <view class="section-desc">
        套餐是复购区和上架资格的入口，也决定兑换券、AI 券和积分补贴能力。
      </view>
      <view v-if="packages.length">
        <view class="list-card" v-for="item in packages.slice(0, 2)" :key="item.id" @click="goPackage(item.id)">
          <view class="item-title">{{ item.package_name }}</view>
          <view class="item-meta">
            售价 {{ item.package_price }} / AI 券最高抵扣 {{ item.ai_coupon_max_deduct_rate }}%
          </view>
          <view class="item-meta">
            购券 {{ item.voucher_reward_rate }}% / 推荐赠券 {{ item.referral_voucher_rate }}%
          </view>
        </view>
      </view>
      <view v-else class="empty-text">暂无套餐上架</view>
    </view>

    <view class="card">
      <view class="section-title">专区看板</view>
      <view class="zone-list">
        <view class="zone-card" v-for="item in zoneTabs" :key="item.key">
          <view class="zone-title">{{ item.title }}</view>
          <view class="zone-tip">{{ item.tip }}</view>
          <view class="zone-count">{{ zoneList(item.key).length }} 条内容</view>
          <view v-if="zoneList(item.key).length" class="zone-preview">
            {{ displayName(zoneList(item.key)[0]) }}
          </view>
          <view v-else class="zone-preview">该专区暂无内容</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">快捷入口</view>
      <view class="quick-grid">
        <view class="quick-item" @click="goPackages">套餐中心</view>
        <view class="quick-item" @click="goLife">本地生活</view>
        <view class="quick-item" @click="goTeam">我的团队</view>
        <view class="quick-item" @click="goInvite">邀请好友</view>
        <view class="quick-item" @click="goCommission">佣金中心</view>
        <view class="quick-item" @click="goOrders">我的订单</view>
        <view class="quick-item" @click="goAssets">资产中心</view>
        <view class="quick-item" @click="goProfile">个人中心</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { homeApi, localLifeApi, packageApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

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
  return item?.product_name || item?.service_name || item?.package_name || `内容 ${item?.id || ''}`
}

function openPage(url) {
  uni.navigateTo({ url })
}

function goPackages() {
  uni.switchTab({ url: '/pages/packages/list' })
}

function goOrders() {
  uni.switchTab({ url: '/pages/orders/list' })
}

function goProfile() {
  uni.switchTab({ url: '/pages/profile/index' })
}

function goPackage(id) {
  openPage(`/subpackages/package/detail?id=${id}`)
}

function goLife() {
  openPage('/subpackages/life/index')
}

function goTeam() {
  openPage('/subpackages/team/index')
}

function goInvite() {
  openPage('/subpackages/invite/index')
}

function goCommission() {
  openPage('/subpackages/commission/index')
}

function goAssets() {
  openPage('/subpackages/assets/index')
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
  lists.value = {
    repurchase: repurchase || [],
    selfOperated: selfOperated || [],
    hotSale: hotSale || [],
    localLife: localLife || []
  }
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 32rpx;
}

.card {
  background: #ffffff;
  border-radius: 24rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
}

.badge {
  display: inline-flex;
  align-items: center;
  height: 48rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: #e8f1ff;
  color: #0d6efd;
  font-size: 24rpx;
  margin-bottom: 18rpx;
}

.title {
  font-size: 40rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
}

.desc {
  font-size: 28rpx;
  color: #6b7280;
  line-height: 1.6;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 24rpx;
}

.metric-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
}

.metric-label {
  font-size: 24rpx;
  color: #6b7280;
  margin-bottom: 8rpx;
}

.metric-value {
  font-size: 40rpx;
  color: #111827;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.metric-meta {
  font-size: 24rpx;
  line-height: 1.5;
  color: #6b7280;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8rpx;
}

.section-title {
  font-size: 34rpx;
  font-weight: 600;
}

.section-link {
  font-size: 26rpx;
  color: #0d6efd;
}

.section-desc {
  font-size: 26rpx;
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 20rpx;
}

.list-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}

.item-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 8rpx;
}

.item-meta {
  font-size: 24rpx;
  color: #6b7280;
  line-height: 1.6;
}

.empty-text {
  font-size: 26rpx;
  color: #9ca3af;
}

.zone-list {
  display: grid;
  gap: 16rpx;
}

.zone-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
}

.zone-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 8rpx;
}

.zone-tip,
.zone-count,
.zone-preview {
  font-size: 24rpx;
  color: #6b7280;
  line-height: 1.6;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16rpx;
}

.quick-item {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 28rpx 12rpx;
  text-align: center;
  font-size: 24rpx;
  line-height: 1.5;
  color: #111827;
}
</style>
