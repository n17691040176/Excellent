<template>
  <div class="page safe-bottom">
    <van-nav-bar title="个人中心" fixed placeholder />

    <div class="page-card">
      <h2 class="page-title">{{ profile.nickname || '会员' }}</h2>
      <p class="page-desc">手机号 {{ profile.phone || '--' }}，邀请码 {{ inviteCode || '--' }}，团队归属 {{ teamSummary.team_id || '未加入团队' }}。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">账户操作</h3>
      <van-cell-group inset>
        <van-cell title="邀请好友" is-link to="/invite" />
        <van-cell title="我的团队" is-link to="/team" />
        <van-cell title="佣金中心" is-link to="/commission" />
        <van-cell title="资产中心" is-link to="/assets" />
        <van-cell title="收货地址" is-link to="/addresses" />
        <van-cell title="我的订单" is-link to="/orders" />
        <van-cell title="账号设置" is-link to="/settings" />
      </van-cell-group>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">资料设置</h3>
      <van-form @submit="saveProfile">
        <van-field v-model="profile.nickname" label="昵称" placeholder="请输入昵称" />
        <van-field v-model="profile.real_name" label="真实姓名" placeholder="请输入真实姓名" />
        <van-field v-model="profile.avatar" label="头像地址" placeholder="请输入头像 URL" />
        <div class="inline-actions submit-bar">
          <van-button block round plain type="primary" @click="handleSignin">每日签到</van-button>
          <van-button block round type="primary" native-type="submit">保存资料</van-button>
        </div>
      </van-form>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { assetApi, commissionApi, userApi } from '@/api/modules'
import { setUserCache } from '@/utils/auth'

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

async function loadData() {
  const [profileData, assetData, summaryData, codeData, teamData] = await Promise.all([
    userApi.profile(),
    assetApi.summary(),
    commissionApi.summary(),
    userApi.inviteCode(),
    userApi.teamSummary()
  ])
  Object.assign(profile, profileData)
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
  Object.assign(profile, data)
  setUserCache(data)
  showSuccessToast('资料已更新')
}

async function handleSignin() {
  await assetApi.signin()
  showSuccessToast('今日签到成功')
  await loadData()
}

onMounted(loadData)
</script>
