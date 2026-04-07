<template>
  <view class="page">
    <view class="card">
      <view class="title">{{ profile.nickname || '会员' }}</view>
      <view class="desc">
        手机号 {{ profile.phone || '--' }}，邀请码 {{ inviteCode || '--' }}，团队归属 {{ teamSummary.team_id || '未加入团队' }}。
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
      <view class="section-title">账户操作</view>
      <view class="action-list">
        <view class="action-item" @click="openPage('/subpackages/invite/index')">邀请好友</view>
        <view class="action-item" @click="openPage('/subpackages/team/index')">我的团队</view>
        <view class="action-item" @click="openPage('/subpackages/commission/index')">佣金中心</view>
        <view class="action-item" @click="openPage('/subpackages/assets/index')">资产中心</view>
        <view class="action-item" @click="switchOrders">我的订单</view>
        <view class="action-item" @click="openPage('/subpackages/profile/settings')">账号设置</view>
      </view>
    </view>

    <view class="card">
      <view class="section-title">资料设置</view>
      <input v-model="profile.nickname" class="input" placeholder="请输入昵称" />
      <input v-model="profile.real_name" class="input" placeholder="请输入真实姓名" />
      <input v-model="profile.avatar" class="input" placeholder="请输入头像 URL" />
      <view class="action-row">
        <button class="secondary-btn" @click="handleSignin">每日签到</button>
        <button class="primary-btn" @click="saveProfile">保存资料</button>
      </view>
    </view>

    <view class="card">
      <button class="danger-btn" @click="logout">退出登录</button>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { assetApi, commissionApi, userApi } from '../../api/modules'
import { clearAuth, setUserCache } from '../../utils/auth'
import { ensureLogin } from '../../utils/guard'

const profile = reactive({
  nickname: '',
  phone: '',
  real_name: '',
  avatar: ''
})
const assets = ref({})
const commissionSummary = ref({})
const inviteCode = ref('')
const teamSummary = ref({})

const metrics = computed(() => [
  { label: '余额', value: Number(assets.value.BALANCE || 0).toFixed(2), meta: '设备分佣与爆款消费' },
  { label: '积分', value: Number(assets.value.POINTS || 0).toFixed(2), meta: '补贴排队、转赠与商城消费' },
  { label: '可提现佣金', value: Number(commissionSummary.value.available_amount || 0).toFixed(2), meta: '确认收货后释放' },
  { label: '冻结佣金', value: Number(commissionSummary.value.frozen_amount || 0).toFixed(2), meta: '订单有效支付后先冻结' }
])

function openPage(url) {
  uni.navigateTo({ url })
}

function switchOrders() {
  uni.switchTab({ url: '/pages/orders/list' })
}

async function loadData() {
  const [profileData, assetData, summaryData, codeData, teamData] = await Promise.all([
    userApi.profile(),
    assetApi.summary(),
    commissionApi.summary(),
    userApi.inviteCode(),
    userApi.teamSummary()
  ])
  Object.assign(profile, profileData || {})
  assets.value = assetData || {}
  commissionSummary.value = summaryData || {}
  inviteCode.value = codeData?.invite_code || ''
  teamSummary.value = teamData || {}
}

async function saveProfile() {
  const data = await userApi.updateProfile({
    nickname: profile.nickname,
    real_name: profile.real_name,
    avatar: profile.avatar
  })
  Object.assign(profile, data || {})
  setUserCache(data)
  uni.showToast({ title: '资料已更新', icon: 'success' })
}

async function handleSignin() {
  await assetApi.signin()
  uni.showToast({ title: '今日签到成功', icon: 'success' })
  loadData()
}

function logout() {
  clearAuth()
  uni.reLaunch({ url: '/pages/login/index' })
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

.section-title {
  font-size: 34rpx;
  font-weight: 600;
  margin-bottom: 20rpx;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 24rpx;
}

.metric-card,
.action-item {
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
  color: #6b7280;
  line-height: 1.6;
}

.action-list {
  display: grid;
  gap: 16rpx;
}

.action-item {
  font-size: 28rpx;
  color: #111827;
}

.input {
  width: 100%;
  height: 88rpx;
  background: #f5f7fb;
  border-radius: 18rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
}

.action-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.primary-btn,
.secondary-btn,
.danger-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  font-size: 30rpx;
}

.primary-btn {
  background: #0d6efd;
  color: #ffffff;
}

.secondary-btn {
  background: #eef4ff;
  color: #0d6efd;
}

.danger-btn {
  background: #fef2f2;
  color: #dc2626;
}
</style>
